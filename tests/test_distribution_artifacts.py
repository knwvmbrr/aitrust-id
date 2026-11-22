"""Real package/graph controls; injected cryptographic results are not signing proof."""
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from tools import distribution_artifacts as a
from tools import artifact_evidence_io as io
from tools.ps_source_distribution import build

ROOT=Path(__file__).resolve().parents[1]
COMMIT='40d85dfabcd6a3d97b84977992d0523b0995c0d9'

class ArtifactWorkflow(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='aitrust-artifact-test-');self.base=Path(self.temp.name).resolve();self.base.chmod(0o700)
        self.artifact=self.base/'ps.zip';self.artifact.write_bytes(build(ROOT));self.artifact.chmod(0o600)
    def tearDown(self):self.temp.cleanup()
    def private(self,name,raw):
        p=self.base/name;p.write_bytes(raw);p.chmod(0o600);return p
    def record(self):return a.prepare('ps-source',self.artifact,COMMIT)
    def cli(self,*args):
        return subprocess.run([sys.executable,'-I','-S','-B',str(ROOT/'scripts/distribution-artifact.py'),*map(str,args)],capture_output=True,timeout=20)
    def test_all_fourteen_real_adapters_and_package_identities(self):
        actual={}
        for route in sorted(a.ROUTES):
            value=a.graph(route);actual[route]=len(value['nodes']);self.assertGreater(actual[route],1)
            self.assertFalse(value['license_clearance']);self.assertFalse(value['complete_embedded_dependency_coverage'])
            self.assertEqual(len({n['key']for n in value['nodes']}),actual[route])
            self.assertIn('tools/distribution_artifacts.py',value['source_sha256'])
        self.assertEqual(actual['ps-source'],9);self.assertEqual(actual['node-build-tools'],205)
        self.assertGreater(actual['source-snapshot'],6000);self.assertEqual(actual['gateway-linux-amd64'],122)
        self.assertEqual(actual['evaluator-linux-amd64'],125);self.assertEqual(actual['anonymizer-linux-amd64'],180)
        self.assertEqual(len(actual),14)
    def test_git_blob_identity_is_not_misrepresented_as_a_file_checksum(self):
        g=a.graph('source-snapshot');node=g['nodes'][0]
        self.assertEqual(node['checksums'],[])
        self.assertRegex(node['details']['git_blob_oid'],r'^[a-f0-9]{40}$')
        document=a.spdx('source-snapshot',{'sha256':'0'*64},g,'2026-11-21T00:00:00Z')
        package=next(p for p in document['packages']if p['name']==node['name'])
        self.assertNotIn('checksums',package)
        self.assertIn(node['details']['git_blob_oid'],package['sourceInfo'])
        self.assertIn('not a plain file checksum',package['sourceInfo'])
    def test_16385_git_rows_refuse_before_constructing_nodes_or_reading_blobs(self):
        rows=b'100644 blob '+b'a'*40+b'\tfixed.txt\0'
        responses=[subprocess.CompletedProcess([],0,b'a'*40+b'\n'),subprocess.CompletedProcess([],0,rows*16385)]
        with io.Capture()as captured,mock.patch.object(a,'run_worker',side_effect=responses)as calls:
            graph=a.Graph('source-snapshot',ROOT,captured)
            with self.assertRaises(ValueError):graph.committed_tree()
            self.assertEqual(graph.nodes,{})
            self.assertEqual(calls.call_count,2)
        import importlib.util
        spec=importlib.util.spec_from_file_location('owned_source_capacity',ROOT/'scripts/source_snapshot_v2.py')
        source=importlib.util.module_from_spec(spec)
        sys.path.insert(0,str(ROOT/'scripts'))
        try:spec.loader.exec_module(source)
        finally:sys.path.pop(0)
        listing=(b'100644 blob '+b'a'*40+b' 1\tfixed.txt\0')*16385
        with mock.patch.object(source,'git',side_effect=[b'a'*40+b'\n',listing])as calls:
            with self.assertRaisesRegex(ValueError,'Committed source limit'):source.build(ROOT,'a'*40)
            self.assertEqual(calls.call_count,2)
        self.assertEqual(source.MAX_FILES,16384);self.assertEqual(a.MAX_NODES,16384)
    def test_spdx_local_ids_unique_sorted_key_mapping_and_deterministic(self):
        g=a.graph('ps-source');artifact={'sha256':'0'*64};created='2026-11-21T00:00:00Z'
        first=a.spdx('ps-source',artifact,g,created);second=a.spdx('ps-source',artifact,copy.deepcopy(g),created)
        self.assertEqual(first,second)
        expected={n['name']:'SPDXRef-Component-'+str(i).zfill(5)for i,n in enumerate(sorted(g['nodes'],key=lambda n:n['key']),1)}
        actual={p['name']:p['SPDXID']for p in first['packages'][1:]}
        self.assertEqual(actual,expected);self.assertEqual(len(set(actual.values())),len(g['nodes']))
        relations=[row for row in first['relationships']if row['relationshipType']=='OTHER']
        self.assertEqual({r['relatedSpdxElement']for r in relations},set(actual.values()))
        self.assertTrue(all('not a containment claim'in r['comment']for r in relations))
        duplicate=copy.deepcopy(g);duplicate['nodes'].append(copy.deepcopy(g['nodes'][0]))
        with self.assertRaises(ValueError):a.spdx('ps-source',artifact,duplicate,created)
    def test_forged_full_node_key_or_exact_relationship_cannot_rebind_local_ids(self):
        r=self.record()
        for key in ('node_key','relationship'):
            b=copy.deepcopy(r)
            if key=='node_key':b['graph']['nodes'][0]['key']+='-FORGED'
            else:b['graph']['relationships'].append({'from':b['graph']['nodes'][0]['key'],'to':b['graph']['nodes'][1]['key'],'type':'DEPENDS_ON'})
            b['graph_sha256']=a.sha(a.encoded(b['graph']))
            b['spdx']=a.spdx('ps-source',b['artifact'],b['graph'],b['created'])
            b['spdx_sha256']=a.sha(a.encoded(b['spdx'])+b'\n')
            with self.assertRaises(ValueError):a.verify_packet(b,self.artifact,'ps-source',COMMIT)
    def test_large_bounded_bundle_and_complete_verification_result_projection(self):
        r,s,b,t=self.verification_inputs();b.write_bytes(b'x'*5_000_001)
        good=self.verifier(r)
        def selected(argv,**kwargs):
            self.assertEqual(argv[-2:],['--jq','map({verificationResult: .verificationResult})'])
            stage=Path(argv[argv.index('--bundle')+1]);self.assertEqual(stage.read_bytes(),b.read_bytes())
            return good(argv,**kwargs)
        value=a.verify_attestation(r,self.artifact,s,b,t,'ps-source',COMMIT,runner=selected)
        self.assertTrue(value['attestation_verified']);self.assertFalse(value['release_authorized'])
        b.write_bytes(b'x'*16_000_001)
        with self.assertRaises(ValueError):a.verify_attestation(r,self.artifact,s,b,t,'ps-source',COMMIT,runner=lambda *args,**kw:self.fail('oversize must refuse before verifier'))
        b.write_bytes(b'{}');t.write_bytes(b'x'*5_000_001)
        with self.assertRaises(ValueError):a.verify_attestation(r,self.artifact,s,b,t,'ps-source',COMMIT,runner=lambda *args,**kw:self.fail('root cap unchanged'))
    def test_actual_ps_artifact_sbom_and_exact_packet_replay(self):
        r=self.record();a.save_packet(r,self.base/'packet.json')
        self.assertEqual(a.verify_packet(r,self.artifact,'ps-source',COMMIT),r)
        self.assertEqual(r['artifact']['sha256'],hashlib.sha256(self.artifact.read_bytes()).hexdigest())
        self.assertEqual(r['spdx']['packages'][0]['checksums'][0]['checksumValue'],r['artifact']['sha256'])
        self.assertEqual(r['spdx_sha256'],hashlib.sha256(io.encoded(r['spdx'])+b'\n').hexdigest())
        self.assertEqual(stat.S_IMODE((self.base/'packet.json').stat().st_mode),0o600)
        self.assertTrue(r['policy']['release_allowed']);self.assertFalse(r['release_authorized'])
        self.assertEqual(r['spdx']['dataLicense'],'CC0-1.0')
        self.assertIn(r['graph_sha256'],r['spdx']['comment'])
    def test_wrong_artifact_changed_graph_predicate_boolean_route_and_source_refuse(self):
        r=self.record()
        for change in ('artifact','graph','spdx','bool','route','source'):
            b=copy.deepcopy(r)
            if change=='artifact':b['artifact']['sha256']='0'*64
            if change=='graph':b['graph']['nodes']=[]
            if change=='spdx':b['spdx']['packages'][0]['licenseConcluded']='MIT'
            if change=='bool':b['release_authorized']=0
            if change=='route':b['route']='ios-app'
            if change=='source':b['source_commit']='0'*40
            with self.assertRaises(ValueError):a.verify_packet(b,self.artifact,'ps-source',COMMIT)
        self.artifact.write_bytes(b'PRIVATE_ARTIFACT_CANARY')
        with self.assertRaises(ValueError):a.verify_packet(r,self.artifact,'ps-source',COMMIT)
    def test_source_and_unknown_approval_never_admit_nonps(self):
        artifact=self.private('candidate.bin',b'explicit unapproved candidate bytes')
        r=a.prepare('android-app',artifact,COMMIT);self.assertFalse(r['policy']['release_allowed'])
        # No supplied authentication object can bypass policy or invoke gh here.
        with self.assertRaises(ValueError):a.authorize_release(r,artifact,None,None,None,'android-app',COMMIT,runner=lambda *x,**y:self.fail('must not invoke verifier'))
        with self.assertRaises(ValueError):a.graph('PRIVATE_UNKNOWN_CANARY')
        self.assertTrue(self.record()['policy']['release_allowed'])
    def test_symlinks_hardlinks_fifo_size_and_existing_outputs_refuse(self):
        link=self.base/'link';link.symlink_to(self.artifact)
        with self.assertRaises(ValueError):a.prepare('ps-source',link,COMMIT)
        hard=self.base/'hard';os.link(self.artifact,hard)
        with self.assertRaises(ValueError):a.prepare('ps-source',hard,COMMIT)
        hard.unlink();fifo=self.base/'fifo';os.mkfifo(fifo)
        with self.assertRaises(ValueError):a.prepare('ps-source',fifo,COMMIT)
        with io.Capture()as c:
            with self.assertRaises(ValueError):c.artifact(self.artifact,limit=1)
        out=self.private('existing.json',b'PRESERVE')
        with self.assertRaises(ValueError):a.save_packet(self.record(),out)
        self.assertEqual(out.read_bytes(),b'PRESERVE')
    def test_actual_cli_prepare_inspect_spdx_no_input_echo_and_duplicate_refusal(self):
        packet=self.base/'packet.json';sbom=self.base/'sbom.json'
        common=['--route','ps-source','--artifact',self.artifact,'--commit',COMMIT]
        for args in [['prepare',*common,'--output',packet],['inspect',*common,'--packet',packet],['spdx',*common,'--packet',packet,'--output',sbom]]:
            r=self.cli(*args);self.assertEqual(r.returncode,0,r.stderr);self.assertNotIn(str(self.base).encode(),r.stdout+r.stderr)
        self.assertEqual(sbom.read_bytes(),io.encoded(json.loads(packet.read_bytes())['spdx'])+b'\n')
        bad=self.private('duplicate.json',b'{"route":"ps-source","route":"ps-source"}')
        r=self.cli('inspect',*common,'--packet',bad);self.assertEqual(r.returncode,2);self.assertNotIn(str(self.base).encode(),r.stdout+r.stderr)
        r=self.cli('graph','--route','PRIVATE_UNKNOWN_CANARY');self.assertEqual(r.returncode,2);self.assertNotIn(b'PRIVATE_UNKNOWN_CANARY',r.stdout+r.stderr)
    def verification_inputs(self):
        r=self.record();sbom=self.private('sbom.json',io.encoded(r['spdx'])+b'\n');bundle=self.private('bundle.json',b'{}');trust=self.private('trust.jsonl',b'{}')
        return r,sbom,bundle,trust
    def verifier(self,r,mutation=None):
        def run(argv,**options):
            self.assertEqual(options,{'timeout':60,'output_limit':16000000});self.assertIn(a.IDENTITY,argv)
            self.assertIn(COMMIT,argv);self.assertIn('--deny-self-hosted-runners',argv)
            statement={'predicateType':a.SPDX_TYPE,'predicate':copy.deepcopy(r['spdx']),'subject':[{'digest':{'sha256':r['artifact']['sha256']}}]}
            if mutation:mutation(statement)
            return subprocess.CompletedProcess(argv,0,io.encoded([{'verificationResult':{'verifiedTimestamps':[{'verified':True}],'statement':statement}}]),b'')
        return run
    def test_verifier_subject_predicate_identity_and_no_clearance_promotion(self):
        r,s,b,t=self.verification_inputs()
        v=a.verify_attestation(r,self.artifact,s,b,t,'ps-source',COMMIT,runner=self.verifier(r));self.assertTrue(v['attestation_verified']);self.assertFalse(v['release_authorized'])
        v=a.authorize_release(r,self.artifact,s,b,t,'ps-source',COMMIT,runner=self.verifier(r));self.assertTrue(v['release_authorized']);self.assertFalse(v['license_clearance'])
        for mutation in [lambda x:x['subject'][0]['digest'].update(sha256='0'*64),lambda x:x.update(predicateType='untrusted'),lambda x:x['predicate']['packages'][0].update(filesAnalyzed=0)]:
            with self.assertRaises(ValueError):a.verify_attestation(r,self.artifact,s,b,t,'ps-source',COMMIT,runner=self.verifier(r,mutation))
    def test_post_verifier_source_or_artifact_drift_refuses(self):
        r,s,b,t=self.verification_inputs();good=self.verifier(r)
        def drift(argv,**kwargs):
            value=good(argv,**kwargs);self.artifact.write_bytes(b'DRIFT');return value
        with self.assertRaises(ValueError):a.verify_attestation(r,self.artifact,s,b,t,'ps-source',COMMIT,runner=drift)
    def test_publication_fdopen_failure_and_postcommit_uncertainty(self):
        r=self.record();out=self.base/'new.json';fds=[];realopen=io.os.open
        def opened(*args,**kw):
            fd=realopen(*args,**kw)
            if str(args[0]).startswith('.artifact-evidence-'):fds.append(fd)
            return fd
        with mock.patch.object(io.os,'open',side_effect=opened),mock.patch.object(io.os,'fdopen',side_effect=OSError('PRIVATE_OPEN_CANARY')):
            with self.assertRaises(ValueError):a.save_packet(r,out)
        self.assertFalse(out.exists())
        for fd in fds:
            with self.assertRaises(OSError):os.fstat(fd)
        unlink=io.os.unlink
        def fault(name,*args,**kw):
            if str(name).startswith('.artifact-evidence-'):raise OSError('PRIVATE_UNLINK_CANARY')
            return unlink(name,*args,**kw)
        with mock.patch.object(io.os,'unlink',side_effect=fault):
            with self.assertRaises(io.OutputCommitUncertain):a.save_packet(r,out)
        self.assertEqual(json.loads(out.read_bytes()),r)
    def test_source_reader_replaced_parent_and_all_close_attempts(self):
        folder=self.base/'parent';folder.mkdir(mode=0o700);x=folder/'input';x.write_bytes(b'INPUT');x.chmod(0o600)
        with io.Capture()as c:
            c.read(x,100);folder.rename(self.base/'old');folder.mkdir(mode=0o700)
            with self.assertRaises(ValueError):c.check()
        c=io.Capture();c.read(self.artifact,1000000);owned=list(c.fds);realclose=io.os.close;seen=[]
        def close(fd):
            seen.append(fd);realclose(fd)
            if len(seen)==1:raise OSError('PRIVATE_CLOSE_CANARY')
        with mock.patch.object(io.os,'close',side_effect=close):
            with self.assertRaises(ValueError):c.close()
        self.assertEqual(sorted(seen),sorted(owned));self.assertEqual(len(seen),len(set(seen)))

    def test_source_drift_immediately_before_and_after_link_has_honest_outcome(self):
        r=self.record();out=self.base/'drift.json';fsync=io.os.fsync;changed=False
        def pre_drift(fd):
            nonlocal changed
            fsync(fd)
            if not changed and stat.S_ISREG(os.fstat(fd).st_mode):
                changed=True;self.artifact.write_bytes(b'CHANGED_BEFORE_PUBLICATION')
        with mock.patch.object(io.os,'fsync',side_effect=pre_drift):
            with self.assertRaises(ValueError):a.publish_bound(r,self.artifact,'ps-source',COMMIT,out)
        self.assertFalse(out.exists())
        self.artifact.write_bytes(build(ROOT));r=self.record();link=io.os.link
        def post_drift(*args,**kwargs):
            link(*args,**kwargs);self.artifact.write_bytes(b'CHANGED_AFTER_PUBLICATION')
        with mock.patch.object(io.os,'link',side_effect=post_drift):
            with self.assertRaises(io.OutputCommitUncertain):a.publish_bound(r,self.artifact,'ps-source',COMMIT,out)
        self.assertEqual(json.loads(out.read_bytes()),r)
    def test_actual_exec_capture_adapter_with_owned_fake_gh_is_not_signature_proof(self):
        r,s,b,t=self.verification_inputs()
        statement={'predicateType':a.SPDX_TYPE,'predicate':r['spdx'],'subject':[{'digest':{'sha256':r['artifact']['sha256']}}]}
        result=io.encoded([{'verificationResult':{'verifiedTimestamps':[{'verified':True}],'statement':statement}}])
        gh=self.base/'gh';gh.write_text('#!'+sys.executable+'\nimport os\nos.write(1,'+repr(result)+')\n');gh.chmod(0o700)
        with mock.patch.dict(os.environ,{'PATH':str(self.base)+os.pathsep+os.environ.get('PATH','')}):
            value=a.verify_attestation(r,self.artifact,s,b,t,'ps-source',COMMIT)
        self.assertTrue(value['attestation_verified']);self.assertFalse(value['release_authorized'])
        self.assertEqual(value['artifact_sha256'],hashlib.sha256(self.artifact.read_bytes()).hexdigest())
        # The real fixed Python exec/capture path runs above; crypto is a deliberately
        # injected owned executable here and cannot be reported as actual signing.
    def test_actual_exec_capture_file_budget_refuses_without_stdout_growth(self):
        gh=self.base/'gh';gh.write_text('#!'+sys.executable+'\nimport os\nfor i in range(300):os.write(1,b"x"*65536)\n');gh.chmod(0o700)
        folder=self.base/'capture';folder.mkdir(mode=0o700);artifact=folder/'artifact.bin';artifact.write_bytes(b'ARTIFACT')
        with mock.patch.dict(os.environ,{'PATH':str(self.base)+os.pathsep+os.environ.get('PATH','')}):
            result=a.run_attestation(['gh','attestation','verify',str(artifact)])
        self.assertNotEqual(result.returncode,0);self.assertEqual(result.stdout,b'')
        self.assertLessEqual((folder/'verification-result.json').stat().st_size,16000000)
    def test_actual_cli_publication_uncertainty_is_fixed_and_private(self):
        packet=self.base/'uncertain.json'
        code="""import importlib.util,sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from tools import artifact_evidence_io as io
spec=importlib.util.spec_from_file_location('owned_cli',Path(sys.argv[1])/'scripts/distribution-artifact.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
real=io.os.unlink
def fault(name,*args,**kwargs):
 if str(name).startswith('.artifact-evidence-'):raise OSError('PRIVATE_UNLINK_CANARY')
 return real(name,*args,**kwargs)
io.os.unlink=fault
sys.argv=['distribution-artifact.py',*sys.argv[2:]]
try:module.main()
except io.OutputCommitUncertain:
 print('{"state":"UNAVAILABLE","reason":"output_commit_uncertain","output_may_exist":true}');raise SystemExit(2)
"""
        result=subprocess.run([sys.executable,'-I','-S','-B','-c',code,str(ROOT),'prepare','--route','ps-source','--artifact',str(self.artifact),'--commit',COMMIT,'--output',str(packet)],capture_output=True,timeout=20)
        self.assertEqual(result.returncode,2);self.assertTrue(packet.exists());self.assertIn(b'output_may_exist',result.stdout)
        self.assertNotIn(b'PRIVATE_UNLINK_CANARY',result.stdout+result.stderr);self.assertNotIn(str(self.base).encode(),result.stdout+result.stderr)

    def test_post_verifier_changed_source_is_not_a_current_valid_packet(self):
        mirror=self.base/'source';mirror.mkdir(mode=0o700)
        inputs=a.graph('ps-source')['source_sha256']
        for path in inputs:
            destination=mirror/path;destination.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(ROOT/path,destination)
        r=a.prepare('ps-source',self.artifact,COMMIT,root=mirror)
        s=self.private('mirrored-sbom.json',io.encoded(r['spdx'])+b'\n');b=self.private('mirrored-bundle.json',b'{}');t=self.private('mirrored-trust.jsonl',b'{}')
        good=self.verifier(r)
        def changed(argv,**kwargs):
            result=good(argv,**kwargs);(mirror/'docs/ps-source-distribution.md').write_bytes(b'CHANGED_SOURCE');return result
        with self.assertRaises(ValueError):a.verify_attestation(r,self.artifact,s,b,t,'ps-source',COMMIT,root=mirror,runner=changed)

    def test_timeout_and_transport_exceptions_never_echo_private_command(self):
        r,s,b,t=self.verification_inputs()
        def failed(*_args,**_kwargs):raise subprocess.TimeoutExpired(['PRIVATE_COMMAND_CANARY'],60)
        with self.assertRaises(ValueError)as observed:a.verify_attestation(r,self.artifact,s,b,t,'ps-source',COMMIT,runner=failed)
        self.assertEqual(str(observed.exception),'Artifact evidence unavailable.')
        self.assertNotIn('PRIVATE_COMMAND_CANARY',str(observed.exception))

    def test_native_adapter_binds_every_retained_source_without_permission_promotion(self):
        manifest=ROOT/'sbom/c2pa-native/manifest.json'
        self.assertTrue(manifest.is_file(),'Reviewed C2PA dependency commit is required for this control.')
        m=json.loads(manifest.read_bytes());self.assertEqual(len(m['packages']),441)
        for route in ('c2pa-linux-x86_64','c2pa-macos-arm64'):
            g=a.graph(route);self.assertEqual(len(g['nodes']),451);self.assertEqual(len(g['relationships']),1131)
            self.assertFalse(g['complete_embedded_dependency_coverage']);self.assertFalse(g['license_clearance'])
            for row in m['sources']:
                self.assertEqual(g['source_sha256'][row['path']],row['sha256'])
                self.assertEqual(hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest(),row['sha256'])
            self.assertTrue(all(node['permission_decision']=='unreviewed'for node in g['nodes']))
            native=[node for node in g['nodes']if node['key'].startswith('c2pa-native:')]
            self.assertEqual(sum(node['details']['native_source_label_observed']for node in native),135)
            self.assertTrue(all(node['details']['compiled_closure_established']is False for node in native))

    def test_public_download_metadata_modes_work_without_public_output(self):
        r,s,b,t=self.verification_inputs();packet=self.private('downloaded.json',io.encoded(r)+b'\n')
        for path in (packet,s,b,t):path.chmod(0o644)
        value=a.verify_attestation(r,self.artifact,s,b,t,'ps-source',COMMIT,runner=self.verifier(r))
        self.assertTrue(value['attestation_verified']);self.assertFalse(value['release_authorized'])
        result=self.cli('inspect','--route','ps-source','--artifact',self.artifact,'--commit',COMMIT,'--packet',packet)
        self.assertEqual(result.returncode,0,result.stderr)
        output=self.base/'new-private.json';a.save_packet(r,output);self.assertEqual(output.stat().st_mode&0o777,0o600)

    def test_broken_optional_native_review_does_not_disable_personal_artifact(self):
        from tools import c2pa_native_obligations
        with mock.patch.object(c2pa_native_obligations,'verify',side_effect=ValueError('PRIVATE_OPTIONAL_CANARY')):
            with self.assertRaises(ValueError)as failed:a.graph('c2pa-linux-x86_64')
            self.assertEqual(str(failed.exception),'Artifact evidence unavailable.')
            self.assertEqual(len(a.graph('ps-source')['nodes']),9)
            self.assertTrue(self.record()['policy']['release_allowed'])

    def test_partial_or_corrupt_temporary_write_never_publishes(self):
        r=self.record()
        for short in (True,False):
            output=self.base/('short.json'if short else'corrupt.json')
            class BrokenStream:
                def __init__(self,fd):self.fd=fd
                def __enter__(self):return self
                def __exit__(self,*_):pass
                def fileno(self):return self.fd
                def write(self,raw):return os.write(self.fd,raw[:1]if short else b'x'*len(raw))
                def flush(self):pass
            with mock.patch.object(io.os,'fdopen',side_effect=lambda fd,*args,**kw:BrokenStream(fd)):
                with self.assertRaises(ValueError):a.save_packet(r,output)
            self.assertFalse(output.exists());self.assertEqual(list(self.base.glob('.artifact-evidence-*')),[])
    def test_output_parent_drift_during_source_recheck_refuses_before_link(self):
        parent=self.base/'destination';parent.mkdir(mode=0o700);output=parent/'record.json'
        def changed():parent.rename(self.base/'old-destination');parent.mkdir(mode=0o700)
        with io.Capture()as c:
            with self.assertRaises(ValueError):c.save(output,{'state':'COMPLETE'},1000,prepublish=changed)
        self.assertFalse(output.exists());self.assertFalse((self.base/'old-destination/record.json').exists())

    def test_post_link_corruption_is_uncertain_and_never_rolled_back(self):
        r=self.record();out=self.base/'corrupted-after-link.json';link=io.os.link
        def corrupt(temporary,name,*args,**kwargs):
            link(temporary,name,*args,**kwargs)
            fd=os.open(name,os.O_WRONLY,dir_fd=kwargs['dst_dir_fd'])
            try:os.write(fd,b'X')
            finally:os.close(fd)
        with mock.patch.object(io.os,'link',side_effect=corrupt):
            with self.assertRaises(io.OutputCommitUncertain):a.save_packet(r,out)
        self.assertTrue(out.exists());self.assertEqual(out.read_bytes()[:1],b'X')

if __name__=='__main__':unittest.main()
