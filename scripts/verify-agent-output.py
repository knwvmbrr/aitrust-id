"""Execute or validate source-bound private agent software evidence."""
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools import agent_output as a
from protocol.reports import write_report

PATHS=(*a.SOURCES,'scripts/verify-agent-output.py','tests/test_agent_output.py',
 'docs/agent-output-plan.md','docs/agent-output.md',
 'scripts/check-ps.py','scripts/build-device-detector.py','services/evaluator/app.py',
 'protocol/normalization.py','protocol/unicode15-data.json')
TESTS=33
def hashes():return {name:a.sha(a.read_file(ROOT/name,2_000_000)) for name in PATHS}
def require(ok):
    if not ok:raise ValueError('Agent software evidence refused')

def verify(row,expected_platform):
    require(row['format']=='ai-trust-id-agent-software/v1' and row['platform']==expected_platform)
    require(expected_platform in ('darwin','linux'))
    for k in ('pass','source_unchanged','non_root','synthetic_inputs_only'):require(row[k] is True)
    for k in ('outside_person_acceptance','physical_phone_tested','independent_accuracy_evidence',
              'certification','collection_enabled'):require(row[k] is False)
    require(row['sources']==hashes() and type(row['tests']) is int and row['tests']==TESTS)
    for k in ('failures','errors','skipped','exit'):require(type(row[k]) is int and row[k]==0)
    require(tuple(int(n) for n in row['python_version'].split('.'))>=(3,12))
    require(type(row['node_version']) is str and re.fullmatch(r'v\d+[.]\d+[.]\d+',row['node_version'])
            and int(row['node_version'][1:].split('.')[0])>=22)
    stamp=datetime.fromisoformat(row['captured_at'])
    require(stamp.tzinfo is not None and stamp<=datetime.now(timezone.utc))
    for k in ('stdout_sha256','stderr_sha256'):
        require(type(row[k]) is str and re.fullmatch('[a-f0-9]{64}',row[k]))
    return {'pass':True,'platform':expected_platform,'tests':TESTS,'sources_current':True,
            'outside_person_acceptance':False,'independent_accuracy_evidence':False,'certification':False}

def execute():
    require(sys.platform in ('darwin','linux') and os.getuid()!=0)
    before=hashes();node=shutil.which('node');require(node is not None)
    version=a.clean_worker([node,'--version'],b'',3,256).decode().strip()
    with tempfile.TemporaryDirectory(prefix='aitrust-agent-acceptance-') as directory:
        junit=Path(directory)/'tests.xml'
        r=subprocess.run([sys.executable,'-m','pytest','tests/test_agent_output.py','-q',
                          '--junitxml',str(junit)],cwd=ROOT,capture_output=True,timeout=120)
        suite=ET.parse(junit).getroot()
        cases=suite.findall('.//testcase')
        row={'format':'ai-trust-id-agent-software/v1','captured_at':datetime.now(timezone.utc).isoformat(),
          'platform':sys.platform,'architecture':platform.machine(),'python_version':platform.python_version(),
          'node_version':version,'sources':before,'source_unchanged':before==hashes(),
          'non_root':os.getuid()!=0,'synthetic_inputs_only':True,'tests':len(cases),
          'failures':len(suite.findall('.//failure')),'errors':len(suite.findall('.//error')),
          'skipped':len(suite.findall('.//skipped')),'exit':r.returncode,
          'stdout_sha256':a.sha(r.stdout),'stderr_sha256':a.sha(r.stderr),
          'outside_person_acceptance':False,'physical_phone_tested':False,
          'independent_accuracy_evidence':False,'certification':False,'collection_enabled':False}
        row['pass']=r.returncode==0 and row['source_unchanged'] and len(cases)==TESTS and not any(row[k] for k in ('failures','errors','skipped'))
    if row['pass']:verify(row,sys.platform)
    return row

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execute',action='store_true')
    p.add_argument('--output');p.add_argument('--receipt',type=Path);p.add_argument('--platform',choices=['darwin','linux'])
    args=p.parse_args()
    try:
        if args.execute:row=execute()
        elif args.receipt and args.platform:row=verify(json.loads(args.receipt.read_bytes()),args.platform)
        else:
            checks=[verify(json.loads((ROOT/('runs/2026-11-06-agent-output-'+label+'.json')).read_bytes()),host)
                    for host,label in [('darwin','macos'),('linux','linux')]]
            row={'pass':True,'supported_os_checks':checks,'independent_accuracy_evidence':False,'certification':False}
        if args.output:write_report(args.output,row)
        print(json.dumps(row));return 0 if row.get('pass') is True else 1
    except Exception:
        print('Agent software evidence unavailable; no private diagnostics or release acceptance inferred.',file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
