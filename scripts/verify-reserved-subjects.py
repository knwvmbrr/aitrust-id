#!/usr/bin/env python3
"""Run prepared-artifact conformance; no detector or decoder support is asserted."""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from protocol.reserved_subjects import subject,validate_span
from protocol.reports import write_report
def verify():
    path=ROOT/'eval/vectors/reserved-subjects-v1.json';vectors=json.loads(path.read_text())
    profiles=json.loads((ROOT/'spec/subject-profiles.json').read_text())
    modalities=json.loads((ROOT/'spec/assertion.schema.json').read_text())['properties']['subject']['properties']['modality']['enum']
    if set(profiles['profiles'])!=set(modalities) or profiles['runtime_evaluation_modalities']!=['text']:raise ValueError('Modality reservation drift')
    for modality in modalities:
        profile=profiles['profiles'][modality]
        if not (ROOT/profile['contract_document']).is_file():raise ValueError('Missing modality contract')
        if modality not in ('text','code') and (profile['contract_version']!=vectors['contract_version'] or profile['detector_supported'] or profile['file_decoder_supported']):raise ValueError('Reserved modality overclaim')
    if vectors['contract_version']!='reserved-subject-v1' or vectors['adopted_wire_protocol'] or vectors['detector_support']:raise ValueError('Invalid vector claim')
    for row in vectors['valid']:
        if subject(row['input'])!=row['expected']:raise ValueError('Python golden mismatch '+row['id'])
    for row in vectors['invalid']:
        try:subject(row['input'])
        except (ValueError,UnicodeError):pass
        else:raise ValueError('Python accepted invalid '+row['id'])
    for row in vectors['valid_spans']:
        if validate_span(row['input'],row['span'])!=row['span']:raise ValueError('Python coordinate mismatch')
    for row in vectors['invalid_spans']:
        try:validate_span(row['input'],row['span'])
        except ValueError:pass
        else:raise ValueError('Python accepted invalid coordinate')
    script="""const fs=require('fs'),{subject,validateSpan}=require('./protocol/reserved-subjects.cjs');const v=JSON.parse(fs.readFileSync(0,'utf8'));let rejects=0,spanRejects=0;const outputs=v.valid.map(x=>subject(x.input));for(const x of v.invalid){let failed=false;try{subject(x.input)}catch{failed=true}if(!failed)throw Error('Invalid artifact accepted');rejects++;}const spans=v.valid_spans.map(x=>validateSpan(x.input,x.span));for(const x of v.invalid_spans){let failed=false;try{validateSpan(x.input,x.span)}catch{failed=true}if(!failed)throw Error('Invalid span accepted');spanRejects++;}console.log(JSON.stringify({outputs,spans,rejects,spanRejects}));"""
    done=subprocess.run(['node','-e',script],cwd=ROOT,input=json.dumps(vectors),text=True,capture_output=True,check=True,timeout=30);observed=json.loads(done.stdout)
    if observed['outputs']!=[r['expected'] for r in vectors['valid']] or observed['spans']!=[r['span'] for r in vectors['valid_spans']] or observed['rejects']!=len(vectors['invalid']) or observed['spanRejects']!=len(vectors['invalid_spans']):raise ValueError('Node conformance mismatch')
    used=set();cli_count=0
    for row in vectors['valid']:
        modality=row['input']['modality']
        if modality in used:continue
        used.add(modality);cli_count+=1
        run=subprocess.run([sys.executable,str(ROOT/'scripts/hash-reserved-artifact.py')],cwd=ROOT,input=json.dumps(row['input']),text=True,capture_output=True,timeout=10,check=True)
        if json.loads(run.stdout)!=row['expected']:raise ValueError('CLI conformance mismatch')
    sources=['protocol/reserved_subjects.py','protocol/reserved-subjects.cjs','protocol/normalization.py','protocol/normalization.cjs','protocol/unicode15-data.json','scripts/hash-reserved-artifact.py','scripts/verify-reserved-subjects.py','eval/vectors/reserved-subjects-v1.json','docs/reserved-subject-contract.md','spec/subject-profiles.json']
    return {'captured_at':dt.datetime.now(dt.timezone.utc).isoformat(),'pass':True,'contract_version':vectors['contract_version'],'valid_vectors_per_implementation':len(vectors['valid']),'rejection_vectors_per_implementation':len(vectors['invalid']),'valid_spans_per_implementation':len(vectors['valid_spans']),'invalid_spans_per_implementation':len(vectors['invalid_spans']),'actual_cli_modalities':sorted(used),'actual_cli_checks':cli_count,'source_sha256':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in sources},'file_decoder_support':False,'detector_support':False,'adopted_wire_protocol':False,'outside_implementer_acceptance':False}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',default='output/verification/reserved-subjects.json');a=p.parse_args();result=verify();write_report(ROOT/a.report,result);print(json.dumps(result))
