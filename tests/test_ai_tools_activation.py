"""Finite privileged-activation guard and ownership checks; no services mutate."""
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch,Mock,MagicMock
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

    def test_readiness_waits_for_positive_health_with_fixed_budget(self):
        import asyncio
        calls=[]
        async def attempt():calls.append(1);return len(calls)==2
        with patch.object(a,'health_attempt',side_effect=attempt):self.assertEqual(a.wait_private_health(),{'ready':True,'attempts':2})
        async def blocked():await asyncio.sleep(1);return True
        with patch.object(a,'health_attempt',side_effect=blocked):
            with self.assertRaisesRegex(ValueError,'private_health_unavailable'):a.wait_private_health(.02)
    def test_late_positive_is_refused_after_absolute_deadline(self):
        clock=[0]
        async def late():clock[0]=6;return True
        with patch.object(a,'ready_now',side_effect=lambda:clock[0]),patch.object(a,'health_attempt',side_effect=late):
            with self.assertRaisesRegex(ValueError,'private_health_unavailable'):a.wait_private_health(5)
    def test_canonical_unit_record_refuses_coherent_rebind(self):
        import copy
        hashes={n:a.digest(t.encode())for n,t in a.render.units(a.APPROVED_COMMIT).items()}
        state={'commit':a.APPROVED_COMMIT,'unit_sha256':hashes,'installed_units':list(a.UNITS)};plan={'release_commit':a.APPROVED_COMMIT,'unit_sha256':copy.deepcopy(hashes),'release_source_sha256':a.APPROVED_SOURCE,'caddyfile_sha256':a.digest(a.render.caddyfile().encode()),'rule_tag':a.TAG,'public_port':443,'host':a.render.HOST}
        self.assertTrue(a.approved_record(state,plan));badstate=copy.deepcopy(state);badplan=copy.deepcopy(plan);badstate['unit_sha256'][a.UNITS[0]]='0'*64;badplan['unit_sha256'][a.UNITS[0]]='0'*64;self.assertFalse(a.approved_record(badstate,badplan))
    def test_private_preparation_cannot_insert_rule_or_start_proxy(self):
        with tempfile.TemporaryDirectory()as d:
            base=Path(d).resolve();files={'Caddyfile':a.render.caddyfile(),**a.render.units(a.APPROVED_COMMIT)};commands=[];units={};real=a.exclusive;exists=Path.exists;islink=Path.is_symlink
            def ex(path,data,mode=0o600):
                if str(path).startswith('/etc/systemd/system/'):
                    units[path.name]=data;return
                return real(path,data,mode)
            def run(argv,timeout=20):
                commands.append(argv)
                return b'not-found'if argv[:2]==['systemctl','show']else b''
            def present(path):
                if str(path).startswith('/etc/systemd/system/aitrustid-ai-tools')or str(path)=='/var/lib/aitrustid-ai-tools-proxy':return False
                return exists(path)
            def linked(path):
                if str(path).startswith('/etc/systemd/system/aitrustid-ai-tools'):return False
                return islink(path)
            def read(path,limit=131072):return b'base'if str(path)=='/etc/nftables.conf'else Path(path).read_bytes()
            with patch.object(a,'BASE',base),patch.object(a,'checked_release',return_value=(base,{'source_sha256':a.APPROVED_SOURCE},files)),patch.object(a,'input_rules',return_value=[]),patch.object(a,'run',side_effect=run),patch.object(a,'read_regular',side_effect=read),patch.object(a,'exclusive',side_effect=ex),patch.object(a,'wait_private_health',return_value={'ready':True,'attempts':2}),patch.object(a,'isolation_proof',return_value={'pass':True}),patch.object(Path,'exists',present),patch.object(Path,'is_symlink',linked):
                result=a.activate(a.APPROVED_COMMIT,True,'192.0.2.1')
            self.assertTrue(result['pass']);self.assertEqual(result['phase'],'private_isolation_ready');self.assertFalse(result['public_activation_performed']);self.assertEqual(set(units),set(a.UNITS));self.assertFalse([x for x in commands if x[0]=='nft'and'-c'not in x]);self.assertNotIn(['systemctl','start',a.UNITS[1]],commands)
    def test_public_resume_refuses_incomplete_private_stage_before_mutation(self):
        with patch.object(a,'checked_record',return_value=(Path('/owned'),{'phase':'private_app_started'},{})),patch.object(a,'run',side_effect=AssertionError('must not mutate')):
            with self.assertRaisesRegex(ValueError,'private_acceptance_unavailable'):a.publish('/owned','192.0.2.1')

    def test_invalid_release_identity_stops_before_any_external_command(self):
        with patch.object(a,'run',side_effect=AssertionError('must not execute')):
            for value in ['main','../x','f'*39,'F'*40,'f'*40+'\n']:
                with self.assertRaises(ValueError):a.checked_release(value)
if __name__=='__main__':unittest.main()
