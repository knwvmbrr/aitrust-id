"""Execute local acceptance controls and record actual, bounded evidence."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from protocol.reports import write_report
SOURCES=['protocol/author-choice.cjs','protocol/conformance-statement.cjs','protocol/corpus_support.py',
 'scripts/conformance-statement.cjs','scripts/corpus-support.py','scripts/receipt.cjs','scripts/group-receipt.cjs',
 'scripts/verify-consent-conformance.py','scripts/verify-image-provenance-boundary.py',
 'scripts/build-composition-tool.py','scripts/verify-composition-tool.cjs','tools/composition/editor.js',
 'tools/composition/editor.html','spec/image-provenance-boundary.json','tests/author-choice.cjs',
 'tests/conformance-statement.cjs','tests/test_consent_conformance.py','tests/test_corpus_support.py']
COMMANDS=[['node','--test','--test-reporter=tap','tests/author-choice.cjs','tests/conformance-statement.cjs'],
 [sys.executable,'-m','pytest','tests/test_consent_conformance.py','tests/test_corpus_support.py','-q'],
 [sys.executable,'scripts/verify-image-provenance-boundary.py']]
def inventory():return {n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in SOURCES}
def verify():
 before=inventory();checks=[]
 for command in COMMANDS:
  r=subprocess.run(command,cwd=ROOT,capture_output=True,timeout=120)
  checks.append({'command':command,'exit_status':r.returncode,'stdout_sha256':hashlib.sha256(r.stdout).hexdigest(),'stderr_sha256':hashlib.sha256(r.stderr).hexdigest()})
  if r.returncode:break
 return {'captured_at':datetime.now(timezone.utc).isoformat(),'pass':len(checks)==len(COMMANDS) and all(c['exit_status']==0 for c in checks) and before==inventory(),
  'sources':before,'source_unchanged_during_execution':before==inventory(),'checks':checks,
  'scope_ids':['F-128','F-144','X-07','F-020a'],'reference_implementation_only':True,
  'independent_accuracy_evidence':False,'human_accessibility_review':False,'physical_phone_tested':False,
  'certification_operating':False,'institutional_coercion_prevented_outside_software':False,'tag_release_approved':False}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();v=verify();write_report(a.output,v);print(json.dumps(v));raise SystemExit(0 if v['pass'] else 1)
