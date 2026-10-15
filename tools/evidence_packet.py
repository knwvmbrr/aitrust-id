"""Inspect current source-bound engineering receipts; never promote release status."""
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import re

from protocol.evidence import unique, reject, finite
from protocol.revalidation import CAPABILITIES, assess, fingerprint
from scripts.source_snapshot import read_file
import json

ROOT = Path(__file__).resolve().parents[1]
BASE = ('state.json', 'docs/scope-progress.json', 'docs/master-scope.json', 'eval/revalidation.json',
        'tests/test_evidence_packet.py',
        'tools/evidence_packet.py', 'scripts/build-evidence-packet.py',
        'protocol/revalidation.py', 'protocol/evidence.py', 'scripts/source_snapshot.py')


def capture(root, name, limit=2_000_000):
    raw = read_file(root / name, limit)
    value = json.loads(raw.decode('utf-8', 'strict'), object_pairs_hook=unique, parse_constant=reject)
    finite(value)
    if type(value) is not dict:
        raise ValueError('Evidence object required')
    return raw, value


def build(root=ROOT):
    captured = {name: read_file(root / name, 2_000_000) for name in BASE}
    state = capture(root, 'state.json')[1]
    ledger = capture(root, 'docs/scope-progress.json')[1]
    selected = state['current_engineering_revalidation']
    if type(selected) is not dict:
        raise ValueError('Selected receipt map refused')
    checks = []
    snapshots = {}
    source_drift = False
    for capability in sorted(CAPABILITIES):
        name = selected.get(capability)
        if (type(name) is not str or not re.fullmatch(r'runs/[a-zA-Z0-9_-]+\.json', name)):
            raise ValueError('Only declared public execution receipts are accepted')
        row = {'capability': capability, 'receipt': name, 'pass': False}
        try:
            raw, receipt = capture(root, name)
            captured[name] = raw
            # Bind assessment, captured bytes and the final source check to
            # the same fingerprint. A later fingerprint cannot replace it.
            current = fingerprint(capability, root)
            snapshots[capability] = current
            assessment = assess(receipt, capability, root)
            if assessment['pass'] and receipt.get('fingerprint') != current:
                source_drift = True
                raise ValueError('Assessment snapshot changed')
            row.update(assessment)
            row['receipt_sha256'] = hashlib.sha256(raw).hexdigest()
            row['executed_at'] = receipt['captured_at'] if assessment['pass'] else None
            # Pin the actual selected source inputs too, including inputs which
            # differ from an older receipt. The index must expose stale evidence.
            for path, expected_digest in current['sources'].items():
                raw_source = read_file(root / path, 32_000_000)
                if hashlib.sha256(raw_source).hexdigest() != expected_digest:
                    source_drift = True
                    raise ValueError('Captured source differs from assessed snapshot')
                captured[path] = raw_source
        except (OSError, ValueError, TypeError, KeyError, RecursionError):
            row['pass'] = False
            row['revalidation_required'] = True
            row['executed_at'] = None
            row['failures'] = ['receipt_or_current_sources_unavailable']
        checks.append(row)
    records = ledger.get('records')
    expected = {r['id'] for r in capture(root, 'docs/master-scope.json')[1]['records']}
    if (type(records) is not list or len(records) != 202
            or len(expected) != 202 or {r['id'] for r in records} != expected
            or any(type(r['percent_complete']) is not int or r['percent_complete'] not in range(0, 101, 20)
                   or type(r['required_acceptance']) is not list
                   or any(type(v) is not str for v in r['required_acceptance']) for r in records)):
        raise ValueError('Full scope identity required')
    open_records = [{'id': r['id'], 'required_acceptance': r['required_acceptance']}
                    for r in records if r['percent_complete'] < 100]
    stable = (not source_drift
              and all(fingerprint(capability, root) == snapshot
                      for capability, snapshot in snapshots.items())
              and all(read_file(root / name, 32_000_000) == raw
                      for name, raw in captured.items()))
    return {'schema_version': 1, 'kind': 'source_bound_evidence_packet',
            'captured_at': datetime.now(timezone.utc).isoformat(),
            'packet_valid': stable, 'source_unchanged_during_inspection': stable,
            'engineering_checks_current': stable and all(r['pass'] for r in checks),
            'receipts': checks,
            'files': {name: hashlib.sha256(raw).hexdigest() for name, raw in sorted(captured.items())},
            'records_preserved': len(records), 'completed_records': len(records)-len(open_records),
            'open_records': open_records, 'independent_accuracy_evidence': False,
            'release_assessed': False, 'release_approved': False, 'certification': False,
            'limits': 'Index and current-source assessment only; no commands executed, no signature authentication or independent acceptance granted.'}
