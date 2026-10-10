"""Cross-implementation subject conformance. No independent accuracy claim."""
import argparse
import base64
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('subjects',ROOT/'protocol/subjects.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def verify():
    vectors=json.loads((ROOT/'eval/vectors/subjects-v1.json').read_text())
    observed=[]
    for v in vectors['vectors']:
        actual=m.text_subject(v['text']) if v['modality']=='text' else m.code_subject(base64.b64decode(v['base64'],validate=True))
        assert actual==v['expected'],v['id']
        observed.append(actual)
    node=shutil.which('node')
    if not node:raise RuntimeError('Node required for second implementation')
    program='''const m=require('./protocol/subjects.cjs');
const v=JSON.parse(require('node:fs').readFileSync(0,'utf8'));
process.stdout.write(JSON.stringify(v.map(x=>x.modality==='text'?m.textSubject(x.text):m.codeSubject(Buffer.from(x.base64,'base64')))));'''
    result=subprocess.run([node,'-e',program],cwd=ROOT,input=json.dumps(vectors['vectors']),capture_output=True,text=True,check=True)
    assert json.loads(result.stdout)==observed
    return {'captured_at':datetime.now(timezone.utc).isoformat(),'pass':True,'contract_version':'subject-v1','vectors':len(observed),'implementations':['Python hashlib/unicodedata','Node crypto/normalize'],'outside_implementer_acceptance':False,'independent_accuracy_evidence':False,'code_gateway_support':False}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path);a=p.parse_args();r=verify()
    if a.output:a.output.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps(r))
