"""Version-two gate consumer. Regression execution is not release certification."""
import argparse
import hashlib
import importlib.util
import json
import math
import re
import sys
from pathlib import Path
from statistics import NormalDist

import yaml
from jsonschema import validate
from jsonschema.exceptions import ValidationError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from protocol.normalization import normalize_nfc, NORMALIZATION_ID
from protocol.categories import category_for_text, CATEGORY_VERSION

class UniqueLoader(yaml.SafeLoader):
    pass

def mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in result:
            raise ValueError(f"duplicate YAML key: {key}")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result

UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping)

def load_config(path):
    config = yaml.load(Path(path).read_text(), Loader=UniqueLoader)
    validate(config, json.loads((ROOT / 'eval/gates.schema.json').read_text()))
    for code in config['production_allowlist']:
        if code != 'PII_REDACTED' and code not in config['tags']:
            raise ValueError(f'allowlisted tag has no gate: {code}')
    return config

def wilson(successes, total, confidence=0.95):
    if type(successes) is not int or type(total) is not int or not 0 <= successes <= total:
        raise ValueError('invalid binomial counts')
    if total == 0:
        return None
    z = NormalDist().inv_cdf((1 + confidence) / 2)
    p = successes / total
    denominator = 1 + z*z/total
    center = (p + z*z/(2*total)) / denominator
    radius = z*math.sqrt(p*(1-p)/total + z*z/(4*total*total))/denominator
    return [max(0.0, center-radius), min(1.0, center+radius)]

def ece(pairs, bins=10):
    if not pairs:
        raise ValueError('ECE requires observations')
    if bins < 1:
        raise ValueError('bins must be positive')
    groups = [[] for _ in range(bins)]
    for confidence, correct in pairs:
        if not math.isfinite(confidence) or not 0 <= confidence <= 1 or correct not in (0, 1):
            raise ValueError('invalid calibration observation')
        groups[min(int(confidence*bins), bins-1)].append((confidence, correct))
    return sum(len(g)/len(pairs)*abs(sum(y for _,y in g)/len(g)-sum(c for c,_ in g)/len(g)) for g in groups if g)

def category_metrics(counts,confidence=.95):
    if set(counts)!={'tp','fp','fn','tn'} or any(type(v)is not int or v<0 for v in counts.values()):raise ValueError('Invalid category counts')
    results={**counts,'n':sum(counts.values())}
    for name,success,total in [('precision',counts['tp'],counts['tp']+counts['fp']),('recall',counts['tp'],counts['tp']+counts['fn']),('false_positive_rate',counts['fp'],counts['fp']+counts['tn']),('false_negative_rate',counts['fn'],counts['tp']+counts['fn'])]:
        results[name]={'successes':success,'denominator':total,'point':success/total if total else None,'interval':wilson(success,total,confidence)}
    results['calibration']={'ece':None,'observations':0,'reason':'Calibration evidence is separate; heuristic scores are not probabilities'}
    return results

def evaluate_fixtures(path):
    spec = importlib.util.spec_from_file_location('fixture_evaluator', ROOT/'services/evaluator/app.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    counts = dict(tp=0, fp=0, fn=0, tn=0)
    failures = [];categories={}
    if Path(path).stat().st_size>16_000_000:raise ValueError('Oversized fixture file')
    raw = Path(path).read_bytes()
    for index, line in enumerate(raw.decode().splitlines(), 1):
        row = json.loads(line)
        if not isinstance(row,dict) or not isinstance(row.get('text'),str) or len(row['text'])>200_000 or not isinstance(row.get('labels'),list) or any(x!='PS' for x in row['labels']) or len(set(row['labels']))!=len(row['labels']):raise ValueError('Invalid fixture at line '+str(index))
        category=row.get('category',category_for_text(row['text']))
        if not isinstance(category,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',category):raise ValueError('Invalid fixture category at line '+str(index))
        actual = 'PS' in row['labels']
        predicted = any(c['code']=='PS' for c in module.signals(module.Doc(text=normalize_nfc(row['text'])))['candidates'])
        key='tp' if actual and predicted else 'fn' if actual else 'fp' if predicted else 'tn'
        counts[key] += 1
        categories.setdefault(category,dict(tp=0,fp=0,fn=0,tn=0))[key]+=1
        if actual != predicted:
            failures.append({'line':index, 'category':category, 'error':'fn' if actual else 'fp'})
    if not sum(counts.values()):
        raise ValueError('empty fixture set')
    return {'PS':{**counts,'category_failures':failures,'category_metrics':{key:category_metrics(value) for key,value in sorted(categories.items())}},'dataset':{'sha256':hashlib.sha256(raw).hexdigest(),'kind':'regression','independently_labeled':False,'method_fixed_before_run':False,'normalization_id':NORMALIZATION_ID,'category_version':CATEGORY_VERSION}}

def assess(config, report):
    failures = []
    output = {}
    dataset = report.get('dataset', {})
    if dataset.get('kind') != 'frozen_holdout' or not dataset.get('independently_labeled') or not dataset.get('method_fixed_before_run') or not dataset.get('sha256'):
        failures.append('release evidence requires a frozen independent holdout, manifest hash, and pre-agreed method')
    for code in config['production_allowlist']:
        if code == 'PII_REDACTED':
            continue  # redaction ordering/coverage is verified by separate integration checks
        gate = config['tags'][code]
        result = report.get(code)
        if not result:
            failures.append(f'{code}: missing results')
            continue
        counts = {k:result[k] for k in ('tp','fp','fn','tn')}
        if any(type(v) is not int or v < 0 for v in counts.values()):
            raise ValueError('counts must be nonnegative integers')
        intervals = {'precision':wilson(counts['tp'], counts['tp']+counts['fp'], config['method']['confidence']), 'recall':wilson(counts['tp'], counts['tp']+counts['fn'], config['method']['confidence'])}
        output[code] = {**counts,'intervals':intervals,'category_failures':result.get('category_failures',[])}
        for metric, interval in intervals.items():
            threshold = gate[f'{metric}_min_lower_bound']
            if interval is None or interval[0] < threshold:
                failures.append(f'{code}.{metric}: lower bound does not clear {threshold}')
        if 'ece_max' in gate:
            if not result.get('calibration_pairs'):
                failures.append(f'{code}: calibration evidence missing; heuristic scores are not probabilities')
            elif ece(result['calibration_pairs']) > gate['ece_max']:
                failures.append(f'{code}: ECE gate failed')
    return {'metrics':output,'failures':failures,'evaluation_gate_pass':not failures,
            'gate_scope':'statistical_evaluation_only','release_assessed':False}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--gates', default=str(ROOT/'eval/gates.yaml'))
    parser.add_argument('--results', default=str(ROOT/'eval/results.json'))
    parser.add_argument('--fixtures')
    parser.add_argument('--output')
    args = parser.parse_args()
    try:
        config = load_config(args.gates)
        report = evaluate_fixtures(args.fixtures) if args.fixtures else json.loads(Path(args.results).read_text())
        result = assess(config, report)
        result['source'] = report
        if args.output:
            Path(args.output).write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result,indent=2))
        return 0 if result['evaluation_gate_pass'] else 1
    except (ValueError, KeyError, OSError, yaml.YAMLError, ValidationError) as error:
        print(f'GATE ERROR: {error}',file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(main())
