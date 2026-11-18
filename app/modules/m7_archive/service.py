from app.modules.m7_archive.export_out import checksum

def execute(state):
    state['archive']={'sha256':checksum(state),
        'evidence_count':len(state.get('calculations',[]))+len(state['quarantine'])+len(state.get('h_quarantine',[])),
        'ready':state.get('reconcile',{}).get('balanced',False)
            and state.get('reconcile',{}).get('handover',{}).get('balanced',True)
            and state.get('reconcile',{}).get('team_cost_balanced',True)}
    return state
