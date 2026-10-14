#!/usr/bin/env python3
"""Compare real isolated PS child results with preserved authored development fixtures."""
from datetime import datetime,timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from protocol.reports import write_report
from protocol.normalization import normalize_nfc


def verify():
    spec=importlib.util.spec_from_file_location('standalone',ROOT/'scripts/check-ps.py')
    ps=importlib.util.module_from_spec(spec);spec.loader.exec_module(ps)
    spec=importlib.util.spec_from_file_location('original',ROOT/'services/evaluator/app.py')
    original=importlib.util.module_from_spec(spec);spec.loader.exec_module(original)
    folder=ROOT/'eval/datasets/unsafe_code'
    manifest=json.loads((folder/'manifest.json').read_text())
    names=['scripts/check-ps.py','scripts/worker_process.py','scripts/verify-standalone-ps.py',
           'scripts/build-device-detector.py','services/evaluator/app.py',
           'protocol/normalization.py','protocol/unicode15-data.json',
           'eval/datasets/unsafe_code/manifest.json']+['eval/datasets/unsafe_code/'+r['file'] for r in manifest['active']]
    before={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in names}
    count=0;findings=0
    for entry in manifest['active']:
        file=folder/entry['file']
        if hashlib.sha256(file.read_bytes()).hexdigest()!=entry['sha256']:raise ValueError('Fixture identity changed')
        for line in file.read_text().splitlines():
            fixture=json.loads(line);text=fixture['text']
            row=ps.check(text)
            expected=original.signals(original.Doc(text=normalize_nfc(text)))
            if any(row[key]!=expected[key] for key in ('candidates','models','calibration_id')):
                raise ValueError('Standalone results differ')
            if bool(row['candidates'])!=('PS' in fixture['labels']):raise ValueError('Authored regression changed')
            count+=1;findings+=bool(row['candidates'])
    after={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in names}
    if before!=after:raise ValueError('Sources changed during execution')
    return {'captured_at':datetime.now(timezone.utc).isoformat(),'pass':True,'checked_by':'Codex',
        'sources':before,'source_unchanged':True,'actual_child_processes':count,
        'fixture_files':len(manifest['active']),'finding_cases':findings,'no_finding_cases':count-findings,
        'exact_current_method_parity':True,'original_input_executed':False,
        'gateway_required':False,'redactor_required':False,'collection_enabled':False,
        'independent_accuracy_evidence':False,'physical_phone_tested':False,
        'scope':'Standalone process parity on all active authored PS development regressions; no accuracy release or human acceptance.'}


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output');args=parser.parse_args()
    try:
        row=verify()
        if args.output:write_report(args.output,row)
        print(json.dumps(row));raise SystemExit(0)
    except (OSError,ValueError,TypeError,KeyError):
        print('Standalone PS verification unavailable; no input or exception data displayed.',file=sys.stderr)
        raise SystemExit(1)
