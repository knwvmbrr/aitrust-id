"""Owned inert filesystem controls; no SDK, pip, archive parsing or subprocess."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import mcp_distribution as m


class DeveloperWorkspaceRetention(unittest.TestCase):
    def test_failed_install_retains_private_workspace_without_recursive_delete(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            root.chmod(0o700)
            archive = root / 'inert.zip'
            archive.write_bytes(b'inert owned bytes')
            output = root / 'connection.json'
            result = {'target': 'inert-only'}
            calls = []
            def refuse(*args, **kwargs):
                calls.append(True)
                raise m.DistributionError('fixed first runtime refusal')
            with patch.object(m, 'verify', return_value=(result, {})), \
                 patch.object(m.shutil, 'disk_usage', return_value=type('Disk', (), {'free': 4*1024**3})()), \
                 patch.object(m, 'command', side_effect=refuse), \
                 patch.object(m.shutil, 'rmtree', side_effect=AssertionError('no pathname cleanup')):
                with self.assertRaises(m.DistributionError):
                    m.install(archive, output, python=sys.executable, pip_python=sys.executable)
            self.assertEqual(calls, [True])
            self.assertFalse(output.exists())
            workspaces = list(root.glob('.mcp-install-*'))
            self.assertEqual(len(workspaces), 1)
            self.assertEqual(workspaces[0].stat().st_mode & 0o777, 0o700)
            self.assertEqual(sorted(x.name for x in workspaces[0].iterdir()), ['tmp'])


if __name__ == '__main__':
    unittest.main()
