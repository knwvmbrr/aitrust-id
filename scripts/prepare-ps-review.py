"""Freeze a new blind review packet. No predictions, execution or uploads."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import random
import re
from io import StringIO
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.blind_review_io import PacketError, directory, member, source as private_source, create as private_create
from protocol.evidence import unique, reject, finite
from tools.review_execution import execution_context, canonical as execution_bytes, digest as execution_digest
INPUT_LIMIT = 10_000_000
MEMBER_LIMIT = 16_000_000
PACKET_LIMIT = 32_000_000
PHONE_LIMIT = 10_000_000
MANIFEST_LIMIT = 64_000
NOTE = 'Hashes freeze bytes; they do not prove reviewer independence or representative sampling.'
LABELS = {'positive', 'negative', 'ambiguous'}
FIELDS = ['id', 'text', 'category', 'source', 'label', 'reason']


def sha(data):
    return hashlib.sha256(data).hexdigest()


def decoded(raw):
    try:
        text=raw.decode('utf-8', errors='strict')
        if '\x00' in text:raise ValueError('Review text contains a forbidden control')
        return text
    except UnicodeError:
        raise ValueError('Review text must be valid UTF-8') from None


def strict_json(raw):
    try:
        value=json.loads(decoded(raw),object_pairs_hook=unique,parse_constant=reject)
        finite(value)
        return value
    except (RecursionError,UnicodeError):
        raise ValueError('Review JSON exceeds safe text or nesting limits') from None


def item(row):
    if not isinstance(row,dict) or set(row)!={'id','text','category','source'}:
        raise ValueError('Each item needs only id, text, category and source; no labels or predictions')
    limits={'id':100,'text':200_000,'category':1000,'source':1000}
    if any(not isinstance(v,str) or not v.strip() or len(v)>limits[k] or '\x00' in v for k,v in row.items()):
        raise ValueError('Item fields must be nonempty text within their limits')
    finite(row)
    return row


def parse_items(raw):
    rows=[item(strict_json(line.encode('utf-8'))) for line in decoded(raw).splitlines()]
    if not 1<=len(rows)<=1000 or len({r['id'] for r in rows})!=len(rows):
        raise ValueError('Require 1–1000 uniquely identified items')
    return rows


def spreadsheet(value):
    if value[:1] in '=+-@\t\r\n' or value.lstrip(' \t\r\n')[:1] in '=+-@':
        return "'"+value
    return value


def validate_manifest(value):
    hashes={'input_sha256','dataset_sha256','method_sha256','gates_sha256','protocol_sha256'}
    flags={'independence_verified','sampling_accepted','predictions_run','release_assessed'}
    version=value.get('format') if isinstance(value,dict) else None
    if version=='ai-trust-id-blind-ps-review/v2':hashes.add('execution_context_sha256')
    if (not isinstance(value,dict) or set(value)!={'format','item_count','note',*hashes,*flags}
            or version not in ('ai-trust-id-blind-ps-review/v1','ai-trust-id-blind-ps-review/v2') or value['note']!=NOTE
            or type(value['item_count']) is not int or not 1<=value['item_count']<=1000
            or any(value[k] is not False for k in flags)
            or any(not isinstance(value[k],str) or not re.fullmatch('[a-f0-9]{64}',value[k]) for k in hashes)):
        raise ValueError('Frozen review manifest is invalid; no independent validation accepted')
    return value


def freeze(source, destination):
    execution=execution_context(ROOT)
    raw = private_source(source, ROOT, INPUT_LIMIT)
    rows = parse_items(raw)
    if len({spreadsheet(r['id']) for r in rows})!=len(rows):
        raise ValueError('Spreadsheet identifiers collide; choose distinct opaque item IDs')
    items = ''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in rows).encode()
    files = {'items.jsonl': items}
    for reviewer in (1, 2):
        order = list(rows)
        random.SystemRandom().shuffle(order)
        # CSV formula injection must not execute when opened in a spreadsheet.
        # A leading apostrophe is part of the blind export, not the frozen text.
        output = StringIO(newline='')
        writer = csv.DictWriter(output, fieldnames=FIELDS)
        writer.writeheader()
        for row in order:
            writer.writerow({**{k: spreadsheet(v)
                               for k, v in row.items()}, 'label': '', 'reason': ''})
        files[f'reviewer-{reviewer}.csv'] = output.getvalue().encode()
    manifest = {'format': 'ai-trust-id-blind-ps-review/v2', 'item_count': len(rows),
        'input_sha256': sha(raw), 'dataset_sha256': sha(items),
        'method_sha256': sha((ROOT/'services/evaluator/app.py').read_bytes()),
        'gates_sha256': sha((ROOT/'eval/gates.yaml').read_bytes()),
        'protocol_sha256': sha((ROOT/'docs/independent-review.md').read_bytes()),
        'execution_context_sha256': execution_digest(execution),
        'independence_verified': False, 'sampling_accepted': False,
        'predictions_run': False, 'release_assessed': False,
        'note': NOTE}
    files['manifest.json'] = (json.dumps(manifest, indent=2) + '\n').encode()
    files['execution-context.json'] = execution_bytes(execution)
    for reviewer in (1, 2):
        order = list(rows)
        random.SystemRandom().shuffle(order)
        form = {'format': 'ai-trust-id-blind-ps-labels/v1', 'reviewer_slot': reviewer,
                **{key: manifest[key] for key in ('dataset_sha256', 'method_sha256', 'gates_sha256', 'protocol_sha256')},
                'items': [{**row, 'label': None, 'reason': ''} for row in order]}
        files[f'reviewer-{reviewer}.json'] = (json.dumps(form, ensure_ascii=False, indent=2)+'\n').encode()
    if (any(len(raw)>(PHONE_LIMIT if name.startswith('reviewer-') and name.endswith('.json') else MANIFEST_LIMIT if name=='manifest.json' else MEMBER_LIMIT) for name,raw in files.items()) or sum(map(len,files.values()))>PACKET_LIMIT):
        raise ValueError('Prepared packet exceeds the safe output byte limit')
    if execution_context(ROOT)!=execution:
        raise ValueError('Execution recipe changed during freeze; no packet created')
    private_create(destination, ROOT, files)
    return manifest


def compare(packet, format='csv', require_execution_binding=False):
    if format not in ('csv','json'):raise ValueError('Unsupported review format')
    if type(require_execution_binding) is not bool:raise ValueError('Invalid execution binding requirement')
    with directory(packet, ROOT) as packet_fd:
        raw_manifest=member(packet_fd,'manifest.json',MANIFEST_LIMIT)
        manifest = validate_manifest(strict_json(raw_manifest))
        execution_bound=manifest['format']=='ai-trust-id-blind-ps-review/v2'
        if require_execution_binding and not execution_bound:
            raise ValueError('Legacy packet has no execution binding; label comparison only')
        if execution_bound:
            raw_execution=member(packet_fd,'execution-context.json',MANIFEST_LIMIT)
            execution=strict_json(raw_execution)
            if execution_digest(execution)!=manifest['execution_context_sha256']:
                raise ValueError('Frozen execution context changed')
            if execution!=execution_context(ROOT):
                raise ValueError('Execution dependency changed after freeze; start a new review')
        items=member(packet_fd,'items.jsonl',MEMBER_LIMIT)
        forms={i:member(packet_fd,f'reviewer-{i}.'+format,PHONE_LIMIT if format=='json' else MEMBER_LIMIT) for i in (1,2)}
    if sha(items) != manifest['dataset_sha256']:
        raise ValueError('Frozen dataset changed')
    if sha((ROOT/'services/evaluator/app.py').read_bytes()) != manifest['method_sha256']:
        raise ValueError('Detector changed after freeze; start a new review')
    if sha((ROOT/'eval/gates.yaml').read_bytes()) != manifest['gates_sha256'] or sha((ROOT/'docs/independent-review.md').read_bytes()) != manifest['protocol_sha256']:
        raise ValueError('Review policy changed after freeze')
    rows = {row['id']: row for row in parse_items(items)}
    if len(rows)!=manifest['item_count']:raise ValueError('Frozen item count changed')
    reviews = []
    for reviewer in (1, 2):
        labels = {}
        if format == 'json':
            form = strict_json(forms[reviewer])
            keys = {'format','reviewer_slot','dataset_sha256','method_sha256','gates_sha256','protocol_sha256','items'}
            if not isinstance(form,dict) or set(form) != keys or type(form['reviewer_slot']) is not int or form['format'] != 'ai-trust-id-blind-ps-labels/v1' or form['reviewer_slot'] != reviewer:
                raise ValueError('Review identity changed')
            for key in ('dataset_sha256','method_sha256','gates_sha256','protocol_sha256'):
                if form[key] != manifest[key]:
                    raise ValueError('Review frozen hashes changed')
            if not isinstance(form['items'], list) or len(form['items']) != len(rows):
                raise ValueError('Review omits items')
            for row in form['items']:
                if not isinstance(row, dict) or set(row) != set(FIELDS):
                    raise ValueError('Review has unexpected fields')
                item({k:row[k] for k in ('id','text','category','source')})
                matched = row['id']
                if matched not in rows or matched in labels or any(row[k] != rows[matched][k] for k in ('id','text','category','source')):
                    raise ValueError('Review has changed, duplicate or unknown items')
                if not isinstance(row['label'],str) or row['label'] not in LABELS or not isinstance(row['reason'],str) or not row['reason'].strip() or len(row['reason']) > 2000 or '\x00' in row['reason']:
                    raise ValueError('Every item needs positive/negative/ambiguous and a reason')
                labels[matched] = row['label']
        else:
            previous_limit=csv.field_size_limit(200_001)
            try:
                reader=csv.DictReader(StringIO(decoded(forms[reviewer]),newline=''))
                if reader.fieldnames!=FIELDS:raise ValueError('CSV headers must match the frozen review format')
                escaped={spreadsheet(r['id']):r for r in rows.values()}
                if len(escaped)!=len(rows):raise ValueError('Spreadsheet identifiers collide; use phone JSON forms')
                for row in reader:
                    if set(row)!=set(FIELDS):raise ValueError('CSV contains missing or extra fields')
                    finite(row)
                    original=escaped.get(row['id'])
                    matched=original['id'] if original is not None else None
                    if (matched is None or matched in labels
                            or any(row.get(k)!=spreadsheet(v) for k,v in original.items())):
                        raise ValueError('Review has changed, duplicate or unknown items')
                    if (row.get('label') not in LABELS or not isinstance(row.get('reason'),str)
                            or not row['reason'].strip() or len(row['reason'])>2000 or '\x00' in row['reason']):
                        raise ValueError('Every item needs positive/negative/ambiguous and a reason')
                    labels[matched]=row['label']
                    if len(labels)>len(rows):raise ValueError('Review contains too many items')
            except csv.Error:
                raise ValueError('Review CSV exceeds its field or syntax limits') from None
            finally:
                csv.field_size_limit(previous_limit)
        if set(labels) != set(rows):
            raise ValueError('Review omits items')
        reviews.append(labels)
    disagreements = [key for key in rows if reviews[0][key] != reviews[1][key]]
    ambiguous = [key for key in rows if any(r[key] == 'ambiguous' for r in reviews)]
    if execution_bound and execution_context(ROOT)!=execution:
        raise ValueError('Execution dependency changed during comparison')
    return {'item_count':len(rows), 'disagreement_ids':disagreements,
            'ambiguous_ids':ambiguous, 'agreement_count':len(rows)-len(disagreements),
            'independence_verified':False, 'predictions_run':False,
            'execution_binding_verified':execution_bound,
            'execution_scope':'selected_offline_python_recipe' if execution_bound else 'legacy_evaluator_file_only',
            'release_assessed':False, 'next':'Record independent reviewer attestations, sampling acceptance and adjudication before evaluation.'}


class PrivateReviewParser(argparse.ArgumentParser):
    def error(self, _message):
        self.exit(2, 'Review command failed. Use freeze or compare as documented. No validation accepted.\n')

def main():
    parser = PrivateReviewParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    create = commands.add_parser('freeze')
    create.add_argument('source', type=Path)
    create.add_argument('destination', type=Path)
    review = commands.add_parser('compare')
    review.add_argument('packet', type=Path)
    review.add_argument('--format', choices=['csv','json'], default='csv')
    review.add_argument('--require-execution-binding',action='store_true',
                        help='Refuse legacy packets that only pinned the evaluator file')
    args = parser.parse_args()
    try:
        result = freeze(args.source, args.destination) if args.command == 'freeze' else compare(args.packet, args.format,args.require_execution_binding)
    except (OSError, ValueError, KeyError, TypeError, UnicodeError, RecursionError, RuntimeError):
        print('Review operation failed. Check input format, unique packet path, frozen hashes and completed labels. No validation accepted.', file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
