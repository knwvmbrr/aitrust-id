"""Strict metadata, credential and entitlement boundaries; no network/provider."""
import json
import unittest
import uuid

from tools import account_core as c

NOW = 1800000000


def record():
    return {'event_id': str(uuid.uuid4()), 'displayed_at': NOW, 'adapter': 'summary-import',
            'tag': 'PS', 'state': 'FINDING',
            'method': {'name': 'rules-only', 'revision': 'context-v6', 'sha256': 'a' * 64}}


class AccountCoreTests(unittest.TestCase):
    def test_import_metadata_and_unknown_content_fields(self):
        value = record()
        saved = c.history_record(value, NOW)
        self.assertEqual(saved['source_label'], 'Imported summary')
        self.assertEqual(saved['display_binding'], 'client_summary_import')
        self.assertFalse(saved['verified_assertion'])
        self.assertFalse(saved['input_included'])
        for field in ('text', 'url', 'subject_sha256', 'email', 'research_consent', 'account_id', 'explanation'):
            with self.subTest(field=field), self.assertRaises(c.AccountError):
                c.history_record({**value, field: 'PRIVATE_INPUT_CANARY'}, NOW)
        for method in ({**value['method'], 'sha256': True}, {**value['method'], 'name': '<script>'}):
            with self.assertRaises(c.AccountError):
                c.history_record({**value, 'method': method}, NOW)

    def test_canonical_identifiers_passwords_and_failed_states(self):
        for name in ('Alice', 'ab', 'a@example.test', '../alice', 'x' * 33):
            with self.assertRaises(c.AccountError):
                c.username(name)
        for secret in ('short', 'x' * 129, 'x' * 15 + '\0', '\ud800' * 15):
            with self.assertRaises(c.AccountError):
                c.password_bytes(secret)
        self.assertNotEqual(c.password_bytes('long passphrase café'), c.password_bytes('long passphrase cafe\u0301'))
        value = record()
        with self.assertRaises(c.AccountError):
            c.history_record({**value, 'state': 'UNAVAILABLE'}, NOW)
        saved = c.history_record({**value, 'state': 'UNAVAILABLE', 'method': None}, NOW)
        self.assertEqual(saved['explanation'], 'No valid check completed.')

    def test_duplicate_nonfinite_and_deep_json_refuse(self):
        for raw in (b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":' + b'[' * 33 + b'0' + b']' * 33 + b'}', b'x' * 16385):
            with self.assertRaises(c.AccountError):
                c.parse(raw)
        self.assertEqual(c.parse(b'{"literal":"{{[quoted]}"}'), {'literal': '{{[quoted]}'})

    def test_entitlements_require_exact_server_shape_and_live_expiry(self):
        owner = str(uuid.uuid4())
        good = {'format': 'account-history-entitlement/v1', 'account_id': owner, 'state': 'ACTIVE', 'valid_until': NOW + 1, 'revision': 1}
        self.assertEqual(c.assessment(lambda *_: good, owner, NOW), good)
        for bad in ({**good, 'paid': True}, {**good, 'account_id': str(uuid.uuid4())}, {**good, 'valid_until': NOW}, {**good, 'revision': True}):
            self.assertEqual(c.assessment(lambda *_: bad, owner, NOW)['state'], 'UNAVAILABLE')
        def failed(*unused):
            raise RuntimeError('PRIVATE_ENGINE_CANARY')
        self.assertNotIn('CANARY', json.dumps(c.assessment(failed, owner, NOW)))

    def test_session_secret_csrf_and_hash_are_separate(self):
        first, second = c.token(), c.token()
        self.assertNotEqual(first, second)
        self.assertEqual(len(c.token_hash(first)), 32)
        self.assertEqual(len(c.csrf(first)), 64)
        self.assertNotEqual(c.csrf(first), c.token_hash(first).hex())
        with self.assertRaises(c.AccountError):
            c.token_hash('invalid')


if __name__ == '__main__':
    unittest.main()
