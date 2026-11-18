"""跨夜支援交接：按实际责任时段核算的规则、守恒与失效重算测试。"""
import pytest
from decimal import Decimal
from app.workflow import run,load
from app.modules.m3b_handovers.rules import parse_handover,normalize_rows,bind_to_shifts,apply
from app.manifest import identity
from app.errors import DomainError

HANDOVER_CSV=(
    'h_id,employee,shift_day,version,at,to_team,note\n'
    'H1,E001,2026-10-01,1,2026-10-02T00:30:00+08:00,LINE-B,x\n'
    'H2,E002,2026-10-01,1,2026-10-02T02:30:00+08:00,LINE-B,break\n').encode()

def test_handover_default_sample_loaded(raw):
    s=run(raw,{})
    assert s['h_input_count']>0 and s['manifest']['handover_sha256']

def test_explicit_no_handover(raw):
    s=run(raw,{'handover':''})
    assert s['handovers']==[] and s['manifest']['handover_sha256']==''
    assert {t['team'] for t in s['team_totals']}=={'HOME'}

def test_handover_split_at_transfer_instant(raw):
    s=run(raw,{'handover':HANDOVER_CSV.decode()})
    e1=[r for r in s['segments'] if r['employee']=='E001']
    home=sum(r['minutes'] for r in e1 if r['team']=='HOME')
    away=sum(r['minutes'] for r in e1 if r['team']=='LINE-B')
    # 22:00-00:30 归 HOME（150min），00:30 之后含复工段归 LINE-B（270min）
    assert home==150 and away==270
    assert all(r['via_handover_line'] is None for r in e1 if r['team']=='HOME')
    assert all(r['via_handover_line']==2 for r in e1 if r['team']=='LINE-B')

def test_handover_during_break_charge_starts_on_resume(raw):
    s=run(raw,{'handover':HANDOVER_CSV.decode()})
    e2=[r for r in s['segments'] if r['employee']=='E002']
    # 02:30 在休息区间内，复工 03:00 后才由 LINE-B 承担 180 分钟
    assert sum(r['minutes'] for r in e2 if r['team']=='LINE-B')==180
    assert sum(r['minutes'] for r in e2 if r['team']=='HOME')==240

def test_team_costs_sum_to_total(raw):
    s=run(raw,{'handover':HANDOVER_CSV.decode()})
    assert s['business']['team_amount']==s['business']['total']
    assert s['business']['team_minutes']==s['business']['minutes']
    assert s['reconcile']['team_cost_balanced'] is True

def test_handover_row_count_conservation(raw):
    s=run(raw,{})
    h=s['reconcile']['handover']
    assert h['balanced']
    assert h['input']==h['accepted']+h['isolated']+h['blank']+h['headers']+h['duplicates']

def test_handover_outside_window_isolated(raw):
    bad=HANDOVER_CSV.decode()+ 'H3,E003,2026-10-01,1,2026-10-01T20:00:00+08:00,LINE-B,early\n'
    s=run(raw,{'handover':bad})
    assert any(q['id']=='H3' and q['code']=='RANGE' for q in s['h_quarantine'])

def test_handover_unknown_shift_isolated(raw):
    bad=HANDOVER_CSV.decode()+ 'H4,E999,2026-10-01,1,2026-10-02T03:00:00+08:00,LINE-B,nobody\n'
    s=run(raw,{'handover':bad})
    assert any(q['id']=='H4' and q['code']=='REFERENCE' for q in s['h_quarantine'])

def test_handover_conflict_group_isolated(raw):
    bad=(HANDOVER_CSV.decode()
        +'H5,E003,2026-10-01,1,2026-10-02T01:00:00+08:00,LINE-B,a\n'
        +'H5,E003,2026-10-01,1,2026-10-02T01:30:00+08:00,LINE-B,b\n')
    s=run(raw,{'handover':bad})
    assert sum(1 for q in s['h_quarantine'] if q['id']=='H5' and q['code']=='CONFLICT')==2

def test_exact_duplicate_handover_collapsed(raw):
    one=HANDOVER_CSV.decode()
    s=run(raw,{'handover':one+one.splitlines()[1]+'\n'})
    assert s['h_duplicate_count']==1

def test_handover_blank_and_header_states():
    with pytest.raises(DomainError) as e:parse_handover(b'')
    assert e.value.code=='EMPTY_FILE'
    with pytest.raises(DomainError) as e:parse_handover(b'\n \n')
    assert e.value.code=='BLANK_FILE'
    header=(','.join(['h_id','employee','shift_day','version','at','to_team','note']))+'\n'
    with pytest.raises(DomainError) as e:parse_handover(header.encode())
    assert e.value.code=='HEADER_ONLY'

def test_bad_handover_header():
    with pytest.raises(DomainError) as e:parse_handover(b'wrong\n1\n')
    assert e.value.code=='HEADER'

def test_changed_handover_changes_run_id(raw):
    # 源数据变化 -> 身份失效 -> 新批次；旧批次不被覆盖
    a=run(raw,{'handover':HANDOVER_CSV.decode()})
    changed=HANDOVER_CSV.decode().replace('00:30','01:00')
    b=run(raw,{'handover':changed})
    assert a['run_id']!=b['run_id']
    # 同输入重跑身份稳定（幂等，不重复累计）
    assert run(raw,{'handover':HANDOVER_CSV.decode()})['run_id']==a['run_id']

def test_identity_includes_handover_hash(raw):
    no_h=identity(raw,{},'');with_h=identity(raw,{},'abc')
    assert no_h!=with_h

def test_evidence_carries_team_and_handover_line(raw):
    s=run(raw,{'handover':HANDOVER_CSV.decode()})
    away=[r for r in s['calculations'] if r['team']=='LINE-B' and r['employee']=='E001']
    assert away and all(r['via_handover_line']==2 for r in away)

def test_archive_contains_handover_evidence(raw):
    from app.modules.m7_archive.export_out import bundle
    import csv,io
    s=run(raw,{})
    rows=list(csv.reader(io.StringIO(bundle(s).lstrip('﻿'))))
    kinds={r[0] for r in rows}
    assert {'交接','交接隔离','班组成本'}<=kinds

def test_dirty_sample_archive_ready(raw):
    s=run(raw,{})
    assert s['archive']['ready'] is True
