"""Exercise source changes, exact approval, expiry and disconnected destinations."""
from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('announcements', ROOT / 'scripts/release-announcements.py')
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)


class Announcements(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'communications/releases').mkdir(parents=True)
        (self.root / 'proof.txt').write_text('checked source')
        self.brief = {'id': 'a-release', 'version': '1 development preview', 'title': 'Specific change',
                      'use_case': 'One bounded use case', 'summary': 'Actual behavior',
                      'limits': 'Not independent accuracy evidence', 'url': 'https://aitrustid.com/reference/conformance/',
                      'evidence': ['proof.txt']}
        self.save()
        self.now = datetime.now(timezone.utc)
        self.accounts = {'accounts': [{'platform': 'bluesky', 'handle': 'AITRUSTID', 'connection_verified': True}]}

    def save(self):
        (self.root / 'communications/releases/a-release.json').write_text(json.dumps(self.brief))

    def approval(self, queue):
        return {'draft_sha256': queue['drafts'][0]['draft_sha256'], 'platform': 'bluesky', 'handle': 'AITRUSTID',
                'approved_by': 'Michael', 'approved_at': (self.now - timedelta(minutes=1)).isoformat(),
                'expires_at': (self.now + timedelta(days=1)).isoformat()}

    def test_exact_handoff_is_deterministic_and_does_not_send(self):
        queue = a.drafts(self.root)
        approval = self.approval(queue)
        first = a.handoff(queue, self.accounts, approval, self.now)
        self.assertEqual(first, a.handoff(queue, self.accounts, approval, self.now))
        self.assertFalse(first['network_post_performed'])
        self.assertEqual(queue['drafts'][0]['status'], 'awaiting_owner_review')
        self.assertIn(self.brief['use_case'], first['text'])
        self.assertIn(self.brief['limits'], first['text'])

    def test_copy_or_evidence_change_requires_new_approval(self):
        original = a.drafts(self.root)
        approval = self.approval(original)
        self.brief['summary'] = 'Changed behavior'
        self.save()
        with self.assertRaises(ValueError):
            a.handoff(a.drafts(self.root), self.accounts, approval, self.now)
        self.brief['summary'] = 'Actual behavior'
        self.save()
        (self.root / 'proof.txt').write_text('different source')
        with self.assertRaises(ValueError):
            a.handoff(a.drafts(self.root), self.accounts, approval, self.now)

    def test_approval_owner_account_and_time_are_required(self):
        queue = a.drafts(self.root)
        original = self.approval(queue)
        for field, value in [('approved_by', 'Codex'), ('handle', 'unrelated'), ('platform', 'other'),
                             ('approved_at', self.now.replace(tzinfo=None).isoformat()),
                             ('expires_at', (self.now - timedelta(seconds=1)).isoformat()),
                             ('expires_at', (self.now + timedelta(days=8)).isoformat())]:
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                a.handoff(queue, self.accounts, {**original, field: value}, self.now)
        for accounts in ({'accounts': []}, {'accounts': self.accounts['accounts'] * 2},
                         {'accounts': [{**self.accounts['accounts'][0], 'connection_verified': False}]}):
            with self.assertRaises(ValueError):
                a.handoff(queue, accounts, original, self.now)

    def test_only_explicit_public_sources_and_official_urls(self):
        for field, value in [('url', 'https://aitrustid.com.evil.invalid/'), ('url', 'https://aitrustid.com/?token=secret'),
                             ('evidence', ['../private']), ('evidence', ['/etc/passwd']), ('evidence', ['missing']),
                             ('evidence', [])]:
            with self.subTest(field=field, value=value):
                brief = self.brief.copy()
                self.brief[field] = value
                self.save()
                with self.assertRaises(ValueError):
                    a.drafts(self.root)
                self.brief = brief
        self.save()
        (self.root / 'proof.txt').unlink()
        (self.root / 'proof.txt').symlink_to(ROOT / 'README.md')
        with self.assertRaises(ValueError):
            a.drafts(self.root)


if __name__ == '__main__':
    unittest.main()
