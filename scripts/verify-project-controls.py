"""Validate named responsibility, six invariants and current threat-model traceability.

Checks an accountable documented contract, not owner availability or security certification.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]
HEADINGS=['No paid dependencies.','No network egress at inference.','No response content in assertion records or telemetry.','Accessibility is a gate, not a follow-up.','A tag may not claim more confidence than its evidence supports.','No detection capability is ever withheld from an individual.']
THREATS={'exfiltration','exposure','credentials','hostile_page','supply_chain','evasion','collection','vendor_drift','accessibility','delivery'}

def verify(root=ROOT):
    roster=json.loads((root/'docs/maintainers.json').read_text());lanes={r['id']:r for r in roster['lanes']}
    moment=datetime.fromisoformat(roster['reviewed_at'])
    if moment.tzinfo is None:raise ValueError('Undated responsibility assignment')
    if not roster['accountable_owner'] or roster['response_sla_accepted'] or roster['institution_operating']:raise ValueError('Unaccepted owner or operational representation')
    for lane in ('security','adapters'):
        row=lanes.get(lane)
        if not row or row['owner']!=roster['accountable_owner'] or not row['execution'] or not (root/row['contract']).is_file():raise ValueError('Missing ongoing owner or contract')
    text=(root/'CONTRIBUTING.md').read_text()
    headings=re.findall(r'^([1-6])\. \*\*(.*?)\*\*',text,re.M)
    if headings!=[(str(i+1),name) for i,name in enumerate(HEADINGS)]:raise ValueError('Six invariant headings changed or missing')
    for stale in ('CI runs the test suite with networking disabled','If human annotators only\n   agree at 0.6'):
        if stale in text:raise ValueError('Unsupported evidence or statistical claim')
    threats=json.loads((root/'docs/threat-controls.json').read_text())
    rows=threats['threats']
    if threats['schema_version']!=1 or len(rows)!=10 or {r['id'] for r in rows}!=THREATS:raise ValueError('Incomplete/duplicate threat model')
    for row in rows:
        if not row['control'] or not row['residual'] or row['owner_lane'] not in lanes:raise ValueError('Threat lacks control, residual or owner')
        if not row['evidence'] or any(not (root/p).is_file() for p in row['evidence']):raise ValueError('Missing threat-control evidence')
    expected=render(threats,roster)
    if (root/'THREAT_MODEL.md').read_text()!=expected:raise ValueError('Rendered threat model is stale')
    return {'captured_at':datetime.now(timezone.utc).isoformat(),'pass':True,'named_security_and_adapter_owner':roster['accountable_owner'],'invariants':6,'threats':10,'evidence_paths_checked':sum(len(r['evidence']) for r in rows),'owner_availability_verified':False,'independent_security_certification':False,'tag_release_validated':False}

def render(threats,roster):
    text='''# Threat model

The website runs the PS development preview in an on-device worker; it is not a
public server-side evaluator or research intake. The separate authenticated
local service and Chrome adapter have their own boundaries. Dedicated Linux
staging checks use synthetic input and do not activate remote user collection.

This is a maintainer assessment with ten current entries and named accountable
lanes. It is not independent security certification, a guarantee against host
compromise, or evidence that residual release work is complete. Hashes establish
identity, not truth or anonymity. Changing a control, route or source reopens its
verification. The full model-asset and normalization corrections are recorded
in the referenced execution evidence.

| Threat | Accountable owner / lane | Control and evidence | Residual risk / remaining release work |
|---|---|---|---|
'''
    for row in threats['threats']:
        evidence=', '.join('['+p+']('+p+')' for p in row['evidence'])
        cells=[row['id'],roster['accountable_owner']+' / '+row['owner_lane'],row['control']+'. '+evidence,row['residual']]
        text+='| '+' | '.join(c.replace('|','\\|').replace('\n',' ') for c in cells)+' |\n'
    return text

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--render',action='store_true');p.add_argument('--output',type=Path);a=p.parse_args()
    if a.render:(ROOT/'THREAT_MODEL.md').write_text(render(json.loads((ROOT/'docs/threat-controls.json').read_text()),json.loads((ROOT/'docs/maintainers.json').read_text())))
    r=verify()
    if a.output:a.output.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps(r))
