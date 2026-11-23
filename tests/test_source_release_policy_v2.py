"""Selected source-copy profile v2; tiny controls without SDKs or source archives."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('source_copy_v2', ROOT / 'tools/source_release_policy_v2.py')
p = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(p)
SELECTED = '6d752cd0ae127e7d1ebe93499ab6fd83f55dcafd'


def blob(raw):
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


class SourceCopyV2(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = (ROOT / p.POLICY).read_bytes()
        cls.legacy_raw = (ROOT / p.LEGACY).read_bytes()
        cls.d, cls.legacy, cls.expected = p.policy(cls.raw, cls.legacy_raw)
        cls.observed = {name: row[:3] for name, row in cls.expected.items()}

    def check(self, observed, reader=None):
        return p.checked(self.d, self.legacy, self.expected, observed,
                         reader or (lambda *a: self.fail('immutable blobs must not be decoded')), lambda: None)

    def test_real_selected_copy_contract_and_all_false_nonclaims(self):
        result = p.verify(source_commit=SELECTED)
        self.assertTrue(result['pass'], result)
        self.assertEqual(result['source_commit'], SELECTED)
        self.assertEqual(result['files'], 13502)
        self.assertEqual(result['source_bytes'], 142114658)
        self.assertIs(result['selected_profile_base_is_protected_release'], True)
        for key in p.FALSE_CLAIMS:
            self.assertIs(result[key], False)

    def test_complete_inheritance_and_explicit615_delta(self):
        self.assertEqual(len(self.d['delta']), 615)
        self.assertEqual(len(self.expected), 13502)
        for old in self.legacy['files']:
            self.assertIn(old[0], self.expected)
            self.assertEqual(self.expected[old[0]][3], old[4])
        self.assertTrue(all(self.check(self.observed)[key] == 0 for key in
                            ('changed_named_project_text_files', 'introduced_named_project_text_files')))

    def test_unknown_path_and_missing_notice_are_not_zero_observations(self):
        observed = dict(self.observed)
        observed['docs/unreviewed-future.py'] = ('100644', blob(b'# SPDX-License-Identifier: Apache-2.0\n'), 38)
        with self.assertRaises(p.Refused) as error:
            self.check(observed)
        self.assertEqual(error.exception.code, 'unknown_path')
        for name in ('LICENSE', 'site/public/fonts/OFL.txt', 'sbom/mcp-runtime/THIRD-PARTY-NOTICES.txt',
                     'sbom/mcp-rust-stdlib/RUST-STDLIB-NOTICES.txt'):
            altered = dict(self.observed)
            altered.pop(name)
            with self.assertRaises(p.Refused) as error:
                self.check(altered)
            self.assertEqual(error.exception.code, 'missing_path')

    def test_changed_grants_and_copied_source_refuse_before_decode(self):
        for name in ('spec/LICENSE', 'eval/vectors/unicode/LICENSE.txt',
                     'sbom/cffi-libffi/sources/libffi-3.4.6-LICENSE',
                     'sbom/mcp-runtime/obligations.json.gz', 'sbom/mcp-runtime/THIRD-PARTY-NOTICES.txt'):
            altered = dict(self.observed)
            mode, oid, size = altered[name]
            altered[name] = (mode, '0' * 40, size)
            with self.assertRaises(p.Refused):
                self.check(altered)

    def test_named_project_edits_preserve_exact_declaration(self):
        name = 'README.md'
        self.assertEqual(self.expected[name][3], 'project-text')
        good = b'An authored documentation update.\n'
        altered = dict(self.observed)
        altered[name] = ('100644', blob(good), len(good))
        self.assertEqual(self.check(altered, lambda *a: good)['changed_named_project_text_files'], 1)
        bad = b'# SPDX-License-Identifier: GPL-3.0-only\n'
        altered[name] = ('100644', blob(bad), len(bad))
        with self.assertRaises(p.Refused) as error:
            self.check(altered, lambda *a: bad)
        self.assertEqual(error.exception.code, 'license_declaration_changed')

    def test_only_exact_new_v2_paths_can_use_project_grant(self):
        good = b'# SPDX-License-Identifier: Apache-2.0\n'
        altered = dict(self.observed)
        altered['tools/source_release_policy_v2.py'] = ('100644', blob(good), len(good))
        self.assertEqual(self.check(altered, lambda *a: good)['introduced_named_project_text_files'], 1)
        bad = b'# Copyright An Unreviewed Third Party\n'
        altered['tools/source_release_policy_v2.py'] = ('100644', blob(bad), len(bad))
        with self.assertRaises(p.Refused):
            self.check(altered, lambda *a: bad)
        altered['tools/other_future_helper.py'] = altered.pop('tools/source_release_policy_v2.py')
        with self.assertRaises(p.Refused):
            self.check(altered, lambda *a: bad)

    def test_coherent_policy_rebinding_never_chooses_its_own_authority(self):
        altered = json.loads(self.raw)
        altered['origins']['reviewed-project-authored']['license'] = 'Invented permission'
        forged = json.dumps(altered, sort_keys=True).encode()
        with self.assertRaises(p.Refused) as error:
            p.policy(forged, self.legacy_raw)
        self.assertEqual(error.exception.code, 'policy_changed')
        with self.assertRaises(p.Refused):
            p.policy(self.raw, self.legacy_raw + b'\n')

    def test_typed_field_aliases_and_false_claims_refuse_under_parser_control(self):
        for mutate in (lambda d: d.update(selected_files=True),
                       lambda d: d.update(selected_raw_bytes=True),
                       lambda d: d['claims'].update(legal_clearance=0),
                       lambda d: d.update(selected_is_protected_release=0),
                       lambda d: d['delta'][0].__setitem__(3, True)):
            d = json.loads(self.raw)
            mutate(d)
            raw = json.dumps(d).encode()
            # Isolate schema validation after the independently tested digest gate.
            with patch.object(p, 'POLICY_SHA256', p.sha(raw)):
                with self.assertRaises(p.Refused):
                    p.policy(raw, self.legacy_raw)

    def test_listing_caps_modes_and_empty_baseline_fail_closed(self):
        valid = b'100644 blob ' + b'1' * 40 + b' 1\tx\0'
        self.assertEqual(p.tree_rows(valid), ({'x': ('100644', '1' * 40, 1)}, 1))
        for raw in (valid * 16385, valid[:-1], valid.replace(b'100644', b'120000'),
                    valid.replace(b' 1\t', b' 32000001\t'), b''):
            with self.assertRaises(p.Refused):
                p.tree_rows(raw)
        with self.assertRaises(p.Refused):
            p.tree_rows(b'x' * (p.MAX_LISTING + 1))

    def test_invalid_observed_bool_and_changed_text_budget_refuse(self):
        altered = dict(self.observed)
        name = 'README.md'
        altered[name] = ('100644', '1' * 40, True)
        with self.assertRaises(p.Refused):
            self.check(altered)
        altered[name] = ('100644', '1' * 40, p.MAX_CHANGED_TEXT + 1)
        with self.assertRaises(p.Refused) as error:
            self.check(altered)
        self.assertEqual(error.exception.code, 'resource_limit')

    def test_captured_neutral_worker_ignores_repository_module_cache(self):
        import types
        poisoned = types.ModuleType('scripts.worker_process')
        poisoned.run_worker = lambda *a, **k: self.fail('repository module imported')
        with patch.dict(sys.modules, {'scripts.worker_process': poisoned}):
            run = p.worker()
            result = run([sys.executable, '-I', '-S', '-B', '-c', 'print("OWNED")'],
                         input=b'', timeout=5, output_limit=128)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, b'OWNED\n')

    def test_inherited_git_configuration_does_not_choose_source(self):
        with patch.dict(os.environ, {'GIT_DIR': '/PRIVATE_GIT_CANARY', 'GIT_WORK_TREE': '/PRIVATE_GIT_CANARY',
                                     'GIT_REPLACE_REF_BASE': 'refs/PRIVATE_GIT_CANARY', 'GIT_CONFIG_COUNT': '999999'}):
            result = p.verify(source_commit=SELECTED)
        self.assertTrue(result['pass'], result)
        self.assertNotIn('PRIVATE_GIT_CANARY', json.dumps(result))

    def test_actual_isolated_cli_selection_and_fixed_refusals(self):
        script = str(ROOT / 'tools/source_release_policy_v2.py')
        for args in (['--source-commit', SELECTED], ['--unknown=PRIVATE_ARGUMENT_CANARY'],
                     ['--source-commit', 'PRIVATE_ARGUMENT_CANARY'], ['--source-commit', '0' * 40]):
            result = subprocess.run([sys.executable, '-I', '-S', '-B', script, *args],
                                    cwd='/tmp', capture_output=True, timeout=35)
            self.assertEqual(result.stderr, b'')
            value = json.loads(result.stdout)
            self.assertIs(value['pass'], args == ['--source-commit', SELECTED])
            self.assertEqual(result.returncode, 0 if value['pass'] else 2)
            self.assertNotIn(b'PRIVATE_ARGUMENT_CANARY', result.stdout)

    def test_legacy_v1_bytes_remain_immutable(self):
        self.assertEqual(p.sha((ROOT / p.LEGACY).read_bytes()), p.LEGACY_SHA256)
        self.assertEqual(p.sha((ROOT / 'tools/source_release_policy.py').read_bytes()), p.LEGACY_HELPER_SHA256)
        self.assertEqual(p.sha((ROOT / 'tests/test_source_release_policy.py').read_bytes()),
                         'c6ce003e4abfa0c3b70b0a8604551eb9651156e79e42517a2343c54c82b4dab6')


if __name__ == '__main__':
    unittest.main()
