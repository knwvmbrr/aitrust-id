"""Finite web format/ownership controls. Injected AUTH is explicitly not crypto."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zlib

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools import web_checker_artifact as w


def fixture(root):
    root.mkdir(mode=0o700)
    bodies={name:b'// privately authored fixture\n' for name in w.BUILD_INPUTS}
    bodies['LICENSE']=(ROOT/'LICENSE').read_bytes()
    for name,raw in bodies.items():
        p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
    sources={name:{'bytes':len(raw),'sha256':w.sha(raw),'git_blob_oid':w.git_oid(raw),'text_source':True,'notices':[]}for name,raw in bodies.items()}
    source={name:{'bytes':len(raw),'git_blob_oid':w.git_oid(raw),'mode':'100644'}for name,raw in bodies.items()}
    module={'id':'file:LICENSE','kind':'project','provider':None,'source_path':'LICENSE','source':sources['LICENSE'],'source_notices':[],'transformed':None}
    chunk=b'/* private fixture only; not a real site build */\n'
    observation={'profile':w.BUILD_PROFILE,'source_commit':'a'*40,'source_tree_oid':'b'*40,'sources':sources,
      'modules':{'file:LICENSE':module},'outputs':{'assets/fixture.js':{'kind':'chunk','bytes':len(chunk),'sha256':w.sha(chunk),
        'modules':[{'id':'file:LICENSE','rendered_length':0}],'imports':[],'dynamic_imports':[]}},
      'toolchain':{'vite':'8.3.4','rolldown':'1.2.13'},'claims':{'permission_issued':False,'release_authorized':False,'compiled_equivalence_proved':False}}
    catalog={'outputs':{},'runtime':{},'runtime_inputs':{},'selected_inputs':{},'npm':{},'providers':{},'grants':{'LICENSE':bodies['LICENSE']},'lock':{'packages':{}}}
    return observation,source,catalog,chunk


def archive(fd,members,build=None):
    manifest={'profile':w.PROFILE,'build':{}if build is None else build,'files':{n:w.row(b)for n,b in members.items()},'claims':w.FALSE_CLAIMS.copy()}
    payload={w.META:w.encoded(manifest)+b'\n',**{'payload/'+n:b for n,b in members.items()}}
    rows={n:w.row(b)|{'crc32':zlib.crc32(b)}for n,b in payload.items()}
    w.canonical_archive(fd,rows,lambda n:w._byte_chunks(payload[n]),w.Ledger())
    return manifest


class WebArtifactTests(unittest.TestCase):
    def test_actual_license_canonical_roundtrip_and_payload_forgery(self):
        raw=(ROOT/'LICENSE').read_bytes()
        with tempfile.NamedTemporaryFile()as f:
            manifest=archive(f.fileno(),{'LICENSE':raw})
            actual,rows=w.inspect_archive(f.fileno(),w.Ledger());self.assertEqual(actual,manifest)
            os.pwrite(f.fileno(),b'X',rows['payload/LICENSE']['offset'])
            with self.assertRaises(w.WebUnavailable):w.inspect_archive(f.fileno(),w.Ledger())

    def test_zip_trailing_and_noncanonical_header_refuse(self):
        for kind in ('trailing','header'):
            with self.subTest(kind=kind),tempfile.NamedTemporaryFile()as f:
                archive(f.fileno(),{'file.txt':b'owned'})
                if kind=='trailing':os.lseek(f.fileno(),0,os.SEEK_END);os.write(f.fileno(),b'X')
                else:os.pwrite(f.fileno(),b'\x01',6)
                with self.assertRaises(w.WebUnavailable):w.inspect_archive(f.fileno(),w.Ledger())

    def test_manifest_numeric_alias_refused(self):
        with tempfile.NamedTemporaryFile()as f:
            m={'profile':w.PROFILE,'build':{},'files':{'a':{'bytes':True,'sha256':w.sha(b'x'),'mode':420}},'claims':w.FALSE_CLAIMS.copy()}
            raw=w.encoded(m)+b'\n';values={w.META:raw,'payload/a':b'x'}
            rows={n:w.row(b)|{'crc32':zlib.crc32(b)}for n,b in values.items()}
            w.canonical_archive(f.fileno(),rows,lambda n:w._byte_chunks(values[n]),w.Ledger())
            with self.assertRaises(w.WebUnavailable):w.inspect_archive(f.fileno(),w.Ledger())

    def test_path_collision_and_escape_refuse(self):
        for names in (['a','a/b'],['A/b','a'],['A','a'],['../a'],['a/.git/x'],['a/.env']):
            with self.subTest(names=names),self.assertRaises(w.WebUnavailable):w.collision_free(names)
        w.collision_free(['a/b','c'])

    def test_json_duplicate_depth_token_and_nodes_refuse(self):
        for raw in (b'{"x":1,"x":2}',b'['*33+b'0'+b']'*33,b'1'*33,b'[NaN]'):
            with self.subTest(raw=raw[:20]),self.assertRaises((w.WebUnavailable,ValueError)):w.parse(raw,w.Ledger())
        ledger=w.Ledger();ledger.nodes=99999
        with self.assertRaises(w.WebUnavailable):w.parse(b'[1,2]',ledger)

    def test_opaque_virtual_ids_and_unknown_provider_refuse(self):
        with tempfile.TemporaryDirectory()as d:
            root=Path(d).resolve()/'source';o,s,c,_=fixture(root)
            v={'id':'virtual:vite-modulepreload','kind':'virtual','provider':'vite','source_path':None,'source':None,'source_notices':[],'transformed':None}
            o['modules'][v['id']]=v
            with w.FileTree(root,w.Ledger())as tree:w.validate_observation(o,'a'*40,s,'b'*40,c,tree,tree.ledger)
            v['provider']='unreviewed'
            with w.FileTree(root,w.Ledger())as tree,self.assertRaises(w.WebUnavailable):w.validate_observation(o,'a'*40,s,'b'*40,c,tree,tree.ledger)
            with self.assertRaises(w.WebUnavailable):w.path_name('\0vite/preload-helper.js')

    def test_source_git_oid_and_unknown_module_refuse(self):
        with tempfile.TemporaryDirectory()as d:
            root=Path(d).resolve()/'source';o,s,c,_=fixture(root)
            with w.FileTree(root,w.Ledger())as tree:w.validate_observation(o,'a'*40,s,'b'*40,c,tree,tree.ledger)
            for kind in ('oid','unknown','numeric'):
                bad=copy.deepcopy(o)
                if kind=='oid':bad['sources']['LICENSE']['git_blob_oid']='0'*40
                elif kind=='unknown':bad['modules']['file:LICENSE']['source_path']='site/unknown.js'
                else:bad['outputs']['assets/fixture.js']['modules'][0]['rendered_length']=False
                with self.subTest(kind=kind),w.FileTree(root,w.Ledger())as tree,self.assertRaises(w.WebUnavailable):w.validate_observation(bad,'a'*40,s,'b'*40,c,tree,tree.ledger)

    def test_npm_dependency_nested_escape_refuse(self):
        with tempfile.TemporaryDirectory()as d:
            root=Path(d).resolve()/'source';o,s,c,_=fixture(root)
            name='site/node_modules/react/node_modules/unknown/index.js'
            o['sources'][name]={'bytes':1,'sha256':w.sha(b'x'),'git_blob_oid':w.git_oid(b'x'),'text_source':True,'notices':[]}
            c['npm']['node_modules/react']={};c['lock']['packages']['node_modules/react']={}
            with w.FileTree(root,w.Ledger())as tree,self.assertRaises(w.WebUnavailable):w.validate_observation(o,'a'*40,s,'b'*40,c,tree,tree.ledger)

    def test_module_notice_forgery_refuse(self):
        with tempfile.TemporaryDirectory()as d:
            root=Path(d).resolve()/'source';o,s,c,_=fixture(root)
            item={'offset':0,'bytes':1,'sha256':w.sha(b'x'),'text':'x'}
            o['sources']['LICENSE']['notices']=[item];o['modules']['file:LICENSE']['source_notices']=[item]
            with w.FileTree(root,w.Ledger())as tree,self.assertRaises(w.WebUnavailable):w.validate_observation(o,'a'*40,s,'b'*40,c,tree,tree.ledger)

    def test_complete_private_fixture_prepare_inspect(self):
        with tempfile.TemporaryDirectory()as d:
            base=Path(d).resolve();root=base/'source';o,s,c,chunk=fixture(root);dist=base/'dist';dist.mkdir()
            (dist/'assets').mkdir();(dist/'assets/fixture.js').write_bytes(chunk)
            (dist/w.OBSERVATION).write_bytes(w.encoded(o)+b'\n')
            with patch.object(w,'source_catalog',return_value=c),patch.object(w,'committed_source',return_value=(s,'b'*40)),patch.object(w,'bind_catalog_source'):
                result=w.prepare(dist,base/'prepared','a'*40,root)
                checked=w.inspect(base/'prepared/checker.zip','a'*40,root)
            self.assertTrue(result['pass']);self.assertTrue(checked['format_and_source_verified'])
            self.assertFalse(result['claims']['release_authorized']);self.assertEqual((base/'prepared/checker.zip').stat().st_mode&0o777,0o600)
            self.assertEqual(checked['files'],4)

    def test_legacy_dist_missing_census_refuses_before_output(self):
        with tempfile.TemporaryDirectory()as d:
            base=Path(d).resolve();root=base/'source';o,s,c,chunk=fixture(root);dist=base/'dist';dist.mkdir();(dist/'index.html').write_text('fixture')
            with patch.object(w,'source_catalog',return_value=c),patch.object(w,'committed_source',return_value=(s,'b'*40)),patch.object(w,'bind_catalog_source'),self.assertRaises(w.WebUnavailable):w.prepare(dist,base/'out','a'*40,root)
            self.assertFalse((base/'out').exists())

    def test_directory_scan_stops_at_bound_and_symlink_refuses(self):
        with tempfile.TemporaryDirectory()as d:
            root=Path(d).resolve();(root/'a').write_bytes(b'a');(root/'b').write_bytes(b'b')
            with w.FileTree(root,w.Ledger())as tree,self.assertRaises(w.WebUnavailable):tree.inventory(max_files=1)
            (root/'b').unlink();(root/'b').symlink_to(root/'a')
            with w.FileTree(root,w.Ledger())as tree,self.assertRaises(w.WebUnavailable):tree.inventory()

    def test_expected_size_refuses_before_file_body_read(self):
        with tempfile.TemporaryDirectory()as d:
            root=Path(d).resolve();(root/'a').write_bytes(b'x'*100)
            with w.FileTree(root,w.Ledger())as tree,patch.object(w.os,'read',side_effect=AssertionError('must not read')),self.assertRaises(w.WebUnavailable):tree.read('a',100,expected={'bytes':1,'sha256':w.sha(b'x')})

    def test_stage_preexisting_and_post_real_mkdir_fault(self):
        with tempfile.TemporaryDirectory()as d:
            base=Path(d).resolve();(base/'exists').mkdir(mode=0o700)
            with self.assertRaises(w.WebUnavailable):
                with w.PrivateStage(base/'exists',w.Ledger()):pass
            mkdir=os.mkdir
            def fault(*a,**k):mkdir(*a,**k);raise OSError('after creation')
            with patch.object(w.os,'mkdir',side_effect=fault),self.assertRaises(w.WebOutputUncertain):
                with w.PrivateStage(base/'created',w.Ledger()):pass
            self.assertTrue((base/'created').is_dir())

    def test_stage_cancellation_close_uncertainty_and_no_delete(self):
        with tempfile.TemporaryDirectory()as d:
            base=Path(d).resolve()
            with self.assertRaises(w.WebOutputUncertain):
                with w.operation(w.Ledger()) as unused:
                    pass
                    # Separate ledger's stage still has its own typed scope.
                    with w.PrivateStage(base/'out',w.Ledger())as stage:
                        stage.save('owned',b'kept');raise KeyboardInterrupt()
            self.assertEqual((base/'out/owned').read_bytes(),b'kept')

    def test_stage_late_git_boundary_and_normal_close(self):
        with tempfile.TemporaryDirectory()as d:
            base=Path(d).resolve();ledger=w.Ledger()
            with self.assertRaises(w.WebOutputUncertain):
                with w.PrivateStage(base/'out',ledger)as stage:
                    stage.save('owned',b'kept');(base/'.git').mkdir()
            self.assertEqual(ledger.fds,0);self.assertEqual((base/'out/owned').read_bytes(),b'kept')

    def test_auth_before_manifest_or_materialization(self):
        with tempfile.TemporaryDirectory()as d:
            base=Path(d).resolve();root=base/'source';o,s,c,_=fixture(root)
            files={name:base/name for name in ('artifact','packet','spdx','bundle','roots')}
            for name,p in files.items():p.write_bytes(b'opaque')
            files['packet'].write_bytes(w.encoded({'route':'web-checker','source_commit':'a'*40,'artifact':{'bytes':6,'sha256':w.sha(b'opaque')}}))
            files['spdx'].write_bytes(b'{}')
            def refuse(*args):
                self.assertLessEqual(args[-1].fds+80,w.MAX_FDS);raise w.WebUnavailable()
            with patch.object(w,'source_catalog',return_value=c),patch.object(w,'committed_source',return_value=(s,'b'*40)),patch.object(w,'bind_catalog_source'),patch.object(w,'SOURCE_PINS',{}),patch.object(w,'_fixed_authorize',side_effect=refuse)as auth,patch.object(w,'inspect_archive',side_effect=AssertionError('before AUTH')),self.assertRaises(w.WebOutputUncertain):
                w.verify_managed(*[files[k]for k in ('artifact','packet','spdx','bundle','roots')],base/'out','a'*40,root)
            self.assertEqual(auth.call_count,1);self.assertFalse((base/'out/site').exists());self.assertEqual((base/'out/artifact.bin').read_bytes(),b'opaque')
            self.assertNotEqual(Path(auth.call_args.args[1]),files['artifact'])

    def test_injected_auth_full_materialization_and_bound_graph_refusal(self):
        with tempfile.TemporaryDirectory()as d:
            base=Path(d).resolve();root=base/'source';o,s,c,chunk=fixture(root);dist=base/'dist';dist.mkdir()
            (dist/'assets').mkdir();(dist/'assets/fixture.js').write_bytes(chunk);(dist/w.OBSERVATION).write_bytes(w.encoded(o)+b'\n')
            patches=[patch.object(w,'source_catalog',return_value=c),patch.object(w,'committed_source',return_value=(s,'b'*40)),patch.object(w,'bind_catalog_source')]
            from contextlib import ExitStack
            with ExitStack()as stack:
                for value in patches:stack.enter_context(value)
                result=w.prepare(dist,base/'packaged','a'*40,root)
                artifact=base/'packaged/checker.zip';bound=json.loads((base/'packaged/build-binding.json').read_bytes())
                packet=base/'packet';spdx=base/'spdx';bundle=base/'bundle';roots=base/'roots'
                for path in (spdx,bundle,roots):path.write_bytes(b'{}')
                record={'route':'web-checker','source_commit':'a'*40,'artifact':result['artifact'],
                  'graph':{'nodes':[{'key':'web:build-observation','details':{'build':bound}}]}}
                packet.write_bytes(w.encoded(record))
                stack.enter_context(patch.object(w,'SOURCE_PINS',{}))
                stack.enter_context(patch.object(w,'_fixed_authorize',return_value={'state':'AUTHORIZED','attestation_verified':True,'release_authorized':True}))
                installed=w.verify_managed(artifact,packet,spdx,bundle,roots,base/'managed','a'*40,root)
                self.assertEqual(installed['state'],'MATERIALIZED');self.assertFalse(installed['execution_started'])
                self.assertEqual((base/'managed/site/assets/fixture.js').read_bytes(),chunk)
                self.assertEqual((base/'managed/site/assets/fixture.js').stat().st_mode&0o777,0o600)
                record['graph']['nodes'][0]['details']['build']['source_tree_oid']='0'*40;packet.write_bytes(w.encoded(record))
                with self.assertRaises(w.WebOutputUncertain):w.verify_managed(artifact,packet,spdx,bundle,roots,base/'forged','a'*40,root)
                self.assertFalse((base/'forged/site').exists())

    def test_original_alarm_unwinds_real_owned_child(self):
        from tools import artifact_process
        import time
        children=[];popen=artifact_process.subprocess.Popen
        def observed(*args,**kwargs):
            child=popen(*args,**kwargs);children.append(child);return child
        ledger=w.Ledger();ledger.deadline=time.monotonic()+.05
        with patch.object(artifact_process.subprocess,'Popen',side_effect=observed),self.assertRaises(artifact_process.ArtifactProcessError):
            with w.original_deadline(ledger):artifact_process.run_worker([sys.executable,'-I','-S','-B','-c','import time;time.sleep(5)'],input=b'',timeout=5,output_limit=100)
        self.assertEqual(len(children),1);self.assertIsNotNone(children[0].returncode)
        self.assertTrue(children[0].stdin.closed and children[0].stdout.closed)
        with self.assertRaises(ChildProcessError):os.waitpid(children[0].pid,os.WNOHANG)

    def test_many_deep_distinct_parents_refuse_before_output_creation(self):
        with tempfile.TemporaryDirectory()as d:
            base=Path(d).resolve();root=base/'source';o,s,c,_=fixture(root);paths=[]
            for number in range(5):
                parent=base/str(number)/'a'/'b'/'c'/'d';parent.mkdir(parents=True);path=parent/'input';path.write_bytes(b'opaque');paths.append(path)
            with patch.object(w,'source_catalog',return_value=c),patch.object(w,'committed_source',return_value=(s,'b'*40)),patch.object(w,'bind_catalog_source'),patch.object(w,'SOURCE_PINS',{}),patch.object(w,'_fixed_authorize',side_effect=AssertionError('must refuse earlier')),self.assertRaises(w.WebUnavailable):
                w.verify_managed(*paths,base/'out','a'*40,root)
            self.assertFalse((base/'out').exists())

    def test_auth_reservation_and_original_timer_restore(self):
        ledger=w.Ledger(managed=True);ledger.reserve_auth(64_000_000);self.assertEqual(ledger.legacy_bytes,722_000_000)
        with self.assertRaises(w.WebUnavailable):ledger.charge(500_000_000)
        before=signal.getsignal(signal.SIGALRM)
        with w.original_deadline(w.Ledger()):self.assertGreater(signal.getitimer(signal.ITIMER_REAL)[0],0)
        self.assertEqual(signal.getitimer(signal.ITIMER_REAL),(0.0,0.0));self.assertEqual(signal.getsignal(signal.SIGALRM),before)

    def test_actual_deadline_setup_and_teardown_faults_restore_process_state(self):
        old=signal.getsignal(signal.SIGALRM);real=signal.setitimer
        self.assertEqual(signal.getitimer(signal.ITIMER_REAL),(0.0,0.0))
        for mode in ('before_arm','after_real_arm','after_real_disarm'):
            calls=[]
            def fail(which,value,*args):
                calls.append(value)
                if mode=='before_arm' and len(calls)==1:raise OSError('injected before arm')
                result=real(which,value,*args)
                if (mode=='after_real_arm' and len(calls)==1)or(mode=='after_real_disarm' and value==0):raise OSError('injected after real timer operation')
                return result
            try:
                with self.subTest(mode=mode),patch.object(w.signal,'setitimer',side_effect=fail),self.assertRaises(OSError):
                    with w.original_deadline(w.Ledger()):pass
                self.assertIs(signal.getsignal(signal.SIGALRM),old)
                self.assertEqual(signal.getitimer(signal.ITIMER_REAL),(0.0,0.0))
                self.assertEqual(calls[-1],0)
            finally:
                real(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,old)

    def test_fast_verifier_does_not_extend_finite_deadline(self):
        ledger=w.Ledger(managed=True)
        with patch.object(w.time,'monotonic',return_value=ledger.started+61),self.assertRaises(w.WebUnavailable):ledger.tick()
        ledger.crypto_seconds=50
        with patch.object(w.time,'monotonic',return_value=ledger.started+109):ledger.tick()
        with patch.object(w.time,'monotonic',return_value=ledger.started+110),self.assertRaises(w.WebUnavailable):ledger.tick()

    def test_actual_fixed_runner_boundary_remaining_and_duration(self):
        from types import SimpleNamespace
        now=[1.0];calls=[]
        def run(argv,**kwargs):
            calls.append((argv,kwargs));now[0]=41.0;return subprocess.CompletedProcess(argv,0,b'[]',b'')
        common=SimpleNamespace(run_attestation=run);ledger=w.Ledger(managed=True);ledger.started=0.;ledger.deadline=115.
        with patch.object(w.time,'monotonic',side_effect=lambda:now[0]):
            result=w._run_real_verifier(common,['fixed'],ledger,60,16_000_000)
        self.assertEqual(result.stdout,b'[]');self.assertEqual(ledger.crypto_seconds,40.0);self.assertEqual(len(calls),1)
        ledger=w.Ledger(managed=True);ledger.started=0.;ledger.deadline=115.;now[0]=51.;calls.clear()
        with patch.object(w.time,'monotonic',side_effect=lambda:now[0]),self.assertRaises(w.WebUnavailable):w._run_real_verifier(common,['fixed'],ledger,60,16_000_000)
        self.assertFalse(calls);self.assertFalse(ledger.verifier_invoked)

    def test_cli_isolated_help_and_no_echo_refusal(self):
        command=[sys.executable,'-I','-S','-B',str(ROOT/'scripts/web-checker-artifact.py')]
        help_result=subprocess.run(command+['--help'],cwd='/',capture_output=True,timeout=5)
        self.assertEqual(help_result.returncode,0)
        refused=subprocess.run(command+['inspect','--source-commit','private-canary'],cwd='/',capture_output=True,timeout=5)
        self.assertEqual(refused.returncode,2);self.assertNotIn(b'private-canary',refused.stdout+refused.stderr)


if __name__=='__main__':unittest.main()
