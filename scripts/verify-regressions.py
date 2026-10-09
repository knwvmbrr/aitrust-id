"""Run every active development dataset; never claim statistical release approval."""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'eval'))
import harness

DEFAULT_MANIFEST = ROOT / 'eval/datasets/unsafe_code/manifest.json'


def load_manifest(path=DEFAULT_MANIFEST):
    path = Path(path)
    data = json.loads(path.read_text())
    if data.get('version') != 1 or data.get('kind') != 'development_regression':
        raise ValueError('Unsupported regression manifest')
    if data.get('independent_accuracy_evidence') is not False:
        raise ValueError('Development fixtures cannot declare independent accuracy')
    active, historical = data['active'], data['historical']
    if not active:
        raise ValueError('No active regression datasets')
    names = []
    for entry in active + historical:
        name = entry['file']
        if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_-]+\.jsonl', name):
            raise ValueError('Dataset must be a JSONL basename')
        names.append(name)
        if hashlib.sha256((path.parent / name).read_bytes()).hexdigest() != entry['sha256']:
            raise ValueError(f'Dataset hash mismatch: {name}')
    if len(set(names)) != len(names):
        raise ValueError('Duplicate dataset classification')
    if set(names) != {p.name for p in path.parent.glob('*.jsonl')}:
        raise ValueError('Every JSONL must be explicitly active or historical')
    active_names = {entry['file'] for entry in active}
    for entry in historical:
        if not entry.get('reason') or entry.get('superseded_by') not in active_names:
            raise ValueError('Historical exclusion needs a reason and active successor')
    return data


def verify(path=DEFAULT_MANIFEST):
    path = Path(path)
    manifest = load_manifest(path)
    datasets, failures = [], []
    for entry in manifest['active']:
        result = harness.evaluate_fixtures(path.parent / entry['file'])['PS']
        datasets.append({'file': entry['file'], 'sha256': entry['sha256'], **result})
        if result['fp'] or result['fn']:
            failures.append({'file': entry['file'], 'fp': result['fp'], 'fn': result['fn']})
    return {'regression_pass': not failures, 'datasets': datasets,
            'case_count': sum(sum(row[key] for key in ('tp', 'fp', 'fn', 'tn')) for row in datasets),
            'failures': failures, 'historical': manifest['historical'],
            'independent_accuracy_evidence': False, 'release_assessed': False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        report = verify(args.manifest)
    except (ValueError, KeyError, OSError, TypeError) as error:
        report = {'regression_pass': False, 'error': str(error), 'release_assessed': False}
    if args.output:
        args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return 0 if report['regression_pass'] else 1


if __name__ == '__main__':
    sys.exit(main())
