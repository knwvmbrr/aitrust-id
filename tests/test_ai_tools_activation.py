"""Finite privileged-activation guard and ownership checks; no services mutate."""
import importlib.util
import os
from pathlib import Path
import tempfile
import json
import stat
from contextlib import ExitStack,nullcontext
import unittest
from unittest.mock import patch,Mock,MagicMock
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('activate',ROOT/'deploy/ai-tools/activate.py');a=importlib.util.module_from_spec(s);s.loader.exec_module(a)
class SyntheticHost:
    """Real owned files, modeled root metadata/commands; never host services."""
    def __enter__(self):
        self.stack=ExitStack();self.top=Path(self.stack.enter_context(tempfile.TemporaryDirectory())).resolve()
        self.base=self.top/'base';self.base.mkdir(mode=0o700);self.units=self.top/'units';self.units.mkdir();self.firewall=self.top/'nftables.conf';self.firewall.write_bytes(b'original firewall');self.commands=[];self.rules=[]
        self.files={'Caddyfile':a.render.caddyfile(),**a.render.units(a.APPROVED_COMMIT)}
        real_path=Path
        def selected(value):
            path=real_path(value)
            if str(path)=='/etc/systemd/system':return self.units
            if str(path).startswith('/etc/systemd/system/'):return self.units/path.name
            if str(path)=='/etc/nftables.conf':return self.firewall
            if str(path)=='/var/lib/aitrustid-ai-tools-proxy':return self.top/'absent-proxy-state'
            return path
        def read(path,limit=131072):
            path=real_path(path);info=path.lstat()
            if not stat.S_ISREG(info.st_mode)or info.st_mode&0o022 or info.st_size>limit:raise ValueError('test_file_refused')
            return path.read_bytes()
        def run(args,timeout=20):
            self.commands.append(args)
            if args[:2]==['systemctl','show']:return b'inactive'if 'ActiveState'in args else b'not-found'
            if args[:2]==['systemctl','is-active']:return b'active'
            if args[:2]==['nft','insert']:self.rules.append({'family':'inet','table':'aitrust_host','chain':'input','handle':7,'comment':a.TAG,'expr':[{'counter':{'packets':1,'bytes':12}},{'accept':None}]})
            if args[:3]==['nft','delete','rule']:self.rules[:]=[r for r in self.rules if str(r['handle'])!=args[-1]]
            return b''
        for target,name,value in [(a,'BASE',self.base),(a,'Path',selected),(a,'read_regular',read),(a,'run',run),(a,'input_rules',lambda:list(self.rules)),(a,'root_owned_record',lambda p:p.is_dir()and not p.stat().st_mode&0o022),(a,'checked_release',lambda commit:(self.base,{'source_sha256':a.APPROVED_SOURCE},self.files)),(a,'wait_private_health',lambda:{'ready':True,'attempts':1}),(a,'isolation_proof',lambda *args:{'pass':True})]:self.stack.enter_context(patch.object(target,name,side_effect=value)if callable(value)else patch.object(target,name,value))
        return self
    def __exit__(self,*args):return self.stack.__exit__(*args)
    def apply(self):
        result=a.activate(a.APPROVED_COMMIT,True,'192.0.2.1');assert result['pass'];return Path(result['record'])
    def state(self,record):return json.loads((record/'state.json').read_bytes())
    def save(self,record,state):(record/'state.json').write_text(json.dumps(state))

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
        with SyntheticHost()as host:
            result=a.activate(a.APPROVED_COMMIT,True,'192.0.2.1')
            self.assertTrue(result['pass']);self.assertEqual(result['phase'],'private_isolation_ready');self.assertFalse(result['public_activation_performed']);self.assertEqual(set(p.name for p in host.units.iterdir()),set(a.UNITS));self.assertFalse([x for x in host.commands if x[0]=='nft'and'-c'not in x]);self.assertNotIn(['systemctl','start',a.UNITS[1]],host.commands)

    def test_public_resume_refuses_incomplete_private_stage_before_mutation(self):
        with patch.object(a,'operation_lock',return_value=nullcontext()),patch.object(a,'checked_record',return_value=(Path('/owned'),{'phase':'private_app_started'},{})),patch.object(a,'run',side_effect=AssertionError('must not mutate')):
            with self.assertRaisesRegex(ValueError,'private_acceptance_unavailable'):a.publish('/owned','192.0.2.1')

    def test_invalid_release_identity_stops_before_any_external_command(self):
        with patch.object(a,'run',side_effect=AssertionError('must not execute')):
            for value in ['main','../x','f'*39,'F'*40,'f'*40+'\n']:
                with self.assertRaises(ValueError):a.checked_release(value)
    def test_retired_record_cannot_remove_actual_new_activation(self):
        with SyntheticHost()as host:
            old=host.apply();old_epoch=host.state(old)['ownership_epoch']
            self.assertTrue(a.rollback(old)['record_retired']);self.assertEqual(host.state(old)['phase'],'rolled_back');self.assertFalse((host.base/'active-record.json').exists())
            replacement=host.apply();self.assertNotEqual(old,replacement);self.assertNotEqual(old_epoch,host.state(replacement)['ownership_epoch']);before={p.name:p.read_bytes()for p in host.units.iterdir()};host.commands.clear()
            with self.assertRaises(ValueError):a.rollback(old)
            self.assertEqual(host.commands,[]);self.assertEqual(before,{p.name:p.read_bytes()for p in host.units.iterdir()})
            # Even editing the old terminal phase cannot borrow the new epoch.
            stale=host.state(old);stale['phase']='private_isolation_ready';host.save(old,stale)
            with self.assertRaisesRegex(ValueError,'record_ownership_refused'):a.rollback(old)
            self.assertEqual(host.commands,[]);self.assertEqual(before,{p.name:p.read_bytes()for p in host.units.iterdir()})
    def test_legacy_unanchored_record_refuses_before_any_resource_mutation(self):
        with SyntheticHost()as host:
            record=host.apply();state=host.state(record)
            for key in ['ownership_record','ownership_epoch','unit_identity']:state.pop(key)
            host.save(record,state);host.commands.clear();before={p.name:p.read_bytes()for p in host.units.iterdir()}
            with self.assertRaises(ValueError):a.rollback(record)
            self.assertEqual(host.commands,[]);self.assertEqual(before,{p.name:p.read_bytes()for p in host.units.iterdir()})
    def test_all_resource_drift_preflights_before_first_stop(self):
        for fault in ['unit_bytes','unit_same_bytes_new_inode','unrecorded_rule','wrong_handle','persistence']:
            with self.subTest(fault=fault),SyntheticHost()as host:
                record=host.apply();state=host.state(record)
                if fault=='unit_bytes':(host.units/a.UNITS[0]).write_bytes(b'changed')
                elif fault=='unit_same_bytes_new_inode':
                    target=host.units/a.UNITS[0];replacement=host.units/'new';replacement.write_bytes(target.read_bytes());os.replace(replacement,target)
                elif fault=='unrecorded_rule':host.rules.append({'comment':a.TAG,'handle':7})
                elif fault=='wrong_handle':state['rule_handle']=8;host.save(record,state);host.rules.append({'comment':a.TAG,'handle':7})
                else:host.firewall.write_bytes(b'changed')
                host.commands.clear()
                with self.assertRaises(ValueError):a.rollback(record)
                self.assertEqual(host.commands,[]);self.assertEqual(host.state(record)['phase'],'private_isolation_ready');self.assertTrue((host.base/'active-record.json').exists())
    def test_recorded_rule_definition_refuses_semantic_drift_before_stop(self):
        with SyntheticHost()as host:
            record=host.apply();self.assertTrue(a.publish(record,'192.0.2.1')['pass']);self.assertEqual(host.state(record)['rule_definition'],a.owned_rule_definition(host.rules[0]));host.rules[0]['expr'][-1]={'drop':None};host.commands.clear()
            with self.assertRaisesRegex(ValueError,'rule_changed'):a.rollback(record)
            self.assertEqual(host.commands,[]);self.assertTrue(all((host.units/n).exists()for n in a.UNITS));self.assertTrue((host.base/'active-record.json').exists())
    def test_only_mutable_counter_values_are_ignored_on_owned_rule(self):
        with SyntheticHost()as host:
            record=host.apply();self.assertTrue(a.publish(record,'192.0.2.1')['pass']);host.rules[0]['expr'][0]['counter'].update(packets=999,bytes=123456);self.assertTrue(a.rollback(record)['record_retired']);self.assertEqual(host.rules,[]);self.assertEqual(host.firewall.read_bytes(),b'original firewall')
        self.assertNotEqual(a.owned_rule_definition({'expr':[{'match':{'bytes':1}}]}),a.owned_rule_definition({'expr':[{'match':{'bytes':2}}]}))

    def test_unit_created_before_ledger_save_is_not_silently_adopted(self):
        with SyntheticHost()as host:
            record=host.apply();state=host.state(record);state['installed_units'].remove(a.UNITS[1]);state['unit_identity'].pop(a.UNITS[1]);host.save(record,state);host.commands.clear()
            with self.assertRaisesRegex(ValueError,'unit_unrecorded'):a.rollback(record)
            self.assertEqual(host.commands,[]);self.assertTrue(all((host.units/n).exists()for n in a.UNITS));self.assertTrue((host.base/'active-record.json').exists())

    def test_first_rollback_state_write_failure_keeps_resources_and_lease(self):
        with SyntheticHost()as host:
            record=host.apply();before={p.name:p.read_bytes()for p in host.units.iterdir()};host.commands.clear()
            with patch.object(a,'save_state',side_effect=OSError('fixed')):
                with self.assertRaises(OSError):a.rollback(record)
            self.assertEqual(host.commands,[]);self.assertEqual(before,{p.name:p.read_bytes()for p in host.units.iterdir()});self.assertTrue((host.base/'active-record.json').exists())
    def test_terminal_write_failure_blocks_replacement_then_same_record_recovers(self):
        with SyntheticHost()as host:
            record=host.apply();save=a.save_state
            def fail(p,state):
                if state['phase']=='rolled_back':raise OSError('fixed')
                return save(p,state)
            with patch.object(a,'save_state',side_effect=fail):
                with self.assertRaises(OSError):a.rollback(record)
            self.assertEqual(host.state(record)['phase'],'rollback_in_progress');self.assertEqual(list(host.units.iterdir()),[]);self.assertTrue((host.base/'active-record.json').exists());host.commands.clear()
            with self.assertRaisesRegex(ValueError,'active_record_collision'):host.apply()
            self.assertEqual(host.commands,[]);self.assertTrue(a.rollback(record)['record_retired']);self.assertFalse((host.base/'active-record.json').exists());self.assertTrue(host.apply().is_dir())
    def test_partial_unit_removal_retains_lease_and_retries_only_same_record(self):
        with SyntheticHost()as host:
            record=host.apply();unlink=os.unlink;failed=[]
            def stop(path,*args,**kw):
                if Path(path)==host.units/a.UNITS[1]and not failed:failed.append(True);raise OSError('fixed')
                return unlink(path,*args,**kw)
            with patch.object(os,'unlink',side_effect=stop):
                with self.assertRaises(OSError):a.rollback(record)
            self.assertFalse((host.units/a.UNITS[0]).exists());self.assertTrue((host.units/a.UNITS[1]).exists());self.assertTrue((host.base/'active-record.json').exists());self.assertEqual(host.state(record)['phase'],'rollback_in_progress');self.assertTrue(a.rollback(record)['record_retired'])
    def test_terminal_write_or_lease_cleanup_uncertainty_never_allows_stale_replay(self):
        for fault in ['after_terminal_write','lease_unlink']:
            with self.subTest(fault=fault),SyntheticHost()as host:
                record=host.apply();save=a.save_state;unlink=os.unlink
                def late(p,state):
                    save(p,state)
                    if state['phase']=='rolled_back':raise OSError('fixed')
                def retained(path,*args,**kw):
                    if Path(path)==host.base/'active-record.json':raise OSError('fixed')
                    return unlink(path,*args,**kw)
                with patch.object(a,'save_state',side_effect=late)if fault=='after_terminal_write'else patch.object(os,'unlink',side_effect=retained):
                    with self.assertRaises(OSError):a.rollback(record)
                self.assertEqual(host.state(record)['phase'],'rolled_back');host.commands.clear()
                with self.assertRaises(ValueError):a.rollback(record)
                with self.assertRaisesRegex(ValueError,'active_record_collision'):host.apply()
                self.assertEqual(host.commands,[])
    def test_lock_contention_and_dry_run_never_create_lease_or_units(self):
        with SyntheticHost()as host:
            self.assertTrue(a.activate(a.APPROVED_COMMIT,False)['public_activation_requires_separate_command']);self.assertEqual(list(host.base.iterdir()),[]);self.assertEqual(list(host.units.iterdir()),[]);host.commands.clear()
            with a.operation_lock():
                with self.assertRaises(BlockingIOError):host.apply()
            self.assertEqual(host.commands,[]);self.assertFalse((host.base/'active-record.json').exists());self.assertEqual(list(host.units.iterdir()),[])
    def test_failed_unit_install_rolls_back_only_its_recorded_first_unit(self):
        with SyntheticHost()as host:
            create=a.exclusive
            def fail(path,*args,**kw):
                if Path(path)==host.units/a.UNITS[1]:raise OSError('fixed')
                return create(path,*args,**kw)
            with patch.object(a,'exclusive',side_effect=fail):result=a.activate(a.APPROVED_COMMIT,True,'192.0.2.1')
            self.assertFalse(result['pass']);record=Path(result['record']);self.assertEqual(host.state(record)['installed_units'],[a.UNITS[0]]);self.assertTrue(a.rollback(record)['record_retired']);self.assertEqual(list(host.units.iterdir()),[])

if __name__=='__main__':unittest.main()
