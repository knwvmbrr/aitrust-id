#!/usr/bin/env python3
"""Execute real private hash-inbox software controls without collecting real feedback."""
import argparse,hashlib,importlib.util,io,json,os,platform,socket,sys,unittest
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.dont_write_bytecode=True
from protocol.reports import write_report
SOURCES=('tools/hash_reports.py','scripts/hash-reports.py','tests/test_hash_reports.py','scripts/verify-hash-reports.py',
 'scripts/verify-hash-reports-linux.py','scripts/verify-hash-reports-evidence.py','tests/test_hash_reports_evidence.py',
 'tools/blind_review_io.py','protocol/reports.py','protocol/evidence.py','docs/hash-report-intake-plan.md','docs/hash-report-intake.md',
 'scripts/check-ps.py','scripts/build-device-detector.py','scripts/worker_process.py','services/evaluator/app.py',
 'protocol/normalization.py','protocol/normalization-core.js','protocol/unicode15-data.json',
 'tools/backup_retention.py','deploy/backup/restore.py','.github/workflows/hash-reports.yml')
def hashes():return {n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in SOURCES}
def isolated():
    if sys.platform!='linux' or {n for _,n in socket.if_nameindex()}!={'lo'}:return False
    for family,address in [(socket.AF_INET,('192.0.2.1',443)),(socket.AF_INET6,('2001:db8::1',443,0,0))]:
        try:
            with socket.socket(family,socket.SOCK_STREAM) as s:
                s.settimeout(.2)
                if s.connect_ex(address)==0:return False
        except OSError:pass
    return True
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output');a=p.parse_args();before=hashes()
    spec=importlib.util.spec_from_file_location('hash_report_controls',ROOT/'tests/test_hash_reports.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(module.HashReports);cases=[t.id().split('.')[-1] for t in suite];stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite);same=before==hashes()
    import sqlite3
    row={'format':'private-hash-inbox-engineering/v1','captured_at':datetime.now(timezone.utc).isoformat(),'checked_by':'Codex','pass':result.wasSuccessful() and not result.skipped and same,
         'platform':sys.platform,'python_version':platform.python_version(),'sqlite_version':sqlite3.sqlite_version,'non_root':os.geteuid()!=0,
         'isolated_network_namespace':isolated(),'source_unchanged':same,'sources':before,'cases':cases,'test_count':result.testsRun,
         'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'actual_cli_processes':True,'synthetic_hash_feedback_only':True,
         'company_collection_enabled':False,'public_registry_enabled':False,'production_changed':False,'automatic_forwarding':False,
         'real_user_feedback_collected':False,'training_labels_created':False,'independent_accuracy_evidence':False,'human_acceptance':False,
         'scope':'Owner-private local software intake only; not a public registry, research pilot, moderation service or detector verdict.'}
    if a.output:write_report(a.output,row)
    print(json.dumps(row))
    if not row['pass']:print(stream.getvalue(),file=sys.stderr)
    return 0 if row['pass'] else 1
if __name__=='__main__':raise SystemExit(main())
