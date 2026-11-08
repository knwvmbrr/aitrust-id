#!/usr/bin/env python3
"""Bind the selected native software proof to current code; never grant phone release."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[1]
PROOF = 'runs/2026-11-07-native-share-bounded-workflow.json'
ASSETS = {'/index.html', '/bridge.mjs', '/method.py', '/device-manifest.json',
          '/runtime/pyodide.mjs', '/runtime/pyodide.asm.mjs', '/runtime/pyodide.asm.wasm',
          '/runtime/python_stdlib.zip', '/runtime/pyodide-lock.json'}


def verify(root=ROOT, proof=None):
    value = json.loads((root / PROOF).read_text()) if proof is None else proof
    required = {'pass': True, 'physical_device': False, 'independent_accuracy': False,
                'human_accessibility': False, 'installable_phone_release': False,
                'source_unchanged_during_execution': True, 'owned_simulator_removed': True}
    if not isinstance(value, dict) or any(value.get(key) is not expected for key, expected in required.items()):
        raise ValueError('Native software proof boundary is invalid')
    if type(value.get('test_count')) is not int or value['test_count'] != 5:
        raise ValueError('Complete native workflow execution is required')
    if value.get('profile') != 'invented-text/UIActivityViewController/local-PS/simulator/v1':
        raise ValueError('Unknown native workflow profile')
    date = datetime.fromisoformat(value['captured_at'])
    if date.tzinfo is None or date > datetime.now(timezone.utc):
        raise ValueError('Native proof date is invalid')
    module = runpy.run_path(str(root / 'scripts/verify-ios-share.py'))
    expected_sources = {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                        for name in module['SOURCES']}
    if value.get('sources') != expected_sources:
        raise ValueError('Native sources changed; run the actual native workflow again')
    method = hashlib.sha256((root / 'services/evaluator/app.py').read_bytes()).hexdigest()
    if value.get('method_sha256') != method:
        raise ValueError('Native method changed')
    hashes = value.get('asset_fingerprints')
    if not isinstance(hashes, dict) or set(hashes) != ASSETS or any(
            not isinstance(k, str) or not k.startswith('/') or '..' in Path(k).parts
            or not isinstance(v, str) or len(v) != 64 or any(c not in '0123456789abcdef' for c in v)
            for k, v in hashes.items()):
        raise ValueError('Native asset identity is incomplete')
    progress = json.loads((root / 'docs/scope-progress.json').read_text())
    row = next(r for r in progress['records'] if r['id'] == 'N-013')
    if row['percent_complete'] >= 100 or row.get('completed_at') or row.get('completed_by'):
        raise ValueError('Simulator evidence cannot complete physical/human acceptance')
    try:
        bundle = runpy.run_path(str(root / 'scripts/native_bundle.py'))['assets']()
    except (ValueError, OSError, KeyError, TypeError):
        raise ValueError('Prepare current native assets before validating their execution proof') from None
    actual = json.loads(bundle['Assets/native-assets.json'])['hashes']
    if hashes != actual:
        raise ValueError('Native bundle differs from the executed assets; run the native workflow again')
    return {'pass': True, 'native_ui_workflows': 5, 'physical_device': False,
            'independent_accuracy': False, 'requirement_complete': False}


if __name__ == '__main__':
    try:
        print(json.dumps(verify()))
    except (ValueError, OSError, KeyError, TypeError, StopIteration):
        print('Native software evidence is missing, stale or overclaimed.', file=sys.stderr)
        raise SystemExit(1)
