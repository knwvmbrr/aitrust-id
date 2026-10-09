#!/usr/bin/env python3
"""Compare actual builder outputs across named interpreters in isolated fresh outputs."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
SCRIPT='''
import importlib.util,json,pathlib,sys
spec=importlib.util.spec_from_file_location('builder',sys.argv[1]);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
m.ROOT=pathlib.Path(sys.argv[3]);p=m.ROOT/'services/evaluator/app.py';p.parent.mkdir(parents=True);p.write_bytes(pathlib.Path(sys.argv[2]).read_bytes())
manifest=m.main();print(json.dumps({'version':sys.version.split()[0],'manifest':manifest}))
'''

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--python',action='append',dest='interpreters')
    p.add_argument('--output')
    a=p.parse_args();runs=[];failures=[];expected=json.loads((ROOT/'site/src/device-manifest.json').read_text())
    for interpreter in a.interpreters or [sys.executable]:
        with tempfile.TemporaryDirectory(prefix='aitrust-builder-') as directory:
            result=subprocess.run([interpreter,'-c',SCRIPT,str(ROOT/'scripts/build-device-detector.py'),str(ROOT/'services/evaluator/app.py'),directory],capture_output=True,text=True,timeout=45)
            if result.returncode:
                failures.append('Builder exited '+str(result.returncode)+' for '+Path(interpreter).name);continue
            data=json.loads(result.stdout.splitlines()[-1]);manifest=data['manifest']
            actual=Path(directory)/'site/public'/manifest['path'].lstrip('/')
            if hashlib.sha256(actual.read_bytes()).hexdigest()!=manifest['bundle_sha256']:failures.append('Manifest/file mismatch '+data['version'])
            if manifest!=expected:failures.append('Tracked manifest or cross-builder artifact drift '+data['version'])
            runs.append({'python':data['version'],'bundle_sha256':manifest['bundle_sha256'],'method_sha256':manifest['method_sha256'],'manifest_sha256':hashlib.sha256((Path(directory)/'site/src/device-manifest.json').read_bytes()).hexdigest(),'fresh_output':True,'exit_status':result.returncode})
    report={'captured_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'author':'Codex','pass':not failures and bool(runs),'builders':runs,'errors':failures,'independent_release_validated':False,'limits':'Actual listed Python builders only; no guarantee about future Python unparse behavior or independent detector accuracy'}
    if a.output:(ROOT/a.output).write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2));return 0 if report['pass'] else 1
if __name__=='__main__':raise SystemExit(main())
