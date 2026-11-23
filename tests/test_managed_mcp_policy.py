"""Finite permission controls; injected review boundary is not artifact approval."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import mcp_release_policy as r
from tools import mcp_distribution as m
from tools import dependency_policy as policy
from tools.artifact_evidence_io import Capture


class FiniteGrantPolicy(unittest.TestCase):
    def component(self):
        value = json.loads((ROOT / policy.POLICY).read_bytes())
        return value['components'][r.COMPONENT], value['routes']['mcp-stdio']

    def test_actual_factual_assessment_matches_retained_data(self):
        raw = (ROOT / r.ASSESSMENT).read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), r.ASSESSMENT_SHA256)
        record = m.decode(raw)
        with Capture() as capture:
            actual = r.facts(capture, ROOT, m.decode((ROOT / m.PROFILE_FILE).read_bytes()))
            capture.check()
        self.assertEqual(record['facts'], actual)
        self.assertEqual(len(actual['targets']), 4)
        self.assertTrue(all(value is False for value in record['claims'].values()))
        for name, digest in r.REVIEW_FILES.items():
            self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), digest)

    def test_carried_project_schema_and_unicode_license_changes_alter_facts(self):
        profile = m.decode((ROOT / m.PROFILE_FILE).read_bytes())
        with Capture() as capture:
            expected = r.facts(capture, ROOT, profile)
            capture.check()
        class ChangedGrantReader:
            def __init__(self, selected, actual): self.selected, self.actual = selected, actual
            def read(self, path, limit, **kwargs):
                if Path(path) == ROOT / self.selected:
                    return b'owned synthetic different license; no permission inferred'
                return self.actual.read(path, limit, **kwargs)
        for name in ('LICENSE', 'NOTICE', 'spec/LICENSE', 'eval/vectors/unicode/LICENSE.txt'):
            self.assertIn(name, expected['inputs'])
            with self.subTest(path=name), Capture() as capture:
                changed = r.facts(ChangedGrantReader(name, capture), ROOT, profile)
                capture.check()
                self.assertNotEqual(changed, expected)

    def test_current_unfixed_helper_or_source_drift_cannot_receive_permission(self):
        # This integration contract holds both before and after normal protected
        # base integration. It never substitutes the fixed helper with a flag.
        actual = hashlib.sha256((ROOT / 'tools/artifact_evidence_io.py').read_bytes()).hexdigest()
        if actual != r.FIXED_IO_SHA256:
            with self.assertRaises(ValueError): r.review(ROOT)
            self.assertFalse(policy.evaluate('mcp-stdio', ROOT)['release_allowed'])
        else:
            # On a current integrated checkout the real complete source/profile
            # inspection, not a test-side approximation, must pass.
            self.assertTrue(r.review(ROOT)['runtime_source_profile_verified'])
            self.assertTrue(policy.evaluate('mcp-stdio', ROOT)['release_allowed'])

    def test_exact_component_positive_then_scoped_mutations_refuse(self):
        component, selected = self.component()
        with patch.object(r, 'review', return_value={'runtime_source_profile_verified': True}):
            self.assertEqual(r.component_status(component, selected, ROOT)[0], 'allowed')
            mutations = [
                lambda c, s: c.update(license_expression='MIT'),
                lambda c, s: c.update(assessment='pending'),
                lambda c, s: c.update(required_processing_payment=0),
                lambda c, s: c['files'].pop(),
                lambda c, s: c['notice_paths'].pop(),
                lambda c, s: c['files'][0].update(sha256='0' * 64),
                lambda c, s: s.update(prerequisites=['No prerequisites']),
                lambda c, s: s.update(kind='source-only'),
                lambda c, s: s['dependencies'][0].update(required=1),
                lambda c, s: s.update(entrypoints=['caller command']),
            ]
            for mutate in mutations:
                c, s = copy.deepcopy(component), copy.deepcopy(selected)
                mutate(c, s)
                with self.subTest(mutation=mutate):
                    self.assertEqual(r.component_status(c, s, ROOT)[0], 'blocked_unknown')

    def test_paid_closed_and_missing_review_keep_distinct_refusals(self):
        component, selected = self.component()
        for updates, expected in [({'required_processing_payment': True}, 'paid'),
                                  ({'source_available': False}, 'prohibited')]:
            c = copy.deepcopy(component)
            c.update(updates)
            self.assertEqual(r.component_status(c, selected, ROOT)[0], expected)
        with patch.object(r, 'review', side_effect=ImportError('fixed unavailable review')):
            self.assertEqual(r.component_status(component, selected, ROOT)[0], 'blocked_unknown')

    def test_coherent_assessment_edit_does_not_approve_itself(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            path = base / r.ASSESSMENT
            path.parent.mkdir(parents=True)
            value = json.loads((ROOT / r.ASSESSMENT).read_bytes())
            value['claims']['legal_clearance'] = True
            path.write_bytes(m.canonical(value))
            with self.assertRaises(ValueError): r.review(base)

    def test_unavailable_optional_module_does_not_poison_ps_or_other_routes(self):
        before = {route: policy.evaluate(route, ROOT)
                  for route in policy.ROUTES - {'mcp-stdio'}}
        self.assertEqual(len(before), 13)
        self.assertIs(before['ps-source']['release_allowed'], True)
        self.assertIs(before['source-snapshot']['release_allowed'], True)
        with patch.object(r, 'component_status', side_effect=ImportError('fixed unavailable optional module')):
            self.assertIs(policy.evaluate('mcp-stdio', ROOT)['release_allowed'], False)
            for route, expected in before.items():
                self.assertEqual(policy.evaluate(route, ROOT), expected)


if __name__ == '__main__':
    unittest.main()
