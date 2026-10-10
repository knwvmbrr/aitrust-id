"""Check current documentation ownership and acceptance/count consistency."""
from datetime import datetime, timezone
import argparse
import json
import re
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from protocol.evidence import read_evidence

def state_chronology(state,root=ROOT):
    now=datetime.now(timezone.utc)
    def moment(value):
        if not isinstance(value,str):raise ValueError("Invalid state evidence timestamp")
        try:parsed=datetime.fromisoformat(value)
        except ValueError:raise ValueError("Invalid state evidence timestamp") from None
        if parsed.tzinfo is None or parsed>now:raise ValueError("Naive or future state evidence timestamp")
        return parsed
    updated=moment(state.get("updated"));updated_at=moment(state.get("updated_at"))
    if updated!=updated_at:raise ValueError("State timestamps disagree")
    def references(value):
        if isinstance(value,dict):
            for child in value.values():yield from references(child)
        elif isinstance(value,list):
            for child in value:yield from references(child)
        elif isinstance(value,str) and value.startswith("runs/") and value.endswith(".json"):yield value
    paths=sorted(set(references(state)));timed=0;untimed=0;latest=None
    for name in paths:
        if not re.fullmatch(r"runs/[A-Za-z0-9_./-]+\.json",name) or ".." in Path(name).parts:raise ValueError("Unsafe state evidence reference")
        file=root/name
        for part in [file,*file.parents]:
            if part==root:break
            if part.is_symlink():raise ValueError("State evidence symlink refused")
        if not file.is_file():raise ValueError("Missing state evidence reference")
        receipt=read_evidence(file)
        if not isinstance(receipt,dict):raise ValueError("Invalid state evidence record")
        stamps=[moment(receipt[key]) for key in ("captured_at","recorded_at") if key in receipt]
        if not stamps:untimed+=1;continue
        timed+=1;captured=max(stamps)
        if updated<captured:raise ValueError("State timestamp predates referenced evidence: "+name)
        latest=max(latest,captured) if latest else captured
    return {"state_evidence_references":len(paths),"timed_evidence_references":timed,"untimed_evidence_references":untimed,"latest_referenced_timestamp":latest.isoformat() if latest else None,"state_chronology_verified":True}
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
    chronology=state_chronology(state,root)
    done=sum(r['percent_complete']==100 for r in ledger['records'])
    if state['scope_completion']['completed_records']!=done or state['scope_completion']['open_records']!=len(ledger['records'])-done:
        raise ValueError('State contradicts acceptance ledger')
    target=state['scope_completion'].get('target_open_records')
    if (type(target) is not int or not 0<=target<=len(ledger['records'])
        or state['scope_completion'].get('target_remaining_closures')!=max(0,len(ledger['records'])-done-target)):
        raise ValueError('Scope target or remaining closures contradicts acceptance ledger')
    return {'captured_at':datetime.now(timezone.utc).isoformat(),'pass':True,
            'requirements':len(ledger['records']),'completed_records':done,'open_records':len(ledger['records'])-done,
            'named_lanes':len(lanes),'legal_institution_or_sla_claimed':False,
            'independent_accuracy_evidence':False,'owner_availability_verified':False,**chronology}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path);a=p.parse_args();r=verify()
    if a.output:a.output.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps(r))
