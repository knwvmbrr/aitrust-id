"""The forced SSH boundary rejects shells and unapproved remote operations."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('backup_remote', Path(__file__).parents[1] / 'deploy/backup/remote.py')
remote = importlib.util.module_from_spec(spec)
spec.loader.exec_module(remote)


class ProtocolBoundary(unittest.TestCase):
    def test_known_protocol(self):
        argv = remote.validate('pgbackrest --stanza=aitrustid --command=backup --remote-type=pg --process=1 remote')
        self.assertEqual(argv[0], '/usr/bin/pgbackrest')
        self.assertEqual(argv[-1], 'remote')

    def test_current_protocol_and_multiple_locks(self):
        argv = remote.validate('pgbackrest --stanza=aitrustid --remote-type=pg --lock=a --lock=b stanza-create:remote')
        self.assertEqual(argv[-1], 'stanza-create:remote')

    def test_rejects_shells_and_unapproved_operations(self):
        for command in ['', 'bash', 'rm -rf /var/lib/pgbackrest',
                        'pgbackrest --stanza=aitrustid --command=restore --remote-type=pg remote',
                        'pgbackrest --stanza=other --command=backup --remote-type=pg remote',
                        'pgbackrest --stanza=aitrustid --command=backup --remote-type=pg --config=/tmp/evil remote',
                        'pgbackrest --stanza=aitrustid --remote-type=pg restore:remote',
                        'pgbackrest --stanza=aitrustid --command=restore --remote-type=pg backup:remote',
                        'pgbackrest --stanza=other --stanza=aitrustid --command=backup --remote-type=pg remote',
                        'pgbackrest --stanza=aitrustid --remote-type=pg --cmd-ssh=/bin/bash backup:remote',
                        'pgbackrest --stanza=aitrustid --remote-type=pg --pg1-path=/home/postgres backup:remote',
                        'pgbackrest --stanza=aitrustid --command=backup --remote-type=pg remote; id']:
            with self.subTest(command=command), self.assertRaises(ValueError):
                remote.validate(command)
