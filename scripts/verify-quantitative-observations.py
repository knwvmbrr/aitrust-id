#!/usr/bin/env python3
"""Run actual quantitative CLI controls, optionally in an offline Linux namespace."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from protocol.reports import write_report
PROGRESS={'current_case':'namespace_boundary','completed_cases':[]}
OUTPUT=None


def main():
    global OUTPUT
    PROGRESS.update(current_case='namespace_boundary',completed_cases=[])
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--require-isolated-linux',action='store_true')
    parser.add_argument('--output');args=parser.parse_args();OUTPUT=args.output
    isolated=False
    if args.require_isolated_linux:
        if sys.platform!='linux' or os.geteuid()==0:raise ValueError('Require ordinary-user Linux namespace.')
        devices={line.split(':')[0].strip() for line in Path('/proc/net/dev').read_text().splitlines() if ':' in line}
        if devices!={'lo'} or len(Path('/proc/net/route').read_text().splitlines())>1:
            raise ValueError('Require a separate network namespace before checking egress.')
        try:
            with socket.create_connection(('1.1.1.1',443),timeout=.5):
                raise ValueError('Expected offline namespace.')
        except OSError:isolated=True
    paths=['tools/quantitative_observations.py','tools/language_observations.py',
        'protocol/normalization.py','protocol/unicode15-data.json','protocol/corpus.py',
        'protocol/reports.py','scripts/quantitative-observations.py','scripts/verify-quantitative-observations.py']
    inventory=lambda:{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths}
    before=inventory();cases=[]
    def check(name,raw,code,expected,extra=()):
        PROGRESS['current_case']=name
        result=subprocess.run([sys.executable,str(ROOT/'scripts/quantitative-observations.py'),
            '--language','en',*extra],input=raw,capture_output=True,timeout=5)
        assert result.returncode==code and not result.stderr
        assert b'PRIVATE_QUANTITATIVE_CANARY' not in result.stdout
        value=json.loads(result.stdout)
        assert all(value.get(k)==v for k,v in expected.items()) and value['tags']==[]
        assert value['truth_established'] is False
        cases.append({'case':name,'pass':True});PROGRESS['completed_cases'].append(name);return value
    check('plain_counts_no_private_text_or_details',b'PRIVATE_QUANTITATIVE_CANARY reports 12 items.',0,
        {'supported_detail_count':1,'without_same_unit_marker':1})
    check('grouping_decimal_and_date_shape',b'There are 1,250.50 items. Date: 2026-10-11.',0,{'supported_detail_count':2})
    check('markers_excluded_and_same_unit_only',b'There are 12 items [1]. Another has 25. https://example.invalid/2026.',0,
        {'supported_detail_count':2,'with_same_unit_marker':1,'without_same_unit_marker':1})
    check('identifiers_ip_and_broken_grouping',b'ID123 abc-123 192.0.2.1 12,34.',0,{'supported_detail_count':0})
    check('non_ascii_boundary_refusal','é123 表456 78\u0301 90\u00a0'.encode(),0,{'supported_detail_count':0,'skipped_detail_count':4})
    for name,raw in [('invalid_utf8',b'\xff PRIVATE_QUANTITATIVE_CANARY'),
                     ('nul_input',b'PRIVATE_QUANTITATIVE_CANARY\0'),('byte_limit',b'x'*32001),
                     ('detail_limit',b' '.join(b'12' for _ in range(257)))]:
        check(name,raw,2,{'state':'UNAVAILABLE'})
    with tempfile.TemporaryDirectory(prefix='aitrust-quantitative-private-') as directory:
        report=Path(directory).resolve()/'details.json'
        check('explicit_private_details',b'Cafe\xcc\x81 reports 12.5%.',0,{'private_report_saved':True},('--private-report',str(report)))
        PROGRESS['current_case']='private_report_permissions_and_normalized_span'
        assert report.stat().st_mode&0o777==0o600
        detail=json.loads(report.read_text());assert detail['details'][0]['span']==[13,18]
        assert 'PRIVATE_QUANTITATIVE_CANARY' not in report.read_text()
        original=report.read_bytes()
        check('private_export_never_overwrites',b'There are 25.',2,{'state':'UNAVAILABLE'},('--private-report',str(report)))
        assert report.read_bytes()==original
    assert before==inventory()
    record={'captured_at':datetime.now(timezone.utc).isoformat(),'pass':True,'cases':cases,
        'case_count':len(cases),'sources':before,'source_unchanged_during_execution':True,
        'isolated_linux':isolated,'external_canary_blocked':True if isolated else None,
        'nonroot_execution':os.geteuid()!=0,'only_authored_synthetic_inputs':True,
        'tag_assertions':0,'independent_accuracy_evidence':False}
    if args.output:write_report(args.output,record,root=ROOT)
    print(json.dumps(record,indent=2))


if __name__=='__main__':
    try:main()
    except (ValueError,OSError,AssertionError,subprocess.SubprocessError) as error:
        failure={'captured_at':datetime.now(timezone.utc).isoformat(),'pass':False,
            **PROGRESS,'failure_kind':type(error).__name__,'independent_accuracy_evidence':False}
        if OUTPUT:write_report(OUTPUT,failure,root=ROOT)
        print('Quantitative CLI verification failed; no release acceptance.',file=sys.stderr)
        raise SystemExit(1)
