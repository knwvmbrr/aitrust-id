"""Freeze a new blind review packet. No predictions, execution or uploads."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
LABELS = {'positive', 'negative', 'ambiguous'}
FIELDS = ['id', 'text', 'category', 'source', 'label', 'reason']


def sha(data):
    return hashlib.sha256(data).hexdigest()


def freeze(source, destination):
    raw = Path(source).read_bytes()
    if len(raw) > 10_000_000:
        raise ValueError('Review input exceeds 10 MB')
    rows = []
    for line in raw.decode('utf-8').splitlines():
        row = json.loads(line)
        if set(row) != {'id', 'text', 'category', 'source'}:
            raise ValueError('Each item needs only id, text, category and source; no labels or predictions')
        if any(not isinstance(value, str) or not value.strip() for value in row.values()):
            raise ValueError('All item fields must be nonempty strings')
        if len(row['text']) > 200_000 or len(row['id']) > 100:
            raise ValueError('Item exceeds checker or identifier limit')
        rows.append(row)
    if not 1 <= len(rows) <= 1000 or len({row['id'] for row in rows}) != len(rows):
        raise ValueError('Require 1–1000 uniquely identified items')
    destination = Path(destination).expanduser().absolute()
    if destination.resolve().is_relative_to(ROOT):
        raise ValueError('Keep blind review material outside the public repository')
    # Never overwrite an existing packet or follow a destination symlink.
    destination.mkdir(mode=0o700, parents=False, exist_ok=False)
    items = ''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in rows).encode()
    files = {'items.jsonl': items}
    for reviewer in (1, 2):
        order = list(rows)
        random.SystemRandom().shuffle(order)
        # CSV formula injection must not execute when opened in a spreadsheet.
        # A leading apostrophe is part of the blind export, not the frozen text.
        from io import StringIO
        output = StringIO(newline='')
        writer = csv.DictWriter(output, fieldnames=FIELDS)
        writer.writeheader()
        for row in order:
            writer.writerow({**{k: "'" + v if v[:1] in '=+-@\t\r' else v
                               for k, v in row.items()}, 'label': '', 'reason': ''})
        files[f'reviewer-{reviewer}.csv'] = output.getvalue().encode()
    manifest = {'format': 'ai-trust-id-blind-ps-review/v1', 'item_count': len(rows),
        'input_sha256': sha(raw), 'dataset_sha256': sha(items),
        'method_sha256': sha((ROOT/'services/evaluator/app.py').read_bytes()),
        'gates_sha256': sha((ROOT/'eval/gates.yaml').read_bytes()),
        'protocol_sha256': sha((ROOT/'docs/independent-review.md').read_bytes()),
        'independence_verified': False, 'sampling_accepted': False,
        'predictions_run': False, 'release_assessed': False,
        'note': 'Hashes freeze bytes; they do not prove reviewer independence or representative sampling.'}
    files['manifest.json'] = (json.dumps(manifest, indent=2) + '\n').encode()
    for name, data in files.items():
        with os.fdopen(os.open(destination/name, os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0o600), 'wb') as handle:
            handle.write(data)
    return manifest


def compare(packet):
    packet = Path(packet)
    manifest = json.loads((packet/'manifest.json').read_text())
    items = (packet/'items.jsonl').read_bytes()
    if sha(items) != manifest['dataset_sha256']:
        raise ValueError('Frozen dataset changed')
    if sha((ROOT/'services/evaluator/app.py').read_bytes()) != manifest['method_sha256']:
        raise ValueError('Detector changed after freeze; start a new review')
    if sha((ROOT/'eval/gates.yaml').read_bytes()) != manifest['gates_sha256'] or sha((ROOT/'docs/independent-review.md').read_bytes()) != manifest['protocol_sha256']:
        raise ValueError('Review policy changed after freeze')
    rows = {row['id']: row for row in map(json.loads, items.decode().splitlines())}
    reviews = []
    for reviewer in (1, 2):
        labels = {}
        with (packet/f'reviewer-{reviewer}.csv').open(newline='') as handle:
            for row in csv.DictReader(handle):
                # Undo only the exact spreadsheet escape used in this packet.
                matched = None
                for item in rows.values():
                    escaped = {k: "'"+v if v[:1] in '=+-@\t\r' else v for k,v in item.items()}
                    if all(row.get(k) == v for k,v in escaped.items()):
                        matched = item['id']
                        break
                if matched is None or matched in labels:
                    raise ValueError('Review has changed, duplicate or unknown items')
                if row.get('label') not in LABELS or not row.get('reason', '').strip():
                    raise ValueError('Every item needs positive/negative/ambiguous and a reason')
                labels[matched] = row['label']
        if set(labels) != set(rows):
            raise ValueError('Review omits items')
        reviews.append(labels)
    disagreements = [key for key in rows if reviews[0][key] != reviews[1][key]]
    ambiguous = [key for key in rows if any(r[key] == 'ambiguous' for r in reviews)]
    return {'item_count':len(rows), 'disagreement_ids':disagreements,
            'ambiguous_ids':ambiguous, 'agreement_count':len(rows)-len(disagreements),
            'independence_verified':False, 'predictions_run':False,
            'release_assessed':False, 'next':'Record independent reviewer attestations, sampling acceptance and adjudication before evaluation.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    create = commands.add_parser('freeze')
    create.add_argument('source', type=Path)
    create.add_argument('destination', type=Path)
    review = commands.add_parser('compare')
    review.add_argument('packet', type=Path)
    args = parser.parse_args()
    try:
        result = freeze(args.source, args.destination) if args.command == 'freeze' else compare(args.packet)
    except (OSError, ValueError, KeyError, TypeError):
        print('Review operation failed. Check input format, unique packet path, frozen hashes and completed labels. No validation accepted.', file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
