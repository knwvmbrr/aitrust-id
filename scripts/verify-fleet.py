#!/usr/bin/env python3
"""Execute actual opt-in fleet CLI controls; never a commercial or accuracy claim."""
import argparse
from datetime import datetime,timezone
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import platform
import socket
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.dont_write_bytecode=True
from protocol.reports import write_report
from tools.fleet import FILES
SOURCES=tuple(dict.fromkeys(FILES+('tools/fleet.py','scripts/fleet.py','tests/test_fleet.py','scripts/verify-fleet.py',
 'tools/blind_review_io.py','docs/fleet-deployment-plan.md','docs/fleet-deployment.md','eval/requirements.lock',
 'scripts/verify-fleet-linux.py','scripts/verify-fleet-evidence.py','tests/test_fleet_evidence.py',
 'tools/backup_retention.py','deploy/backup/restore.py','protocol/reports.py','.github/workflows/fleet.yml')))
def hashes():return {name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in SOURCES}
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
    spec=importlib.util.spec_from_file_location('fleet_controls',ROOT/'tests/test_fleet.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(module.Fleet);cases=[t.id().split('.')[-1] for t in suite]
    stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite);same=before==hashes()
    row={'format':'fleet-software-engineering/v1','captured_at':datetime.now(timezone.utc).isoformat(),'checked_by':'Codex',
         'pass':result.wasSuccessful() and not result.skipped and same,'platform':sys.platform,'python_version':platform.python_version(),
         'non_root':os.geteuid()!=0,'isolated_network_namespace':isolated(),'source_unchanged':same,'sources':before,
         'cases':cases,'test_count':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),
         'actual_cli_processes':True,'synthetic_credentials_and_inputs_only':True,'enrolled_real_devices':False,
         'production_changed':False,'collection_enabled':False,'commercial_service_activated':False,'independent_accuracy_evidence':False,
         'human_acceptance':False,'physical_phone_tested':False,'scope':'Opt-in approved-source PS development deployment on owner-private macOS/Linux workspaces; no browser force-install or public tag release.'}
    if a.output:write_report(a.output,row)
    print(json.dumps(row))
    if not row['pass']:print(stream.getvalue(),file=sys.stderr)
    return 0 if row['pass'] else 1
if __name__=='__main__':raise SystemExit(main())
