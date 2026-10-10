"""Publish method-bound development measurements, never independent validation."""
import argparse
import hashlib
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'eval'))
import harness
from protocol.measurements import validate_timing


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
    for key,name in [('normalization_sha256','normalization.py'),('normalization_data_sha256','unicode15-data.json'),('category_source_sha256','categories.py')]:
        if report.get(key)!=digest(ROOT/'protocol'/name):raise ValueError('Stale normalization identity')
    active=json.loads((ROOT/'eval/datasets/unsafe_code/manifest.json').read_text())['active']
    spec=importlib.util.spec_from_file_location('measurement_provenance',ROOT/'scripts/verify-dataset-provenance.py')
    provenance_module=importlib.util.module_from_spec(spec);spec.loader.exec_module(provenance_module)
    current_provenance=provenance_module.verify()
    for key in ('pass','examples','active_examples','historical_examples','manifest_sha256','provenance_sha256','independent_accuracy_evidence'):
        if report.get('provenance',{}).get(key)!=current_provenance[key]:raise ValueError('Stale or invalid example provenance')
    if report.get('category_version')!=harness.CATEGORY_VERSION:raise ValueError('Stale category version')
    names=[r['file'] for r in report['datasets']]
    if len(names)!=len(set(names)) or set(names)!={r['file'] for r in active}:raise ValueError('Missing or duplicate active measurements')
    counts = dict.fromkeys(('tp','fp','fn','tn'), 0)
    fixtures = [];categories=[]
    for row in report['datasets']:
        name = row['file']
        if Path(name).name != name:
            raise ValueError('Invalid fixture name')
        path = ROOT / 'eval/datasets/unsafe_code' / name
        if digest(path) != row['sha256']:
            raise ValueError('Fixture changed since measured run')
        recomputed=harness.evaluate_fixtures(path)['PS']
        for key in ('tp','fp','fn','tn','category_failures','category_metrics'):
            if row.get(key)!=recomputed[key]:raise ValueError('Published count/category differs from source recomputation')
        categories.extend({'source_dataset':name,'category':category,**metrics} for category,metrics in recomputed['category_metrics'].items())
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
    reference=json.loads((ROOT/'docs/device-build-reference.json').read_text())
    engines=mobile['engines'] if mobile.get('pass') and mobile_method==method and mobile.get('bundle_sha256')==reference['bundle_sha256'] and mobile.get('normalization_data_sha256')==reference['normalization_data_sha256'] and all(isinstance(e.get('timing',{}).get('samples'),list) for e in mobile.get('engines',[])) else []
    for engine in engines:validate_timing(engine['timing'],engine['case_count'])
    return {'format':'ai-trust-id-performance-evidence/v1',
        'captured_at':datetime.now(timezone.utc).isoformat(),
        'kind':'development_regression','independently_labeled':False,'release_validated':False,
        'method_sha256':method,'gates_sha256':digest(ROOT/'eval/gates.yaml'),'measurement_source_sha256':digest(ROOT/'eval/harness.py'),'timing_source_sha256':digest(ROOT/'protocol/measurements.py'),
        'category_version':report['category_version'],'category_source_sha256':report['category_source_sha256'],
        'category_metrics':categories,'provenance':report['provenance'],
        'normalization_sha256':report['normalization_sha256'],'normalization_data_sha256':report['normalization_data_sha256'],
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
    parser.add_argument('--regressions',type=Path,default=ROOT/'eval/regression-report.json')
    parser.add_argument('--device',type=Path,default=ROOT/'output/verification/handheld-checks.json')
    parser.add_argument('--output',type=Path,default=ROOT/'eval/tag-performance-evidence.json')
    args=parser.parse_args()
    result=build(args.regressions.resolve(), args.device.resolve())
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'case_count':result['case_count'],'sizing':result['sizing'],'mobile_attribution_verified':result['mobile']['attribution_verified']},indent=2))


if __name__=='__main__':
    main()
