"""Tiny actual filesystem/fault controls; no SDK, archive, account or network."""
import errno
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import artifact_evidence_io as io


class PublicationOwnership(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.base.chmod(0o700)
        self.output = self.base / 'result.json'
        self.value = {'state': 'COMPLETE', 'count': 1}
        self.raw = io.encoded(self.value) + b'\n'

    def temporary(self):
        paths = list(self.base.glob('.artifact-evidence-*'))
        self.assertEqual(len(paths), 1)
        return paths[0]

    def assert_closed(self, fds):
        for fd in fds:
            with self.assertRaises(OSError) as error:
                os.fstat(fd)
            self.assertEqual(error.exception.errno, errno.EBADF)

    def test_normal_complete_private_atomic_output(self):
        with io.Capture() as captured:
            captured.save(self.output, self.value, 1000)
            owned = list(captured.fds)
        self.assert_closed(owned)
        self.assertEqual(self.output.read_bytes(), self.raw)
        self.assertEqual(self.output.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.output.stat().st_nlink, 1)
        self.assertFalse(list(self.base.glob('.artifact-evidence-*')))

    def test_existing_and_symlink_destinations_never_overwritten(self):
        target = self.base / 'existing'
        target.write_bytes(b'fixed owned sentinel')
        for link in (False, True):
            if link:
                self.output.symlink_to(target)
            else:
                self.output.write_bytes(b'original destination')
            with io.Capture() as captured:
                with self.assertRaises(io.PrivateInputError):
                    captured.save(self.output, self.value, 1000)
            self.assertEqual(target.read_bytes(), b'fixed owned sentinel')
            if not link:
                self.assertEqual(self.output.read_bytes(), b'original destination')
            self.output.unlink()
        self.assertFalse(list(self.base.glob('.artifact-evidence-*')))

    def test_refused_callback_retains_original_and_temporary_successor(self):
        def replaced():
            temporary = self.temporary()
            temporary.rename(self.base / 'original-held')
            temporary.write_bytes(b'replacement must survive')
            raise ValueError('fixed owned callback refusal')
        with self.assertRaisesRegex(ValueError, 'fixed owned callback refusal'):
            with io.Capture() as captured:
                captured.save(self.output, self.value, 1000, prepublish=replaced)
        self.assertFalse(self.output.exists())
        self.assertEqual((self.base / 'original-held').read_bytes(), self.raw)
        self.assertEqual(self.temporary().read_bytes(), b'replacement must survive')

    def test_returning_callback_cannot_publish_successor(self):
        def replaced():
            temporary = self.temporary()
            temporary.rename(self.base / 'original-held')
            temporary.write_bytes(b'replacement must survive')
        with self.assertRaises(io.PrivateInputError):
            with io.Capture() as captured:
                captured.save(self.output, self.value, 1000, prepublish=replaced)
        self.assertFalse(self.output.exists())
        self.assertEqual((self.base / 'original-held').read_bytes(), self.raw)
        self.assertEqual(self.temporary().read_bytes(), b'replacement must survive')

    def test_callback_modified_descriptor_bytes_refuse_before_link(self):
        def changed():
            self.temporary().write_bytes(b'changed owned bytes')
        with self.assertRaises(io.PrivateInputError):
            with io.Capture() as captured:
                captured.save(self.output, self.value, 1000, prepublish=changed)
        self.assertFalse(self.output.exists())
        self.assertEqual(self.temporary().read_bytes(), b'changed owned bytes')

    def test_fdopen_failure_retains_private_temp_and_closes_raw_descriptor(self):
        captured = io.Capture()
        raw_fds = []
        def failed(fd, *args, **kwargs):
            raw_fds.append(fd)
            raise OSError('fixed synthetic open failure')
        with patch.object(io.os, 'fdopen', side_effect=failed):
            with self.assertRaises(OSError):
                with captured:
                    captured.save(self.output, self.value, 1000)
        self.assertFalse(self.output.exists())
        self.assertEqual(self.temporary().stat().st_mode & 0o777, 0o600)
        self.assertEqual(captured.fds, [])
        self.assertEqual(len(raw_fds), 1)
        self.assert_closed(raw_fds)

    def test_partial_stream_write_refusal_has_no_final_output(self):
        original = os.fdopen
        class BrokenStream:
            def __init__(self, fd):
                self.inner = original(fd, 'wb', closefd=False)
            def __enter__(self): return self
            def __exit__(self, *args): self.inner.close()
            def fileno(self): return self.inner.fileno()
            def write(self, raw):
                self.inner.write(raw[:1])
                self.inner.flush()
                raise OSError('fixed synthetic write failure')
        with patch.object(io.os, 'fdopen', side_effect=lambda fd, *a, **k: BrokenStream(fd)):
            with self.assertRaises(OSError):
                with io.Capture() as captured:
                    captured.save(self.output, self.value, 1000)
        self.assertFalse(self.output.exists())
        self.assertEqual(self.temporary().read_bytes(), self.raw[:1])

    def test_post_link_cleanup_failure_is_typed_uncertain(self):
        real = os.unlink
        def failed(name, *args, **kwargs):
            if str(name).startswith('.artifact-evidence-'):
                raise OSError('fixed cleanup failure')
            return real(name, *args, **kwargs)
        with patch.object(io.os, 'unlink', side_effect=failed):
            with self.assertRaises(io.OutputCommitUncertain):
                with io.Capture() as captured:
                    captured.save(self.output, self.value, 1000)
        self.assertEqual(self.output.read_bytes(), self.raw)
        self.assertEqual(self.temporary().read_bytes(), self.raw)

    def test_post_link_temporary_successor_is_retained_not_unlinked(self):
        real = os.link
        def replaced(source, target, *args, **kwargs):
            real(source, target, *args, **kwargs)
            temporary = self.base / source
            temporary.rename(self.base / 'original-held')
            temporary.write_bytes(b'post-link successor survives')
        with patch.object(io.os, 'link', side_effect=replaced):
            with self.assertRaises(io.OutputCommitUncertain):
                with io.Capture() as captured:
                    captured.save(self.output, self.value, 1000)
        self.assertEqual(self.output.read_bytes(), self.raw)
        self.assertEqual((self.base / 'original-held').read_bytes(), self.raw)
        self.assertEqual(self.temporary().read_bytes(), b'post-link successor survives')

    def test_post_link_parent_sync_failure_is_typed_uncertain(self):
        real = os.fsync
        def failed(fd):
            if stat.S_ISDIR(os.fstat(fd).st_mode):
                raise OSError('fixed parent sync failure')
            return real(fd)
        with patch.object(io.os, 'fsync', side_effect=failed):
            with self.assertRaises(io.OutputCommitUncertain):
                with io.Capture() as captured:
                    captured.save(self.output, self.value, 1000)
        self.assertEqual(self.output.read_bytes(), self.raw)

    def test_close_fault_attempts_every_owned_fd_once(self):
        captured = io.Capture()
        captured.save(self.output, self.value, 1000)
        owned = list(captured.fds)
        closed = []
        real = os.close
        def failed(fd):
            self.assertNotIn(fd, closed)
            closed.append(fd)
            real(fd)
            if len(closed) == 1:
                raise OSError('fixed close-after-release failure')
        with patch.object(io.os, 'close', side_effect=failed):
            with self.assertRaises(io.OutputCommitUncertain): captured.close()
            captured.close()
        self.assertCountEqual(closed, owned)
        self.assert_closed(owned)
        self.assertEqual(self.output.read_bytes(), self.raw)

    def test_git_marker_during_callback_refuses_no_final(self):
        def changed(): (self.base / '.git').write_text('owned synthetic marker')
        with self.assertRaises(io.PrivateInputError):
            with io.Capture() as captured:
                captured.save(self.output, self.value, 1000, prepublish=changed)
        self.assertFalse(self.output.exists())
        self.assertEqual(self.temporary().read_bytes(), self.raw)

    def test_git_marker_after_save_is_uncertain_and_still_closes_all(self):
        captured = io.Capture()
        captured.save(self.output, self.value, 1000)
        owned = list(captured.fds)
        (self.base / '.git').write_text('owned synthetic marker')
        with self.assertRaises(io.OutputCommitUncertain): captured.close()
        self.assert_closed(owned)
        self.assertEqual(self.output.read_bytes(), self.raw)

    def test_private_ancestor_marker_and_mode_rechecked_through_close(self):
        inner = self.base / 'inner'
        inner.mkdir(mode=0o700)
        for mode in ('ancestor-marker', 'private-mode'):
            captured = io.Capture()
            captured.parent(inner / 'new.json')
            owned = list(captured.fds)
            if mode == 'ancestor-marker': (self.base / '.git').write_text('owned marker')
            else: inner.chmod(0o755)
            with self.assertRaises(io.PrivateInputError): captured.check()
            with self.assertRaises(io.PrivateInputError): captured.close()
            self.assert_closed(owned)
            if mode == 'ancestor-marker': (self.base / '.git').unlink()
            else: inner.chmod(0o700)

    def test_cached_public_descriptor_cannot_bypass_private_git_boundary(self):
        with io.Capture() as captured:
            captured.parent(self.output, private=False)
            (self.base / '.git').write_text('owned marker')
            with self.assertRaises(io.PrivateInputError): captured.parent(self.output)


if __name__ == '__main__':
    unittest.main()
