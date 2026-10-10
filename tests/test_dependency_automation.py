"""Actual configuration and filesystem controls; no simulated bot execution claim."""
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('dependency_automation', ROOT / 'scripts/verify-dependency-automation.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class ProposalPolicy(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        sources = {'.github/CODEOWNERS', '.github/dependabot.yml', '.github/workflows/ci.yml'}
        for ecosystem, directory in m.EXPECTED:
            for name in {'npm': ['package.json', 'package-lock.json'], 'pip': ['requirements.txt', 'requirements.lock'] + (['requirements.freeze'] if directory.startswith('/services/') else []),
                         'docker': ['Dockerfile'], 'github-actions': []}[ecosystem]:
                sources.add(str(Path(directory.lstrip('/')) / name))
        for name in sources:
            (self.root / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, self.root / name)
        self.config = self.root / '.github/dependabot.yml'

    def tearDown(self):
        self.temp.cleanup()

    def change(self, mutate):
        data = json.loads(self.config.read_text())
        mutate(data)
        self.config.write_text(json.dumps(data))

    def refused(self):
        with self.assertRaises((ValueError, TypeError, KeyError)):
            m.verify(self.root)

    def test_current_policy_preserves_execution_limits(self):
        result = m.verify(self.root)
        self.assertEqual(result['monitoring_roots'], 10)
        self.assertFalse(result['scheduled_jobs_observed'])
        self.assertFalse(result['github_configuration_accepted'])

    def test_missing_install_root_refused(self):
        self.change(lambda d: d['updates'].pop())
        self.refused()

    def test_duplicate_root_cannot_replace_missing_root(self):
        self.change(lambda d: d['updates'].__setitem__(-1, d['updates'][0]))
        self.refused()

    def test_inactive_registry_cannot_replace_active_root(self):
        self.change(lambda d: d['updates'][4].__setitem__('directory', '/services/registry/prototype'))
        self.refused()

    def test_extra_execution_permission_refused(self):
        self.change(lambda d: d['updates'][3].__setitem__('insecure-external-code-execution', 'allow'))
        self.refused()

    def test_private_registry_refused(self):
        self.change(lambda d: d.__setitem__('registries', {'private': {'token': 'synthetic'}}))
        self.refused()

    def test_duplicate_json_key_refused(self):
        self.config.write_text(self.config.read_text().replace('"version": 2', '"version": 2, "version": 2', 1))
        self.refused()

    def test_missing_lock_refused(self):
        (self.root / 'eval/requirements.lock').unlink()
        self.refused()

    def test_version_only_proposal_rejected_for_each_python_root(self):
        for directory in ['eval', 'services/gateway', 'services/evaluator', 'services/anonymizer']:
            path = self.root / directory / 'requirements.txt'
            original = path.read_text()
            name = 'PyYAML==6.0.3' if directory == 'eval' else 'fastapi==0.143.0'
            changed = 'PyYAML==6.0.4' if directory == 'eval' else 'fastapi==0.143.1'
            self.assertIn(name, original)
            path.write_text(original.replace(name, changed))
            with self.subTest(directory=directory):
                self.refused()
            path.write_text(original)

    def test_frozen_pin_drift_rejected(self):
        path = self.root / 'services/gateway/requirements.freeze'
        path.write_text(path.read_text().replace('fastapi==0.143.0', 'fastapi==0.143.1'))
        self.refused()

    def test_unreviewed_extra_cannot_keep_old_lock(self):
        path = self.root / 'services/gateway/requirements.txt'
        path.write_text(path.read_text().replace('uvicorn[standard]', 'uvicorn[other]'))
        self.refused()

    def test_false_owner_coverage_refused(self):
        (self.root / '.github/CODEOWNERS').write_text('/site/ @knwvmbrr\n')
        self.refused()

    def test_later_ownership_override_refused(self):
        with (self.root / '.github/CODEOWNERS').open('a') as f:
            f.write('/deploy/ @someone-else\n')
        self.refused()

    def test_symlinked_lock_refused(self):
        path = self.root / 'eval/requirements.lock'
        path.unlink()
        path.symlink_to(self.root / 'eval/requirements.txt')
        self.refused()

    def test_unbounded_proposals_refused(self):
        self.change(lambda d: d['updates'][0].__setitem__('open-pull-requests-limit', True))
        self.refused()

    def test_symlinked_policy_directory_refused(self):
        path = self.root / '.github'
        target = self.root / 'policy-original'
        path.rename(target)
        path.symlink_to(target, target_is_directory=True)
        self.refused()

    def test_symlinked_root_refused(self):
        alias = self.root / 'root-alias'
        alias.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ValueError):
            m.verify(alias)


if __name__ == '__main__':
    unittest.main()
