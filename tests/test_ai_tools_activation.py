"""Finite privileged-activation guard and ownership checks; no services mutate."""
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('activate',ROOT/'deploy/ai-tools/activate.py');a=importlib.util.module_from_spec(s);s.loader.exec_module(a)
class Activation(unittest.TestCase):
    def test_only_owned443_rule_and_namespace(self):
        self.assertEqual(str(a.BASE),'/opt/aitrustid-ai-tools');self.assertEqual(a.UNITS,('aitrustid-ai-tools.service','aitrustid-ai-tools-proxy.service'));self.assertIn('ct state new tcp dport 443 limit rate 40/second burst 80 packets accept',a.RULE);self.assertNotIn('flush',a.RULE);self.assertNotIn('reload',a.RULE)
    def test_existing_rules_preserved_despite_counter_updates(self):
        before=[{'handle':1,'expr':[{'counter':{'packets':1,'bytes':4}},{'accept':None}]}];after=[{'handle':2,'comment':a.TAG,'expr':[{'accept':None}]},{'handle':1,'expr':[{'counter':{'packets':8,'bytes':32}},{'accept':None}]}]
        self.assertTrue(a.preserved(before,after));after[1]['expr'][1]={'drop':None};self.assertFalse(a.preserved(before,after));self.assertFalse(a.preserved(before,after[:1]))
    def test_exclusive_creation_never_overwrites(self):
        with tempfile.TemporaryDirectory()as d:
            p=Path(d)/'owned';a.exclusive(p,b'first')
            with self.assertRaises(FileExistsError):a.exclusive(p,b'second')
            self.assertEqual(p.read_bytes(),b'first');self.assertEqual(p.stat().st_mode&0o777,0o600)
    def test_symlink_and_fifo_reads_refuse_without_hanging(self):
        with tempfile.TemporaryDirectory()as d:
            p=Path(d)/'target';p.write_text('private');link=Path(d)/'link';link.symlink_to(p)
            with self.assertRaises(OSError):a.read_regular(link)
            fifo=Path(d)/'fifo';os.mkfifo(fifo)
            with self.assertRaises(ValueError):a.read_regular(fifo)
            self.assertEqual(p.read_text(),'private')
    def test_atomic_replacement_refuses_preexisting_drift(self):
        with tempfile.TemporaryDirectory()as d:
            p=Path(d)/'config';p.write_bytes(b'other')
            with patch.object(a,'read_regular',return_value=b'other'):
                with self.assertRaises(ValueError):a.atomic_replace(p,b'before',b'after')
            self.assertEqual(p.read_bytes(),b'other');self.assertEqual(list(Path(d).iterdir()),[p])
    def test_atomic_replacement_checks_drift_again_before_commit(self):
        with tempfile.TemporaryDirectory()as d:
            p=Path(d)/'config';p.write_bytes(b'before')
            with patch.object(a,'read_regular',side_effect=[b'before',b'concurrent']):
                with self.assertRaises(ValueError):a.atomic_replace(p,b'before',b'after')
            self.assertEqual(p.read_bytes(),b'before');self.assertEqual(list(Path(d).iterdir()),[p])
    def test_atomic_owned_success_closes_and_preserves_new_bytes(self):
        with tempfile.TemporaryDirectory()as d:
            p=Path(d)/'config';p.write_bytes(b'before')
            with patch.object(a,'read_regular',return_value=b'before'):a.atomic_replace(p,b'before',b'after')
            self.assertEqual(p.read_bytes(),b'after');self.assertEqual(p.stat().st_mode&0o777,0o644)
    def test_constructor_failure_closes_owned_fd_and_removes_private_temp(self):
        import errno
        with tempfile.TemporaryDirectory()as d:
            p=Path(d)/'candidate';opened=[];real=os.open
            def capture(*args,**kwargs):
                fd=real(*args,**kwargs);opened.append(fd);return fd
            with patch.object(os,'open',side_effect=capture),patch.object(os,'fdopen',side_effect=OSError(errno.EIO,'fixed')):
                with self.assertRaises(OSError):a.exclusive(p,b'owned')
            self.assertFalse(p.exists())
            with self.assertRaises(OSError):os.fstat(opened[0])
            p.write_bytes(b'before')
            with patch.object(a,'read_regular',return_value=b'before'),patch.object(os,'fdopen',side_effect=OSError(errno.EIO,'fixed')):
                with self.assertRaises(OSError):a.atomic_replace(p,b'before',b'after')
            self.assertEqual(list(Path(d).iterdir()),[p]);self.assertEqual(p.read_bytes(),b'before')
    def test_close_after_release_never_retries_reused_descriptor(self):
        import errno
        with tempfile.TemporaryDirectory()as d:
            p=Path(d)/'candidate';marker=Path(d)/'marker';marker.write_bytes(b'keep');real=os.close;reused=[]
            def close(fd):
                real(fd);replacement=os.open(marker,os.O_RDONLY);self.assertEqual(replacement,fd);reused.append(replacement);raise OSError(errno.EIO,'fixed')
            try:
                with patch.object(os,'close',side_effect=close):
                    with self.assertRaises(OSError):a.exclusive(p,b'owned')
                self.assertEqual(len(reused),1);self.assertEqual(os.read(reused[0],4),b'keep');self.assertFalse(p.exists())
            finally:
                for fd in reused:real(fd)

    def test_reviewed_exact_source_projection_refuses_coherent_rebind(self):
        import copy
        manifest={'commit':a.APPROVED_COMMIT,'source_sha256':copy.deepcopy(a.APPROVED_SOURCE)}
        self.assertTrue(a.approved_projection(a.APPROVED_COMMIT,manifest))
        for mode in ['source','commit','extra','missing']:
            changed=copy.deepcopy(manifest)
            if mode=='source':changed['source_sha256']['tools/remote_tag_server.py']='0'*64
            if mode=='commit':changed['commit']='0'*40
            if mode=='extra':changed['source_sha256']['private.env']='0'*64
            if mode=='missing':del changed['source_sha256']['NOTICE']
            self.assertFalse(a.approved_projection(a.APPROVED_COMMIT,changed))
        self.assertFalse(a.approved_projection('0'*40,manifest))

    def test_invalid_release_identity_stops_before_any_external_command(self):
        with patch.object(a,'run',side_effect=AssertionError('must not execute')):
            for value in ['main','../x','f'*39,'F'*40,'f'*40+'\n']:
                with self.assertRaises(ValueError):a.checked_release(value)
if __name__=='__main__':unittest.main()
