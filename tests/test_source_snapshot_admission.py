"""Copy permission cannot be manufactured from a packet or a status flag."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import source_snapshot_admission as a
from tools import dependency_policy as p

ROOT = Path(__file__).resolve().parents[1]
LEGACY_6D = '6d752cd0ae127e7d1ebe93499ab6fd83f55dcafd'
SELECTED = '9c98ac5000a2784df66d8e1f5bf17d34cb0f53b7'


class SourceSnapshotAdmission(unittest.TestCase):
    def rows(self):
        policy = json.loads((ROOT / p.POLICY).read_bytes())
        return policy['components'][a.COMPONENT], policy['routes']['source-snapshot']

    def test_real_current_source_copy_not_runtime_accuracy_or_signature(self):
        from tools import source_release_policy_v3 as legacy
        from tools import source_release_policy_v4 as current
        historical = legacy.verify(source_commit=LEGACY_6D)
        self.assertIs(historical['pass'], True)
        self.assertEqual(historical['profile'], legacy.PROFILE)
        self.assertEqual(historical['source_commit'], LEGACY_6D)
        self.assertEqual(historical['files'], 13502)
        self.assertEqual(historical['source_bytes'], 142114658)
        for key in legacy.FALSE_CLAIMS:
            self.assertIs(historical[key], False)
        result = a.review(source_commit=SELECTED)
        self.assertIs(result['pass'], True)
        self.assertEqual(result['profile'], current.PROFILE)
        self.assertEqual(result['source_commit'], SELECTED)
        self.assertEqual(result['files'], 13747)
        self.assertEqual(result['source_bytes'], 147265706)
        for key in ('legal_clearance', 'compiled_runtime_permission',
                    'source_archive_admitted', 'release_authorized', 'accuracy',
                    'complete_F057_X02'):
            self.assertIs(result[key], False)

    def test_source_admission_requires_actual_finite_classifier(self):
        component, route = self.rows()
        with patch.object(a, 'review', side_effect=ValueError('unavailable')) as check:
            self.assertEqual(a.component_status(component, route)[0], 'blocked_unknown')
            check.assert_called_once()

    def test_altered_source_hash_and_updated_status_flag_do_not_bypass(self):
        component, route = self.rows()
        row = next(row for row in component['files'] if row['path'] == 'LICENSE')
        row['sha256'] = '0' * 64
        with patch.object(a, 'review', side_effect=AssertionError('must refuse first')):
            self.assertEqual(a.component_status(component, route)[0], 'blocked_unknown')

    def test_foreign_route_or_extra_entrypoint_cannot_inherit_copy_rights(self):
        component, route = self.rows()
        for field, value in (('kind', 'bundled-runtime'),
                             ('entrypoints', ['services/evaluator/app.py']),
                             ('prerequisites', ['All runtimes approved'])):
            altered = copy.deepcopy(route)
            altered[field] = value
            with patch.object(a, 'review', side_effect=AssertionError('must refuse first')):
                self.assertEqual(a.component_status(component, altered)[0], 'blocked_unknown')

    def test_paid_and_closed_cannot_be_relabelled_as_copy_only(self):
        component, route = self.rows()
        for field, value, state in (('required_processing_payment', True, 'paid'),
                                    ('source_available', False, 'prohibited')):
            altered = copy.deepcopy(component)
            altered[field] = value
            with patch.object(a, 'review', side_effect=AssertionError('must refuse first')):
                self.assertEqual(a.component_status(altered, route)[0], state)

    def test_missing_notice_unknown_member_or_boolean_number_refuses(self):
        component, route = self.rows()
        for field, value in (('notice_paths', []), ('required_processing_payment', 0),
                             ('source_available', 1)):
            altered = copy.deepcopy(component)
            altered[field] = value
            self.assertEqual(a.component_status(altered, route)[0], 'blocked_unknown')
        altered = copy.deepcopy(component)
        altered['files'].append({'path': 'unreviewed.py', 'sha256': '0' * 64, 'bytes': 1})
        self.assertEqual(a.component_status(altered, route)[0], 'blocked_unknown')

    def test_caller_chosen_checkout_cannot_supply_approval(self):
        with tempfile.TemporaryDirectory() as name:
            with self.assertRaises(ValueError):
                a.review(root=Path(name), source_commit=SELECTED)

    def test_unavailable_copy_route_never_disables_standalone_ps(self):
        before = p.require_route('ps-source')
        with patch.object(a, 'component_status', return_value=('blocked_unknown', 'test_unavailable')):
            self.assertIs(p.evaluate('source-snapshot')['release_allowed'], False)
            self.assertEqual(p.require_route('ps-source'), before)

    def test_received_copy_report_with_forged_authority_or_commit_refuses(self):
        from tools import source_release_policy_v4 as source
        actual = source.verify(source_commit=SELECTED)
        self.assertIs(actual['pass'], True)
        baseline = a.review(source_commit=SELECTED)
        self.assertIs(baseline['pass'], True)
        self.assertEqual(baseline['source_commit'], SELECTED)
        self.assertEqual(baseline['profile'], source.PROFILE)
        for key, value in (('pass', 1), ('source_copy_profile_satisfied', 1),
                           ('source_commit', '0' * 40), ('release_authorized', True),
                           ('files', True), ('accuracy', True)):
            altered = copy.deepcopy(actual)
            altered[key] = value
            with patch.object(source, 'verify', return_value=altered):
                with self.assertRaises(ValueError):
                    a.review(source_commit=SELECTED)

    def test_source_spdx_retains_every_identity_and_edge_when_prose_is_deduplicated(self):
        from tools import distribution_artifacts as artifacts
        nodes = [{'key': 'git:' + name, 'name': name, 'version': None,
                  'origin': 'committed-git-blob', 'evidence': 'scripts/source_snapshot_v3.py',
                  'checksums': [], 'details': {'git_blob_oid': oid, 'mode': '100644'}}
                 for name, oid in (('LICENSE', 'a' * 40), ('scripts/check-ps.py', 'b' * 40))]
        graph = {'nodes': nodes, 'relationships': [], 'source_sha256': {'LICENSE': 'c' * 64}}
        document = artifacts.spdx('source-snapshot', {'sha256': 'd' * 64}, graph,
                                  '2026-11-23T18:00:00Z')
        components = document['packages'][1:]
        self.assertEqual({row['name'] for row in components}, {row['name'] for row in nodes})
        self.assertEqual(len(document['relationships']), 3)
        for node in nodes:
            component = next(row for row in components if row['name'] == node['name'])
            self.assertIn(node['details']['git_blob_oid'], component['sourceInfo'])
            self.assertIn('mode 100644', component['sourceInfo'])
            self.assertNotIn('checksums', component)
            self.assertEqual(component['licenseConcluded'], 'NOASSERTION')
            self.assertTrue(any(row.get('relatedSpdxElement') == component['SPDXID'] and
                                row['relationshipType'] == 'OTHER'
                                for row in document['relationships']))
        self.assertIn('not a containment or permission claim', document['comment'])
        self.assertTrue(all(row.get('comment') == 'Source evidence'
                            for row in document['relationships']
                            if row['relationshipType'] == 'OTHER'))


if __name__ == '__main__':
    unittest.main()
