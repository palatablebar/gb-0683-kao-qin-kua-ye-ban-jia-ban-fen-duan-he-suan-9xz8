from app.config import MODULES

def test_all_module_apis(client):
    for mod,_ in MODULES:assert client.get('/api/'+mod).status_code==200
def test_all_module_pages(client):
    for mod,_ in MODULES:assert client.get('/'+mod).status_code==200
def test_run_and_export(client):
    r=client.post('/api/runs',json={'sample':'dirty.csv'});assert r.status_code==200
    s=r.get_json();e=client.get('/api/archive/'+s['run_id']+'/export.csv');assert e.status_code==200 and '运行清单' in e.data.decode('utf-8-sig')
def test_idempotent_api(client):
    a=client.post('/api/runs',json={}).get_json();b=client.post('/api/runs',json={}).get_json()
    assert a['run_id']==b['run_id'] and len(client.get('/api/runs').get_json())==1
def test_bad_sample(client):
    r=client.post('/api/runs',json={'sample':'../x'});assert r.status_code==422 and r.get_json()['code']=='SAMPLE'
def test_missing_batch(client):
    assert client.get('/api/runs/absent').status_code==404
def test_bad_file(client):
    r=client.post('/api/runs',json={'csv':'wrong\n1\n'});assert r.status_code==422 and r.get_json()['code']=='HEADER'


def test_custom_source_is_visible_after_run(client):
    from app.workflow import load
    raw=load('clean.csv').decode('utf-8-sig');submitted=client.post('/api/runs',json={'csv':raw,'parameters':{}}).get_json()
    from app.config import MODULES
    page=client.get('/'+MODULES[0][0]);assert submitted['run_id'] in page.data.decode()

def test_reselect_existing_run_updates_visible_batch(client):
    a=client.post('/api/runs',json={'sample':'dirty.csv'}).get_json();b=client.post('/api/runs',json={'sample':'clean.csv'}).get_json();client.post('/api/runs',json={'sample':'dirty.csv'})
    assert client.get('/api/runs').get_json()[0]['id']==a['run_id'] and a['run_id']!=b['run_id']

def test_invalid_csv_type_rejected(client):
    assert client.post('/api/runs',json={'csv':123}).status_code==422

def test_handover_submission_splits_team_cost(client):
    handover=('h_id,employee,shift_day,version,at,to_team,note\n'
        'H1,E001,2026-10-01,1,2026-10-02T00:30:00+08:00,LINE-B,x\n')
    r=client.post('/api/runs',json={'sample':'dirty.csv','handover':handover})
    assert r.status_code==200
    s=r.get_json();teams={t['team']:t for t in s['team_totals']}
    assert 'LINE-B' in teams and s['business']['team_amount']==s['business']['total']

def test_handover_change_invalidates_old_run_without_double_count(client):
    h1=('h_id,employee,shift_day,version,at,to_team,note\n'
        'H1,E001,2026-10-01,1,2026-10-02T00:30:00+08:00,LINE-B,x\n')
    h2=h1.replace('00:30','01:00')
    a=client.post('/api/runs',json={'sample':'dirty.csv','handover':h1}).get_json()
    b=client.post('/api/runs',json={'sample':'dirty.csv','handover':h2}).get_json()
    assert a['run_id']!=b['run_id']
    # 再跑一次 h1：身份复用旧批次，库中不新增、不累计
    again=client.post('/api/runs',json={'sample':'dirty.csv','handover':h1}).get_json()
    ids=[r['id'] for r in client.get('/api/runs').get_json()]
    assert again['run_id']==a['run_id'] and ids.count(a['run_id'])==1

def test_no_handover_run_is_separate_identity(client):
    a=client.post('/api/runs',json={'sample':'dirty.csv'}).get_json()
    b=client.post('/api/runs',json={'sample':'dirty.csv','handover':''}).get_json()
    assert a['run_id']!=b['run_id']

def test_handover_pages_render(client):
    from app.config import MODULES
    for mod in ('m3b_handovers','m4_segments','m5_calculate','m6_reconcile'):
        assert client.get('/'+mod).status_code==200
    assert len(MODULES)==8

def test_bad_handover_type_rejected(client):
    assert client.post('/api/runs',json={'sample':'dirty.csv','handover':123}).status_code==422
