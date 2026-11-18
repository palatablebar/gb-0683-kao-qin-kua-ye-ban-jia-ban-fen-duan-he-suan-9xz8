from decimal import Decimal

def handover_balance(state):
    """交接源行数守恒：输入=采纳+隔离+空行+重复表头+完全重复。"""
    accepted=len(state.get('handovers',[]))
    accounted=(accepted+len(state.get('h_quarantine',[]))+state.get('h_blank_count',0)
        +state.get('h_header_count',0)+state.get('h_duplicate_count',0))
    return {'input':state.get('h_input_count',0),'accepted':accepted,
        'isolated':len(state.get('h_quarantine',[])),'blank':state.get('h_blank_count',0),
        'headers':state.get('h_header_count',0),'duplicates':state.get('h_duplicate_count',0),
        'accounted':accounted,'balanced':accounted==state.get('h_input_count',0)}

def balance(state):
    accepted=len(state['rows']);isolated=len(state['quarantine'])
    accounted=accepted+isolated+state['blank_count']+state['header_count']+state['duplicate_count']
    business=state.get('business',{})
    team_balanced=(not business) or business.get('team_amount')==business.get('total') \
        and business.get('team_minutes')==business.get('minutes')
    return {'input':state['input_count'],'accepted':accepted,'isolated':isolated,
        'blank':state['blank_count'],'headers':state['header_count'],'duplicates':state['duplicate_count'],
        'accounted':accounted,'balanced':accounted==state['input_count'],
        'handover':handover_balance(state),'team_cost_balanced':team_balanced,
        'business':business}
