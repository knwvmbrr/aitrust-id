#!/usr/bin/env python3
"""Audit the complete route registry without turning refusal into clearance."""
import hashlib
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.dependency_policy import ROUTES, load, validate_route, evaluate, require_route


def verify():
    value, raw = load(ROOT)
    used = set()
    for route in value['routes'].values():
        validate_route(route, value['components'])
        used.update(item['component'] for item in route['dependencies'])
    if used != set(value['components']):
        raise ValueError('Orphan dependency component')
    decisions = [evaluate(route, ROOT) for route in sorted(ROUTES)]
    if ({row['route'] for row in decisions} != ROUTES or
            any(row.get('reason') == 'invalid_or_unavailable_policy' for row in decisions)):
        raise ValueError('Invalid route graph')
    selected = require_route('ps-source', ROOT)
    allowed = {'ps-source', 'mcp-stdio', 'source-snapshot'}
    for row in decisions:
        expected = row['route'] in allowed
        if (type(row.get('release_allowed')) is not bool or
                row['release_allowed'] is not expected or
                row.get('status') != ('allowed' if expected else 'blocked_unknown') or
                any(row.get(claim) is not False for claim in
                    ('legal_clearance', 'complete_project_obligations',
                     'independent_accuracy_evidence'))):
            raise ValueError('Unreviewed policy promotion or unavailable reviewed route')
    if (len(selected['files']) != 9 or selected['route'] != 'ps-source'):
        raise ValueError('Changed PS source export contract')
    return {'pass': True, 'profile': value['profile'], 'registered_routes': len(decisions),
            'allowed_source_routes': ['ps-source', 'source-snapshot'],
            'allowed_routes': sorted(allowed),
            'managed_mcp_consumer': 'scripts/install-managed-mcp.py',
            'managed_source_consumer': 'scripts/verify-managed-source.py',
            'managed_release_signature_verified_by_registry': False,
            'blocked_routes': [row['route'] for row in decisions if not row['release_allowed']],
            'source_files': len(selected['files']),
            'selected_policy_sha256': selected['policy_sha256'],
            'registry_sha256': hashlib.sha256(raw).hexdigest(),
            'enforced_export_consumer': 'scripts/export-ps-source.py',
            'other_existing_consumers_promoted': False,
            'legal_clearance': False, 'complete_project_obligations': False,
            'independent_accuracy_evidence': False}


if __name__ == '__main__':
    try:
        print(json.dumps(verify(), sort_keys=True))
    except (OSError, ValueError, TypeError, KeyError, RecursionError):
        print(json.dumps({'pass': False, 'reason': 'dependency_registry_refused'}))
        raise SystemExit(2)
