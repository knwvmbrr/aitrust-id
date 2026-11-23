"""Inspect current source-bound engineering receipts; never promote release status."""
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import re
import stat
from time import monotonic

from protocol.evidence import unique, reject, finite
from protocol.revalidation import CAPABILITIES, assess, fingerprint
from scripts.source_snapshot import read_file
import json

ROOT = Path(__file__).resolve().parents[1]
EMPTY_SHA256 = hashlib.sha256(b'').hexdigest()
MAX_INPUTS = 16_384
MAX_CAPTURED_BYTES = 128 * 1024 * 1024
OPERATION_SECONDS = 60
BASE = ('state.json', 'docs/scope-progress.json', 'docs/master-scope.json', 'eval/revalidation.json',
        'tests/test_evidence_packet.py',
        'tools/evidence_packet.py', 'scripts/build-evidence-packet.py',
        'protocol/revalidation.py', 'protocol/evidence.py', 'scripts/source_snapshot.py')


class InspectionBoundError(ValueError):
    """An exhausted operation budget cannot become an ordinary stale row."""


def capture(root, name, limit=2_000_000, reader=None):
    raw = (read_file if reader is None else reader)(root / name, limit)
    value = json.loads(raw.decode('utf-8', 'strict'), object_pairs_hook=unique, parse_constant=reject)
    finite(value)
    if type(value) is not dict:
        raise ValueError('Evidence object required')
    return raw, value


def empty_source(path):
    """Observe an explicitly empty source; JSON evidence still must be nonempty."""
    path = Path(path).absolute()
    if '..' in path.parts or not 2 <= len(path.parts) <= 64:
        raise ValueError('Empty source path refused')
    if not all(hasattr(os, key) for key in ('O_DIRECTORY', 'O_NOFOLLOW', 'O_NONBLOCK')):
        raise ValueError('Safe empty source capture unavailable')
    owned = []
    close_failed = False
    try:
        owned.append(os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW))
        for part in path.parts[1:-1]:
            owned.append(os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                                 dir_fd=owned[-1]))
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                     dir_fd=owned[-1])
        owned.append(fd)
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size != 0:
            raise ValueError('Declared empty source refused')
        raw = os.read(fd, 1)
        after = os.fstat(fd)
        fields = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns', 'st_nlink')
        if raw or any(getattr(before, key) != getattr(after, key) for key in fields):
            raise ValueError('Declared empty source changed')
        return b''
    except OSError:
        raise ValueError('Declared empty source unavailable') from None
    finally:
        # Remove ownership before each close; a reported close error is not retried.
        while owned:
            try:
                os.close(owned.pop())
            except BaseException:
                close_failed = True
        if close_failed:
            raise ValueError('Declared empty source close unavailable')


def build(root=ROOT):
    deadline = monotonic() + OPERATION_SECONDS
    def within_budget():
        if monotonic() >= deadline:
            raise InspectionBoundError('Evidence inspection deadline exceeded')
    def budget_read(path, limit):
        within_budget()
        raw = read_file(path, limit)
        within_budget()
        return raw
    def budget_capture(name):
        within_budget()
        result = capture(root, name, reader=budget_read)
        within_budget()
        return result
    def read_source(name, expected):
        within_budget()
        raw = empty_source(root / name) if expected == EMPTY_SHA256 else budget_read(root / name, 32_000_000)
        within_budget()
        return raw
    def check_size():
        if len(captured) > MAX_INPUTS or captured_bytes > MAX_CAPTURED_BYTES:
            raise InspectionBoundError('Evidence inspection input bound exceeded')
        within_budget()
    def retain(name, raw):
        nonlocal captured_bytes
        total = captured_bytes + len(raw) - len(captured.get(name, b''))
        if (name not in captured and len(captured) >= MAX_INPUTS) or total > MAX_CAPTURED_BYTES:
            raise InspectionBoundError('Evidence inspection input bound exceeded')
        captured[name] = raw
        captured_bytes = total
        check_size()

    captured = {}
    captured_bytes = 0
    for name in BASE:
        retain(name, budget_read(root / name, 2_000_000))
    state = budget_capture('state.json')[1]
    ledger = budget_capture('docs/scope-progress.json')[1]
    selected = state['current_engineering_revalidation']
    if type(selected) is not dict:
        raise ValueError('Selected receipt map refused')
    checks = []
    snapshots = {}
    source_drift = False
    source_digests = {}
    for capability in sorted(CAPABILITIES):
        within_budget()
        name = selected.get(capability)
        if (type(name) is not str or not re.fullmatch(r'runs/[a-zA-Z0-9_-]+\.json', name)):
            raise ValueError('Only declared public execution receipts are accepted')
        row = {'capability': capability, 'receipt': name, 'pass': False}
        try:
            raw, receipt = budget_capture(name)
            retain(name, raw)
            check_size()
            # Bind assessment, captured bytes and the final source check to
            # the same fingerprint. A later fingerprint cannot replace it.
            current = fingerprint(capability, root)
            within_budget()
            snapshots[capability] = current
            assessment = assess(receipt, capability, root)
            within_budget()
            if assessment['pass'] and receipt.get('fingerprint') != current:
                source_drift = True
                raise ValueError('Assessment snapshot changed')
            row.update(assessment)
            row['receipt_sha256'] = hashlib.sha256(raw).hexdigest()
            row['executed_at'] = receipt['captured_at'] if assessment['pass'] else None
            # Pin the actual selected source inputs too, including inputs which
            # differ from an older receipt. The index must expose stale evidence.
            for path, expected_digest in current['sources'].items():
                within_budget()
                if path not in source_digests:
                    raw_source = captured.get(path)
                    if raw_source is None:
                        raw_source = read_source(path, expected_digest)
                    actual_digest = hashlib.sha256(raw_source).hexdigest()
                    if actual_digest == expected_digest:
                        retain(path, raw_source)
                        source_digests[path] = actual_digest
                        check_size()
                else:
                    actual_digest = source_digests[path]
                if actual_digest != expected_digest:
                    source_drift = True
                    raise ValueError('Captured source differs from assessed snapshot')
        except InspectionBoundError:
            raise
        except (OSError, ValueError, TypeError, KeyError, RecursionError):
            row['pass'] = False
            row['revalidation_required'] = True
            row['executed_at'] = None
            row['failures'] = ['receipt_or_current_sources_unavailable']
        checks.append(row)
        # In particular, a deadline/size refusal caught above may never be
        # converted into a valid-but-stale packet by the ordinary row fallback.
        check_size()
    records = ledger.get('records')
    expected = {r['id'] for r in budget_capture('docs/master-scope.json')[1]['records']}
    if (type(records) is not list or len(records) != 202
            or len(expected) != 202 or {r['id'] for r in records} != expected
            or any(type(r['percent_complete']) is not int or r['percent_complete'] not in range(0, 101, 20)
                   or type(r['required_acceptance']) is not list
                   or any(type(v) is not str for v in r['required_acceptance']) for r in records)):
        raise ValueError('Full scope identity required')
    open_records = [{'id': r['id'], 'required_acceptance': r['required_acceptance']}
                    for r in records if r['percent_complete'] < 100]
    stable = not source_drift
    for capability, snapshot in snapshots.items():
        within_budget()
        if fingerprint(capability, root) != snapshot:
            stable = False
        within_budget()
    for name, raw in captured.items():
        expected = source_digests.get(name)
        if expected is not None:
            observed = read_source(name, expected)
        else:
            within_budget()
            observed = budget_read(root / name, 32_000_000)
        if observed != raw:
            stable = False
        within_budget()
    check_size()
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
