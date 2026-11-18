import time,importlib,json,base64,hashlib
from pathlib import Path
from app.config import MODULES,HANDOVER_SAMPLE
from app.errors import DomainError
from app.manifest import identity,manifest

SAMPLES=('dirty.csv','clean.csv','legacy.csv')
# 交接原始字节在流水线内的私有通道；不进任何持久化结果，仅参与身份与解析
RAW_HANDOVER_KEY='_handover_raw'

def load(sample):
    if sample not in SAMPLES and sample not in ('handovers_dirty.csv','handovers.csv'):
        raise DomainError('SAMPLE','样例名称无效')
    return (Path(__file__).resolve().parents[1]/'sample_data'/sample).read_bytes()

def resolve_handover(params):
    """返回交接源字节。显式 handover=None/'' 表示本批无交接；默认随批带交接样例。"""
    if not isinstance(params,dict) or 'handover' not in params:
        return load(HANDOVER_SAMPLE)
    value=params['handover']
    if value is None or value=='':return None
    if isinstance(value,str) and value in ('handovers_dirty.csv','handovers.csv'):
        return load(value)
    if isinstance(value,str):return value.encode('utf-8')
    raise DomainError('PARAMETERS','交接数据必须是文本或样例名')

def run(content,parameters=None,stage=None):
    if len(content)>2_000_000:raise DomainError('SIZE','文件超过2MB',413)
    params=dict(parameters or {})
    if not isinstance(parameters,dict) and parameters is not None:
        raise DomainError('PARAMETERS','参数必须是对象')
    handover_raw=resolve_handover(params)
    params.pop('handover',None)
    start=time.monotonic();state=None;limit=len(MODULES) if stage is None else stage
    for n,entry in enumerate(MODULES,1):
        if n>limit:break
        module=importlib.import_module('app.modules.'+entry[0]+'.service')
        if entry[0]=='m3b_handovers':state[RAW_HANDOVER_KEY]=handover_raw
        state=module.execute(content,params) if n==1 else module.execute(state)
    # Decimal values are serialized as strings before any storage or response.
    state=json.loads(json.dumps(state,default=str,ensure_ascii=False))
    handover_hash=hashlib.sha256(handover_raw).hexdigest() if handover_raw else ''
    state['run_id']=identity(content,params,handover_hash)
    state['manifest']=manifest(content,params,time.monotonic()-start,handover_hash)
    state['source_b64']=base64.b64encode(content).decode('ascii')
    if stage is None or stage>=len(MODULES):
        from app.modules.m7_archive.export_out import checksum
        state['archive']['sha256']=checksum(state)
    return state
