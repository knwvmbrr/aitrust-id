"""Check current documentation ownership and acceptance/count consistency."""
from datetime import datetime, timezone
import argparse
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def verify(root=ROOT):
    roster=json.loads((root/'docs/maintainers.json').read_text())
    if roster.get('schema_version')!=1 or roster.get('accountable_owner')!='Michael':
        raise ValueError('Accountable owner missing or unaccepted')
    if roster.get('institution_operating') is not False or roster.get('response_sla_accepted') is not False or roster.get('tools_are_legal_officers') is not False:
        raise ValueError('Unaccepted institutional representation')
    lanes=roster.get('lanes',[])
    if len(lanes)!=6 or {r['id'] for r in lanes}!={'product','source','security','adapters','operations','independent_review'}:
        raise ValueError('Missing or duplicate responsibility lane')
    for lane in lanes:
        if lane['owner']!=roster['accountable_owner'] or not lane['execution'] or not (root/lane['contract']).is_file():
            raise ValueError('Unassigned responsibility or missing contract')
    if set(roster['handoff_required'])!={'source_revision','files','evidence','remaining_failures','accepted_owner'}:
        raise ValueError('Incomplete handoff contract')
    for name in ('README.md','CHANGELOG.md','MAINTAINERS.md','DECISIONS.md','state.json','docs/changelog-policy.md'):
        if not (root/name).is_file() or not (root/name).read_text().strip():raise ValueError('Missing accountability document')
    if not list((root/'runs/changes').glob('*.json')):raise ValueError('Missing execution records')
    ledger=json.loads((root/'docs/scope-progress.json').read_text())
    state=json.loads((root/'state.json').read_text())
    done=sum(r['percent_complete']==100 for r in ledger['records'])
    if state['scope_completion']['completed_records']!=done or state['scope_completion']['open_records']!=len(ledger['records'])-done:
        raise ValueError('State contradicts acceptance ledger')
    return {'captured_at':datetime.now(timezone.utc).isoformat(),'pass':True,
            'requirements':len(ledger['records']),'completed_records':done,'open_records':len(ledger['records'])-done,
            'named_lanes':len(lanes),'legal_institution_or_sla_claimed':False,
            'independent_accuracy_evidence':False,'owner_availability_verified':False}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path);a=p.parse_args();r=verify()
    if a.output:a.output.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps(r))
