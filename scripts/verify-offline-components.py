"""Execute offline component controls and record source-bound engineering evidence."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from protocol.reports import write_report

def sha(raw):return hashlib.sha256(raw).hexdigest()
def inventory():
    names=['protocol/repetition.py','protocol/receipts.cjs','protocol/signals.py',
           'scripts/receipt.cjs','scripts/atomic-output.cjs','scripts/check-repetition.py','scripts/build-composition-tool.py',
           'scripts/verify-tag-development.py','scripts/verify-offline-components.py',
           'scripts/verify-composition-tool.cjs','scripts/verify-dependencies.py',
           'tests/composition-observations.cjs','tests/offline-receipts.cjs',
           'tests/test_tag_development.py','tests/test_repetition_observation.py',
           'tests/test_dependency_contract.py','eval/requirements.lock','eval/requirements.txt',
           'spec/signal-registry.json','protocol/assertions.py','spec/assertion.schema.json']
    names += [p.relative_to(ROOT).as_posix() for pattern in ['tools/composition/*','eval/datasets/tag_development/*'] for p in ROOT.glob(pattern)]
    if any((ROOT/n).is_symlink() for n in names):raise ValueError('Source symlink refused')
    return {n:sha((ROOT/n).read_bytes()) for n in sorted(names)}

def execute():
    before=inventory();commands=[['node','--test','tests/composition-observations.cjs','tests/offline-receipts.cjs'],[sys.executable,'-m','pytest','tests/test_tag_development.py','tests/test_repetition_observation.py','tests/test_dependency_contract.py','-q']]
    checks=[]
    for command in commands:
        r=subprocess.run(command,cwd=ROOT,capture_output=True,timeout=120,env={**os.environ,'AITRUST_VERIFY_PYTHON':sys.executable})
        match=re.search(r'(\d+) passed',r.stdout.decode(errors='replace')) if command[0]==sys.executable else re.search(r'ℹ tests (\d+)',r.stdout.decode(errors='replace'))
        public_command=['{python}' if item==sys.executable else item for item in command]
        checks.append({'command':public_command,'exit':r.returncode,'passed_tests':int(match.group(1)) if match else None,'stdout_sha256':sha(r.stdout),'stderr_sha256':sha(r.stderr)})
        if r.returncode:break
    stable=before==inventory()
    return {'captured_at':datetime.now(timezone.utc).isoformat(),'pass':stable and len(checks)==2 and all(c['exit']==0 and c['passed_tests'] for c in checks),'sources_unchanged':stable,'sources':before,'checks':checks,'receipt_algorithms':['Ed25519','ECDSA-P256-SHA256'],'independent_accuracy_evidence':False,'tag_release_approved':False,'scope':'Executed offline component, synthetic key/receipt CLI, fixture integrity and lock compatibility controls. Browser integration is separately recorded.'}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',default='output/verification/offline-components.json');a=p.parse_args();r=execute();write_report(a.report,r);print(json.dumps(r));sys.exit(0 if r['pass'] else 1)
