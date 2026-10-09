"""Publish method-bound development measurements, never independent validation."""
import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'eval'))
import harness


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def minimum_denominator(floor, errors=0, confidence=.95):
    if not 0 < floor < 1 or type(errors) is not int or errors < 0:
        raise ValueError('Invalid sizing request')
    for n in range(max(1, errors + 1), 100001):
        if harness.wilson(n-errors, n, confidence)[0] >= floor:
            return n
    raise ValueError('Sizing exceeds cap')


def build(regressions, device):
    report = json.loads(regressions.read_text())
    method = digest(ROOT / 'services/evaluator/app.py')
    if report['method_sha256'] != method or report['independent_accuracy_evidence'] is not False:
        raise ValueError('Stale or misclassified regression evidence')
    counts = dict.fromkeys(('tp','fp','fn','tn'), 0)
    fixtures = []
    for row in report['datasets']:
        name = row['file']
        if Path(name).name != name:
            raise ValueError('Invalid fixture name')
        path = ROOT / 'eval/datasets/unsafe_code' / name
        if digest(path) != row['sha256']:
            raise ValueError('Fixture changed since measured run')
        for key in counts:
            if type(row[key]) is not int or row[key] < 0:
                raise ValueError('Invalid counts')
            counts[key] += row[key]
        fixtures.append({'path':str(path.relative_to(ROOT)), 'sha256':row['sha256']})
    if sum(counts.values()) != report['case_count']:
        raise ValueError('Count mismatch')
    gate = harness.load_config(ROOT / 'eval/gates.yaml')
    confidence = gate['method']['confidence']
    metrics=[]
    for key, title, description, denominator in (
        ('precision','Correct alerts','How many flagged examples were correctly flagged.',counts['tp']+counts['fp']),
        ('recall','Patterns caught','How many labeled risk examples were found.',counts['tp']+counts['fn'])):
        interval=harness.wilson(counts['tp'],denominator,confidence)
        metrics.append({'id':key,'label':title,'description':description,
                        'successes':counts['tp'],'denominator':denominator,
                        'point':counts['tp']/denominator if denominator else None,
                        'interval':interval,'candidate_lower_bound':gate['tags']['PS'][key+'_min_lower_bound']})
    mobile=json.loads(device.read_text())
    mobile_method=mobile.get('method_sha256')
    # Legacy engine reports predate explicit method attribution; do not reuse them as current measurements.
    engines=mobile['engines'] if mobile.get('pass') and mobile_method==method else []
    return {'format':'ai-trust-id-performance-evidence/v1',
        'captured_at':datetime.now(timezone.utc).isoformat(),
        'kind':'development_regression','independently_labeled':False,'release_validated':False,
        'method_sha256':method,'gates_sha256':digest(ROOT/'eval/gates.yaml'),
        'fixtures':fixtures,'case_count':report['case_count'],'counts':counts,'metrics':metrics,
        'confidence':confidence,'interval_method':'wilson',
        'evidence':[str(regressions.relative_to(ROOT)),str(device.relative_to(ROOT))],
        'evidence_sha256':{str(p.relative_to(ROOT)):digest(p) for p in (regressions,device)},
        'mobile':{'emulated':True,'physical_device_tested':False,'engines':engines,
                  'attribution_verified':bool(engines)},
        'sizing':{'scope':'Mathematical denominator minima only; representative independently labeled sampling still required.',
                  'precision_zero_errors':minimum_denominator(gate['tags']['PS']['precision_min_lower_bound'],confidence=confidence),
                  'precision_one_error':minimum_denominator(gate['tags']['PS']['precision_min_lower_bound'],1,confidence),
                  'recall_zero_errors':minimum_denominator(gate['tags']['PS']['recall_min_lower_bound'],confidence=confidence)}}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--regressions',type=Path,default=ROOT/'runs/2026-10-09-performance-regressions.json')
    parser.add_argument('--device',type=Path,default=ROOT/'runs/2026-10-09-performance-device-local.json')
    parser.add_argument('--output',type=Path,default=ROOT/'eval/tag-performance-evidence.json')
    args=parser.parse_args()
    result=build(args.regressions.resolve(), args.device.resolve())
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'case_count':result['case_count'],'sizing':result['sizing'],'mobile_attribution_verified':result['mobile']['attribution_verified']},indent=2))


if __name__=='__main__':
    main()
