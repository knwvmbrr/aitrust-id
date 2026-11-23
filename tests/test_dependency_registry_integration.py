"""Closed registry assertions against real decisions, with bounded fault injection."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('registry_guard', ROOT / 'scripts/verify-dependency-policy.py')
GUARD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GUARD)


class RegistryIntegration(unittest.TestCase):
    def test_actual_current_two_routes_and_ps_contract(self):
        result = GUARD.verify()
        self.assertTrue(result['pass'])
        self.assertEqual(result['registered_routes'], 14)
        self.assertEqual(result['allowed_routes'], ['mcp-stdio', 'ps-source'])
        self.assertEqual(result['allowed_source_routes'], ['ps-source'])
        self.assertEqual(result['source_files'], 9)
        self.assertEqual(len(result['blocked_routes']), 12)
        self.assertIs(result['managed_release_signature_verified_by_registry'], False)

    def test_exact_route_status_boolean_and_claim_faults_refuse(self):
        actual = {route: GUARD.evaluate(route, ROOT) for route in GUARD.ROUTES}
        faults = [
            ('mcp-stdio', {'release_allowed': False, 'status': 'blocked_unknown'}),
            ('source-snapshot', {'release_allowed': True, 'status': 'allowed'}),
            ('ps-source', {'release_allowed': 1}),
            ('mcp-stdio', {'release_allowed': 1}),
            ('source-snapshot', {'release_allowed': 0}),
            ('mcp-stdio', {'status': 'blocked_unknown'}),
            ('mcp-stdio', {'reason': 'invalid_or_unavailable_policy'}),
            ('ps-source', {'legal_clearance': True}),
            ('mcp-stdio', {'complete_project_obligations': 0}),
            ('source-snapshot', {'independent_accuracy_evidence': None}),
        ]
        for route, changes in faults:
            with self.subTest(route=route, changes=changes):
                altered = copy.deepcopy(actual)
                altered[route].update(changes)
                with patch.object(GUARD, 'evaluate', side_effect=lambda name, root: altered[name]):
                    with self.assertRaises(ValueError):
                        GUARD.verify()

    def test_missing_route_and_invalid_registry_refuse(self):
        actual = GUARD.evaluate
        def missing(route, root):
            result = actual(route, root)
            if route == 'mcp-stdio':
                result['route'] = 'ps-source'
            return result
        with patch.object(GUARD, 'evaluate', side_effect=missing):
            with self.assertRaises(ValueError):
                GUARD.verify()
        with patch.object(GUARD, 'load', side_effect=ValueError('fixed synthetic refusal')):
            with self.assertRaises(ValueError):
                GUARD.verify()

    def test_actual_isolated_cli_faults_are_fixed_and_private(self):
        for fault in ('load', 'mcp_blocked', 'extra_allowed'):
            with self.subTest(fault=fault):
                code = '''import sys, runpy
sys.path.insert(0, sys.argv[1])
from tools import dependency_policy as p
fault = sys.argv[2]
original = p.evaluate
def evaluate(route, root):
    row = original(route, root)
    if fault == 'mcp_blocked' and route == 'mcp-stdio':
        row.update(release_allowed=False, status='blocked_unknown')
    if fault == 'extra_allowed' and route == 'source-snapshot':
        row.update(release_allowed=True, status='allowed')
    return row
def refused(root):
    raise ValueError('PRIVATE_SYNTHETIC_REGISTRY_CANARY')
if fault == 'load': p.load = refused
else: p.evaluate = evaluate
runpy.run_path(sys.argv[1] + '/scripts/verify-dependency-policy.py', run_name='__main__')
'''
                result = subprocess.run([sys.executable, '-I', '-S', '-B', '-c', code,
                                         str(ROOT), fault], capture_output=True, timeout=10)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stderr, b'')
                self.assertEqual(json.loads(result.stdout),
                                 {'pass': False, 'reason': 'dependency_registry_refused'})
                self.assertNotIn(b'PRIVATE_SYNTHETIC_REGISTRY_CANARY', result.stdout)


if __name__ == '__main__':
    unittest.main()
