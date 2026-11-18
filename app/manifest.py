import hashlib,json
from datetime import datetime,timezone
from app.config import RULE_VERSION

def identity(content, parameters, handover_hash=''):
    raw=(content+json.dumps(parameters,sort_keys=True,ensure_ascii=False).encode()
        +RULE_VERSION.encode()+handover_hash.encode())
    return hashlib.sha256(raw).hexdigest()[:20]

def manifest(content, parameters, elapsed, handover_hash=''):
    return {'sha256':hashlib.sha256(content).hexdigest(),
        'handover_sha256':handover_hash,'rule_version':RULE_VERSION,
        'parameters':parameters,'elapsed_ms':round(elapsed*1000),
        'generated_at':datetime.now(timezone.utc).isoformat(),'timezone':'Asia/Shanghai'}
