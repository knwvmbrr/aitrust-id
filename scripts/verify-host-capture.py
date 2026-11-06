#!/usr/bin/env python3
"""Execute synthetic foreground adapter controls; no independent accuracy claim."""
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
from tools.host_capture import CORE_SOURCES,PS_SOURCES
from protocol.reports import write_report
SOURCES=CORE_SOURCES+PS_SOURCES+('tests/test_host_capture.py','scripts/verify-host-capture.py','docs/host-capture.md')

def hashes():return {name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in SOURCES}

def isolated():
    """Only report kernel namespace isolation when loopback is the sole interface."""
    if sys.platform!='linux':return False
    if {name for _,name in socket.if_nameindex()}!={'lo'}:return False
    for family,address in ((socket.AF_INET,('192.0.2.1',443)),(socket.AF_INET6,('2001:db8::1',443,0,0))):
        try:
            with socket.socket(family,socket.SOCK_STREAM) as client:
                client.settimeout(.2)
                if client.connect_ex(address)==0:return False
        except OSError:pass
    return True

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output');a=p.parse_args()
    before=hashes();spec=importlib.util.spec_from_file_location('test_host_capture',ROOT/'tests/test_host_capture.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(module.HostCapture)
    cases=[test.id().split('.')[-1] for test in suite];stream=io.StringIO()
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    same=before==hashes()
    row={'format':'ai-trust-id-host-capture-engineering/v1','captured_at':datetime.now(timezone.utc).isoformat(),
        'pass':result.wasSuccessful() and not result.skipped and same,'platform':sys.platform,
        'python_version':platform.python_version(),'non_root':os.geteuid()!=0,
        'isolated_network_namespace':isolated(),'actual_foreground_pty':True,
        'test_count':result.testsRun,'cases':cases,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),
        'source_unchanged':same,'sources':before,'synthetic_inputs_only':True,'automatic_upload':False,
        'independent_accuracy_evidence':False,'human_acceptance_complete':False,'physical_phone_tested':False,
        'company_collection_enabled':False,'scope':'Foreground owner-selected text-file adapter only; fault-injected child failures are engineering controls.'}
    if a.output:write_report(a.output,row)
    print(json.dumps(row))
    if not row['pass']:print(stream.getvalue(),file=sys.stderr)
    return 0 if row['pass'] else 1
if __name__=='__main__':raise SystemExit(main())
