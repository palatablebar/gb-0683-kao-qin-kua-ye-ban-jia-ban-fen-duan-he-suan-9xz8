import csv,io
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from app.config import HANDOVER_REQUIRED
from app.errors import DomainError
from app.modules.m1_ingest.decode import decode
from app.modules.m2_mapping.coerce import number,day,instant,SENTINELS
from app.modules.m3_versions.rules import ZONE

def parse_handover(raw):
    """交接源是独立第二数据源，沿用编码回退、列数隔离、空态与哨兵约定。"""
    if raw is None:
        return {'h_rows':[],'h_quarantine':[],'h_input_count':0,'h_blank_count':0,
            'h_header_count':0,'h_duplicate_count':0,'h_encoding':'-'}
    text,encoding=decode(raw)
    if not text:raise DomainError('EMPTY_FILE','交接文件为空')
    if not text.strip():raise DomainError('BLANK_FILE','交接文件仅含空行')
    reader=csv.reader(io.StringIO(text,newline=''))
    try:header=[s.strip().lstrip('﻿') for s in next(reader)]
    except (StopIteration,csv.Error):raise DomainError('HEADER','交接表头无法读取')
    if len(set(header))!=len(header) or not set(HANDOVER_REQUIRED)<=set(header):
        raise DomainError('HEADER','交接表头缺失或重复')
    out={'h_rows':[],'h_quarantine':[],'h_input_count':0,'h_blank_count':0,
        'h_header_count':0,'h_duplicate_count':0,'h_encoding':encoding}
    try:
        for row in reader:
            out['h_input_count']+=1;line=reader.line_num
            if not row or not any(s.strip() for s in row):out['h_blank_count']+=1;continue
            if [s.strip() for s in row]==header:out['h_header_count']+=1;continue
            if len(row)!=len(header):
                out['h_quarantine'].append({'line':line,'id':'','code':'WIDTH','raw':row});continue
            item=dict(zip(header,row));item['_line']=line;item['_raw']=dict(item);out['h_rows'].append(item)
    except csv.Error as exc:raise DomainError('CSV',str(exc))
    if out['h_input_count']==0:raise DomainError('HEADER_ONLY','交接文件仅含表头')
    return out

def normalize_rows(parsed):
    """逐行字段校验 + (h_id,version) 重复键：完全相同去重，内容冲突整组隔离。"""
    good=[];groups=defaultdict(list)
    for row in parsed['h_rows']:
        try:
            for field in HANDOVER_REQUIRED:
                if str(row.get(field,'')).strip().upper() in SENTINELS:
                    raise DomainError('MISSING','交接必填值缺失')
            item=dict(row)
            item['version']=number(item['version'])
            if item['version']<0:raise DomainError('NUMBER','交接版本无效')
            item['shift_day']=day(item['shift_day'])
            item['at']=instant(item['at'])
            team=str(item['to_team']).strip()
            if not team or len(team)>32:raise DomainError('RANGE','接收班组无效')
            item['to_team']=team
            groups[(item['h_id'],str(item['version']))].append(item)
        except DomainError as error:
            parsed['h_quarantine'].append({'line':row['_line'],'id':row.get('h_id',''),
                'code':error.code,'raw':row['_raw']})
    for key,rows in groups.items():
        signature={str(sorted((k,str(v)) for k,v in r.items() if not k.startswith('_'))) for r in rows}
        if len(signature)>1:
            for r in rows:parsed['h_quarantine'].append({'line':r['_line'],'id':r['h_id'],
                'code':'CONFLICT','raw':r['_raw']})
        else:
            good.append(rows[0]);parsed['h_duplicate_count']+=len(rows)-1
    parsed['h_rows']=good
    return parsed

def bind_to_shifts(state):
    """交接必须落在所指班次的实际打卡窗口内；同班交接时刻升序、不得重复。"""
    index={(s['employee'],s['day']):s for s in state['shifts']}
    grouped=defaultdict(list)
    for r in state['h_rows']:grouped[(r['employee'],r['shift_day'])].append(r)
    kept=[]
    for key,rows in sorted(grouped.items()):
        shift=index.get(key)
        if shift is None or shift['in'] is None or shift['out'] is None:
            for r in rows:state['h_quarantine'].append({'line':r['_line'],'id':r['h_id'],
                'code':'REFERENCE','raw':r['_raw']})
            continue
        start=datetime.fromisoformat(shift['in']['at']);end=datetime.fromisoformat(shift['out']['at'])
        bad=False;seen=set()
        for r in rows:
            at=datetime.fromisoformat(r['at'])
            if not (start<at<end) or at in seen:bad=True
            seen.add(at)
        if bad:
            for r in rows:state['h_quarantine'].append({'line':r['_line'],'id':r['h_id'],
                'code':'RANGE','raw':r['_raw']})
            continue
        rows.sort(key=lambda r:r['at'])
        for r in rows:
            local=datetime.fromisoformat(r['at']).astimezone(ZONE)
            kept.append({'h_id':r['h_id'],'employee':r['employee'],'shift_day':r['shift_day'],
                'version':str(r['version']),'at':r['at'],'at_local':local.isoformat(),
                'to_team':r['to_team'],'line':r['_line']})
    state['handovers']=kept
    by_shift=defaultdict(list)
    for h in kept:by_shift[(h['employee'],h['shift_day'])].append(h)
    for s in state['shifts']:s['handovers']=by_shift.get((s['employee'],s['day']),[])
    return state

def apply(state):
    parsed=normalize_rows(parse_handover(state.pop('_handover_raw',None)))
    for k,v in parsed.items():state[k]=v
    return bind_to_shifts(state)
