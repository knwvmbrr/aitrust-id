"""Security/delivery contracts, including retries and deduplication."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch
import ssl
import os
import stat
from types import SimpleNamespace

spec = importlib.util.spec_from_file_location('alerts', Path(__file__).parents[1] / 'deploy/alerts/alerts.py')
alerts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(alerts)
CONFIG = {'smtp_host': 'smtp.example.org', 'smtp_port': 587, 'tls_mode': 'starttls',
          'username': 'dedicated-user', 'password': 'private-token',
          'sender': 'alerts@example.org', 'recipient': 'admin@aitrustid.com'}


class OperationalAlerts(unittest.TestCase):
    def test_systemd_credential_mount_boundary(self):
        path = Path('/run/credentials/aitrust-alerts.service/delivery.json')
        info = SimpleNamespace(st_uid=0, st_gid=0, st_mode=stat.S_IFREG | 0o440)
        parent = SimpleNamespace(st_uid=0, st_gid=0, st_mode=stat.S_IFDIR | 0o550)
        with patch.dict(os.environ, {'CREDENTIALS_DIRECTORY': str(path.parent)}), patch.object(Path, 'lstat', return_value=parent):
            self.assertTrue(alerts.systemd_credential(path, info))
            self.assertFalse(alerts.systemd_credential(Path('/tmp/delivery.json'), info))
            for mode in (stat.S_IFDIR | 0o555, stat.S_IFDIR | 0o750, stat.S_IFLNK | 0o550):
                parent.st_mode = mode
                self.assertFalse(alerts.systemd_credential(path, info))
            parent.st_mode = stat.S_IFDIR | 0o550
            parent.st_uid = os.geteuid() or 123
            self.assertFalse(alerts.systemd_credential(path, info))
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(alerts.systemd_credential(path, info))

    def test_notification_destination_and_redirects(self):
        good = {'transport':'ntfy', 'base_url':'https://notify.aitrustid.com',
                'topic':'aitrust-primary-ops', 'token':'tk_' + 'a' * 29}
        self.assertEqual(alerts.validated_config(good), good)
        for change in ({'base_url':'http://notify.aitrustid.com'},
                       {'base_url':'https://attacker.example'}, {'topic':'another-topic'},
                       {'token':'secret\nHeader: injected'}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                alerts.validated_config({**good, **change})
        with self.assertRaises(ValueError):
            alerts.RejectRedirect().redirect_request(None,None,302,'',{},'https://attacker.example')

    def test_tls_port_and_header_validation(self):
        for change in ({'tls_mode': 'none'}, {'smtp_port': 25}, {'smtp_port': True},
                       {'recipient': 'x@example.org\nBcc: evil@example.org'}, {'extra': 'x'}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                alerts.validated_config({**CONFIG, **change})

    def test_private_file_only(self):
        import json
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'smtp.json'
            path.write_text(json.dumps(CONFIG))
            path.chmod(0o644)
            with self.assertRaises(ValueError):
                alerts.load_config(path)
            path.chmod(0o600)
            self.assertEqual(alerts.load_config(path), CONFIG)
            link = Path(directory) / 'link'
            link.symlink_to(path)
            with self.assertRaises(OSError):
                alerts.load_config(link)

    def test_tls_precedes_auth_and_failure_never_authenticates(self):
        client = MagicMock()
        calls = []
        client.starttls.side_effect = lambda **kw: calls.append('tls')
        client.login.side_effect = lambda *a: calls.append('auth')
        client.send_message.return_value = {}
        with patch.object(alerts.smtplib, 'SMTP', return_value=client):
            alerts.deliver(CONFIG, alerts.message(CONFIG, 'primary', 'test', []))
        self.assertEqual(calls, ['tls', 'auth'])
        context = client.starttls.call_args.kwargs['context']
        self.assertTrue(context.check_hostname)
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
        client.reset_mock()
        client.starttls.side_effect = ssl.SSLCertVerificationError('synthetic')
        with patch.object(alerts.smtplib, 'SMTP', return_value=client), self.assertRaises(ssl.SSLCertVerificationError):
            alerts.deliver(CONFIG, alerts.message(CONFIG, 'primary', 'test', []))
        client.login.assert_not_called()
        client.send_message.assert_not_called()

    def test_incident_repeat_recovery_and_heartbeat(self):
        kind, digest = alerts.plan({}, ['ssh.service:failed'], 10000)
        self.assertEqual(kind, 'incident')
        previous = {'digest': digest, 'had_issues': True, 'sent_at': 10000}
        self.assertIsNone(alerts.plan(previous, ['ssh.service:failed'], 10100)[0])
        self.assertEqual(alerts.plan(previous, ['ssh.service:failed'], 13600)[0], 'incident')
        self.assertEqual(alerts.plan(previous, [], 10100)[0], 'recovered')
        kind, digest = alerts.plan({}, [], 10000)
        self.assertEqual(kind, 'heartbeat')
        previous = {'digest': digest, 'had_issues': False, 'sent_at': 10000}
        self.assertIsNone(alerts.plan(previous, [], 11000)[0])
        self.assertEqual(alerts.plan(previous, [], 96400)[0], 'heartbeat')

    def test_failed_delivery_retries_and_test_does_not_silence(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'sent.json'
            with patch.object(alerts, 'inspect', return_value=['ssh.service:failed']), patch.object(alerts, 'deliver', side_effect=OSError('synthetic')):
                with self.assertRaises(OSError):
                    alerts.run(CONFIG, 'primary', path)
            self.assertFalse(path.exists())
            with patch.object(alerts, 'inspect', return_value=['ssh.service:failed']), patch.object(alerts, 'deliver') as deliver:
                self.assertEqual(alerts.run(CONFIG, 'primary', path, test=True)['kind'], 'test')
                self.assertFalse(path.exists())
                self.assertEqual(alerts.run(CONFIG, 'primary', path)['kind'], 'incident')
                self.assertEqual(alerts.run(CONFIG, 'primary', path)['action'], 'suppressed')
                self.assertEqual(deliver.call_count, 2)

    def test_checks_detect_missing_failed_and_stopped_required_units(self):
        result = MagicMock(stdout='LoadState=loaded\nActiveState=active\nResult=success\n')
        with patch.object(alerts.subprocess, 'run', return_value=result):
            self.assertEqual(alerts.inspect('primary'), [])
        for output in ('LoadState=not-found\n', 'LoadState=loaded\nActiveState=failed\nResult=exit-code\n', 'LoadState=loaded\nActiveState=inactive\nResult=success\n'):
            with patch.object(alerts.subprocess, 'run', return_value=MagicMock(stdout=output)):
                self.assertTrue(alerts.inspect('primary'))


if __name__ == '__main__':
    unittest.main()
