#!/usr/bin/env python3
"""Execute bounded migration controls and bind the exact sources; no accuracy claim."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from protocol.reports import write_report

FILES=('protocol/migration.py','protocol/migration_io.py','protocol/evidence.py',
       'protocol/assertions.py','protocol/replay_identity.py','protocol/corpus.py',
       'scripts/migrate-assertion.py','scripts/verify-assertion-migration.py',
       'scripts/check-assertion.py','scripts/check-ps.py','services/evaluator/app.py',
       'extension/src/shared/contract.js','spec/assertion.schema.json',
       'spec/versions/0.2.0/assertion.schema.json','tests/test_assertion_migration.py',
       'tests/migration-reference.cjs','tests/fixtures/migration/complete.json',
       'tests/fixtures/migration/large-integer.json','tests/fixtures/migration/README.md',
       'docs/protocol-migration-contract.json','docs/protocol-migration-plan.md',
       'docs/assertion-migration.md','eval/requirements.lock','scripts/check-tags.py',
       'scripts/worker_process.py','scripts/aitrust.py','services/gateway/app.py',
       'tests/test_draft_privacy.py','tests/test_gateway_integration.py',
       'tests/test_gateway_cancellation.py','tests/test_local_cli.py','tests/replay_fixture.py')

def sources():
    return {p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in FILES}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report',required=True)
    args=parser.parse_args()
    before=sources()
    command=[sys.executable,'-m','unittest','discover','-s','tests','-p','test_assertion_migration.py','-v']
    commands=[command,[sys.executable,'-m','pytest',
        'tests/test_draft_privacy.py::test_privacy_uses_only_redactor_and_exact_identity',
        'tests/test_draft_privacy.py::test_privacy_never_bypasses_existing_controls','-q']]
    checks=[]
    for current in commands:
        result=subprocess.run(current,cwd=ROOT,capture_output=True,timeout=90)
        checks.append({'command':['{python}',*current[1:]],'exit_code':result.returncode,
                       'stdout_sha256':hashlib.sha256(result.stdout).hexdigest(),
                       'stderr_sha256':hashlib.sha256(result.stderr).hexdigest()})
        if result.returncode:
            sys.stderr.buffer.write(result.stderr);sys.stderr.buffer.write(result.stdout);break
    stable=before==sources()
    record={'format':'assertion-migration-execution/v1','captured_at':datetime.now(timezone.utc).isoformat(),
            'pass':len(checks)==len(commands) and all(c['exit_code']==0 for c in checks) and stable,'sources':before,'source_unchanged_during_execution':stable,
            'checks':checks,'exit_code':result.returncode,
            'synthetic_protocol_vectors_only':True,'independent_accuracy_evidence':False,
            'privacy_gateway_uses_synthetic_upstream':True,'actual_recognizer_accuracy_measured':False,
            'production_version_changed':False,'release_approved':False}
    write_report(args.report,record)
    print(json.dumps(record))
    return 0 if record['pass'] else 1

if __name__=='__main__':raise SystemExit(main())
