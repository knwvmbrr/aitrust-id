#!/usr/bin/env python3
"""Execute or check F-119's bounded software acceptance; never grant human acceptance."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools.conformance_vectors import load,sources,decode,EXITS
from protocol.reports import write_report
EVIDENCE='runs/2026-11-06-conformance-software-execution.json'
EXTRA=('scripts/verify-conformance-delivery.py','services/gateway/requirements.lock','eval/requirements.lock','package-lock.json')

def require(value):
    if not value:raise ValueError('Conformance software acceptance refused')

def identity():return {**sources(),**{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in EXTRA}}

def verify(row):
    require(row['format']=='ai-trust-id-conformance-software-acceptance/v1')
    require(row['pass'] is True and row['source_unchanged'] is True and row['sources']==identity())
    for key in ('outside_person_acceptance','independent_accuracy_evidence','certification','release_approved'):require(row[key] is False)
    when=datetime.fromisoformat(row['captured_at']);require(when.tzinfo is not None and when<=datetime.now(timezone.utc))
    reference=row['reference'];require(reference['pass'] is True and reference['source_unchanged_during_execution'] is True and reference['sources']==sources())
    require(reference['implementation']=='reference' and reference['vector_profile']=='aitrust-assertion-vectors/1.0.0')
    for key in ('outside_person_acceptance','independent_accuracy_evidence','certification','release_approved'):require(reference[key] is False)
    expected=[(case['id'],profile,case['expected'][profile]) for profile in ('schema','extension') for case in load()['cases']]
    checks=reference['checks'];require(len(checks)==28 and [(c['case'],c['profile'],c['expected']) for c in checks]==expected)
    require(reference['cases_run']==reference['cases_passed']==28)
    for c in checks:
        require('failure' not in c and c['pass'] is True and c['observed']==c['expected'] and type(c['exit']) is int and c['exit']==EXITS[c['expected']])
        require(type(c['response_sha256']) is str and len(c['response_sha256'])==64 and all(ch in '0123456789abcdef' for ch in c['response_sha256']))
    focused=row['focused'];require(type(focused['exit']) is int and focused['exit']==0 and type(focused['tests']) is int and focused['tests']==12)
    for key in ('failures','errors','skipped'):require(type(focused[key]) is int and focused[key]==0)
    require(type(row['reference_cli_exit']) is int and row['reference_cli_exit']==0)
    return {'pass':True,'requirement':'F-119','reference_checks':28,'focused_tests':12,'source_bound':True,'outside_person_acceptance':False,'independent_accuracy_evidence':False,'release_approved':False}

def execute():
    before=identity()
    reference=subprocess.run([sys.executable,str(ROOT/'scripts/check-conformance-vectors.py')],cwd=ROOT,capture_output=True,timeout=150,check=False)
    require(reference.returncode==0 and len(reference.stdout)<=2_000_000)
    with tempfile.TemporaryDirectory(prefix='aitrust-conformance-acceptance-') as directory:
        report=Path(directory)/'result.xml'
        result=subprocess.run([sys.executable,'-m','pytest','tests/test_conformance_vectors.py','-q','--junitxml',str(report)],cwd=ROOT,capture_output=True,timeout=180,check=False)
        require(result.returncode==0)
        xml=ET.parse(report).getroot();suites=list(xml.iter('testsuite'))
        counts={key:sum(int(s.attrib.get(key,'0')) for s in suites) for key in ('tests','failures','errors','skipped')}
    row={'format':'ai-trust-id-conformance-software-acceptance/v1','captured_at':datetime.now(timezone.utc).isoformat(),
         'pass':True,'source_unchanged':before==identity(),'sources':before,
         'reference_cli_exit':reference.returncode,'reference':decode(reference.stdout),
         'focused':{**counts,'exit':result.returncode,'stdout_sha256':hashlib.sha256(result.stdout).hexdigest(),'stderr_sha256':hashlib.sha256(result.stderr).hexdigest()},
         'outside_person_acceptance':False,'independent_accuracy_evidence':False,'certification':False,'release_approved':False}
    verify(row);return row

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execute',action='store_true');p.add_argument('--output');a=p.parse_args()
    try:
        row=execute() if a.execute else decode((ROOT/EVIDENCE).read_bytes())
        summary=verify(row)
        if a.output:write_report(a.output,row if a.execute else summary)
        print(json.dumps(summary));return 0
    except (OSError,ValueError,KeyError,TypeError,ET.ParseError,subprocess.SubprocessError):
        print('Conformance software acceptance refused.',file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
