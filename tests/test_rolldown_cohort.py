"""Evidence refusal controls; synthetic mutations are not legal clearance."""
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest

from tools import rolldown_cohort as review


class RolldownCohortTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.value = json.loads((review.ROOT / review.MANIFEST).read_text())
        paths = [review.MANIFEST, 'site/package-lock.json', 'sbom/native/manifest.json',
                 'sbom/notices/manifest.json', *review.FILES,
                 *(text['path'] for text in self.value['source_texts'])]
        for name in paths:
            target = self.root / name; target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(review.ROOT / name, target)
        self.addCleanup(self.temp.cleanup)

    def save(self):
        (self.root / review.MANIFEST).write_text(json.dumps(self.value))

    def refused(self):
        self.save()
        with self.assertRaises(ValueError):
            review.verify(self.root)

    def test_current_evidence_preserves_unknowns(self):
        result = review.verify(self.root)
        self.assertTrue(result['pass'])
        self.assertEqual(result['native_addons'], 15)
        self.assertFalse(result['binary_bytes_replayed'])
        self.assertTrue(all(result[key] is False for key in review.FLAGS))

    def test_missing_previously_overlooked_third_party_notice_refused(self):
        wrapper = next(p for p in self.value['packages'] if p['selector'] is None)
        del wrapper['bundled_notices']['THIRD-PARTY-LICENSE']
        self.refused()

    def test_truncated_notice_content_refused(self):
        text = next(t for t in self.value['source_texts'] if t['member'] == 'THIRD-PARTY-LICENSE')
        (self.root / text['path']).write_bytes(b'MIT')
        with self.assertRaises(ValueError): review.verify(self.root)

    def test_wrong_platform_selector_refused(self):
        self.value['packages'][0]['package_json']['cpu'] = ['x64']
        self.refused()

    def test_wrong_wrapper_optional_version_refused(self):
        wrapper = next(p for p in self.value['packages'] if p['selector'] is None)
        wrapper['package_json']['optionalDependencies']['@rolldown/binding-darwin-arm64'] = '1.2.14'
        self.refused()

    def test_changed_native_member_hash_refused(self):
        self.value['packages'][0]['native_member']['sha256'] = '0' * 64
        self.refused()

    def test_current_lock_source_mismatch_refused(self):
        path = self.root / 'site/package-lock.json'
        value = json.loads(path.read_text())
        value['packages']['node_modules/rolldown']['version'] = '1.2.14'
        path.write_text(json.dumps(value))
        with self.assertRaises(ValueError): review.verify(self.root)

    def test_legal_or_compiler_permission_promotion_refused(self):
        for key in review.FLAGS:
            with self.subTest(key=key):
                original = self.value[key]; self.value[key] = True
                self.refused(); self.value[key] = original

    def test_changed_verifier_source_refused(self):
        (self.root / review.FILES[0]).write_text('changed')
        with self.assertRaises(ValueError): review.verify(self.root)

    def test_unsafe_duplicate_and_link_members_refused(self):
        cases = [('package/../private', 'file'), ('package/LICENSE', 'link'), ('package/LICENSE', 'duplicate')]
        for name, kind in cases:
            with self.subTest(kind=kind):
                stream = io.BytesIO()
                with tarfile.open(fileobj=stream, mode='w:gz') as archive:
                    for _ in range(2 if kind == 'duplicate' else 1):
                        item = tarfile.TarInfo(name)
                        if kind == 'link': item.type = tarfile.SYMTYPE; item.linkname = '/private'
                        archive.addfile(item)
                with self.assertRaises(ValueError): review.members(stream.getvalue())

    def test_cli_refusal_has_no_private_argument_echo(self):
        canary = 'AUTHORED_PRIVATE_ARG_CANARY'
        result = subprocess.run([sys.executable, '-B', str(review.ROOT / 'scripts/verify-rolldown-cohort.py'), '--unknown=' + canary], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, '')
        self.assertEqual(result.stderr, 'Rolldown cohort evidence unavailable.\n')
        self.assertNotIn(canary, result.stderr)


if __name__ == '__main__': unittest.main()
