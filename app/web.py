import base64
from flask import request,render_template,jsonify
from app.errors import DomainError
from app.config import TITLE,MODULES,SHORT
from app.workflow import run,load
from app import store

def payload():
    data=request.get_json(silent=True) or {}
    if not isinstance(data,dict):raise DomainError('PAYLOAD','请求必须是对象')
    if 'csv' in data and not isinstance(data['csv'],str):raise DomainError('CSV','CSV内容必须是文本')
    if 'handover' in data and data['handover'] is not None and not isinstance(data['handover'],str):
        raise DomainError('CSV','交接内容必须是文本')
    sample=data.get('sample',request.args.get('sample','dirty.csv'))
    content=data.get('csv')
    parameters=data.get('parameters',{}) or {}
    if 'handover' in data:parameters=dict(parameters);parameters['handover']=data['handover']
    return (content.encode() if isinstance(content,str) else load(sample)),parameters

def api(stage):
    content,parameters=payload();return jsonify(run(content,parameters,stage))

def page(stage,template):
    latest=store.history();state=store.get(latest[0]['id']) if latest else run(load('dirty.csv'),{})
    if 'sample' in request.args:
        source=load(request.args['sample'])
    elif state.get('source_b64'):
        source=base64.b64decode(state['source_b64'])
    else:
        source=load('dirty.csv')
    parameters=dict(state.get('manifest',{}).get('parameters',{}))
    # 交接源以哈希登记在清单中，同哈希样例可原样重放；无哈希表示该批无交接
    h_hash=state.get('manifest',{}).get('handover_sha256','')
    if h_hash:
        from app.config import HANDOVER_SAMPLES
        from hashlib import sha256
        for name in HANDOVER_SAMPLES:
            if sha256(load(name)).hexdigest()==h_hash:parameters['handover']=name;break
        else:parameters['handover']=''  # 自定义交接源无法从页面重放，回退为无交接并产生新批次
    elif 'handover' not in parameters:
        parameters['handover']=''
    data=run(source,parameters,stage)
    return render_template(template,title=TITLE,short=SHORT,modules=MODULES,current=stage,data=data,run=state,history=latest)
