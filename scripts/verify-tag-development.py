"""Development fixture integrity and unavailable-capability controls, not accuracy."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from protocol.evidence import read_evidence
from protocol.reports import write_report

def verify(folder=None):
    folder=folder or ROOT/'eval/datasets/tag_development'
    manifest=read_evidence(folder/'manifest.json')
    if manifest.get('schema_version')!=1 or manifest.get('dataset_id')!='tag-development/1.0.0' or manifest.get('split')!='development' or any(manifest.get(k) is not False for k in ('independently_labeled','release_holdout','classifier_accuracy_established')):
        raise ValueError('Unaccepted development evidence claim')
    if set(manifest['files'])!={'hp-v1.jsonl','mt-v1.jsonl','fi-v1.jsonl'}:raise ValueError('Missing fixture family')
    spec=importlib.util.spec_from_file_location('development_evaluator',ROOT/'services/evaluator/app.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    total=0;identities=set()
    def unique(pairs):
        value={}
        for key,item in pairs:
            if key in value:raise ValueError('Duplicate fixture field')
            value[key]=item
        return value
    for name,definition in manifest['files'].items():
        file=folder/name
        if file.is_symlink() or file.stat().st_size>100000:raise ValueError('Unsupported fixture source')
        raw=file.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=definition['sha256']:raise ValueError('Fixture identity changed')
        rows=[json.loads(line,object_pairs_hook=unique) for line in raw.decode().splitlines()]
        if len(rows)!=definition['rows'] or len(rows)<10:raise ValueError('Fixture count mismatch')
        for row in rows:
            if set(row)!={'id','tag','category','text','annotation','author','label_status','expected_runtime'} or row['tag']!=definition['tag'] or row['id'] in identities or row['author']!='Codex' or row['label_status']!='synthetic_scenario_intent_not_independent_truth' or row['expected_runtime']!='capability_unavailable' or any(not isinstance(row[k],str) or not row[k] or len(row[k])>2000 for k in row):raise ValueError('Invalid fixture or unsupported provenance')
            identities.add(row['id'])
            result=module.signals(module.Doc(text=row['text']))
            if any(c['code'] in ('HP','MT','FI') for c in result['candidates']):raise ValueError('Development fixtures cannot release an unimplemented tag')
            total+=1
    return {'captured_at':datetime.now(timezone.utc).isoformat(),'pass':True,'dataset_id':manifest['dataset_id'],'rows':total,'families':3,'manifest_sha256':hashlib.sha256((folder/'manifest.json').read_bytes()).hexdigest(),'runtime_unavailable_checked':True,'independent_accuracy_evidence':False,'release_holdout':False,'scope':'Exact versioned development fixtures and current evaluator non-emission; scenario annotations are not detector ground truth.'}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report');a=p.parse_args();r=verify()
    if a.report:write_report(a.report,r)
    print(json.dumps(r))
