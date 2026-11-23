"""Tiny composed consumer controls; injected rights are not a grant approval."""
import gzip
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import types
import unittest
from unittest.mock import patch
from scripts import source_snapshot_v3 as snapshot

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('copy_archive_v2', ROOT/'tools/source_release_policy_v2.py')
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


class CopyArchiveV2(unittest.TestCase):
    def fixture(self):
        temp = tempfile.TemporaryDirectory(prefix='copy-v2-boundary-')
        self.addCleanup(temp.cleanup)
        root = Path(temp.name).resolve()
        def git(*args):
            return subprocess.check_output(['/usr/bin/git', '-C', str(root), *args], stderr=subprocess.DEVNULL)
        git('init', '-q');git('config', 'user.name', 'Synthetic Engineering')
        git('config', 'user.email', 'fixture@example.invalid')
        (root/'a.txt').write_bytes(b'actual-source\n')
        git('add', 'a.txt');git('commit', '-qm', 'Synthetic source')
        commit = git('rev-parse', 'HEAD').decode().strip()
        raw = snapshot.build(root, commit)
        for name in [p.POLICY, p.LEGACY, 'tools/source_release_policy.py', 'tools/source_snapshot_binding.py',
                     'scripts/worker_process.py', 'scripts/source_snapshot.py',
                     'scripts/source_snapshot_v2.py', 'scripts/source_snapshot_v3.py']:
            target=root/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,target)
        return root, commit, raw

    def invoke(self, root, commit, raw):
        # Only isolate the rights decision: the binding worker/Git and archive are real.
        with patch.object(p, 'ROOT', root), patch.object(p, 'verify', return_value={
                'pass': True, 'source_copy_profile_satisfied': True, 'files': 1, 'source_bytes': 14}):
            return p.verify_archive(raw, source_commit=commit)

    def test_old_v2_and_v1_identities_are_preserved(self):
        history=ROOT/'eval/dependencies/source-copy-v2-history'
        self.assertEqual(p.sha((history/'source_release_policy_v2-1438edcb8a7f363fd8da77432d6693b33da529f4dbee17f92655f098d95387fc.py').read_bytes()),
                         '1438edcb8a7f363fd8da77432d6693b33da529f4dbee17f92655f098d95387fc')
        self.assertEqual(p.sha((history/'source-snapshot-release-v2-b5ffe6abefe80a0b42fcfb3516dc11845e337b21f8612bd14b83f57269a49809.json').read_bytes()),
                         'b5ffe6abefe80a0b42fcfb3516dc11845e337b21f8612bd14b83f57269a49809')
        self.assertEqual(p.sha((ROOT/p.LEGACY).read_bytes()),p.LEGACY_SHA256)
        self.assertEqual(p.sha((ROOT/'tools/source_release_policy.py').read_bytes()),p.LEGACY_HELPER_SHA256)

    def test_marker_transition_is_exact_and_never_other_path_or_bytes(self):
        raw=(ROOT/p.POLICY).read_bytes();legacy=(ROOT/p.LEGACY).read_bytes()
        d,_,_=p.policy(raw,legacy)
        row=next(r for r in d['delta'] if r[0]=='docs/legal/execution-packet.md')
        self.assertEqual((row[6],row[2]),p.MARKER_TRANSITIONS[row[0]][1:])
        for mutate in [lambda x:x.__setitem__(2,'1'*40),lambda x:x.__setitem__(6,'0'*64)]:
            forged=json.loads(raw);changed=next(r for r in forged['delta'] if r[0]==row[0]);mutate(changed)
            candidate=json.dumps(forged).encode()
            with patch.object(p,'POLICY_SHA256',p.sha(candidate)),self.assertRaises(p.Refused):p.policy(candidate,legacy)

    def test_unknown_copy_rights_refuse_before_any_binding_execution(self):
        with patch.object(p,'verify',return_value={'pass':False,'reason':'unknown_path'}), \
             patch.object(p,'_binding_capture',side_effect=AssertionError('binding must not execute')):
            r=p.verify_archive(b'not parsed as gzip',source_commit=p.SELECTED_PROTECTED)
        self.assertFalse(r['pass']);self.assertEqual(r['reason'],'unknown_path')
        self.assertNotIn('source_files',r)

    def test_archive_basic_type_and_capacity_refuse_before_work(self):
        with patch.object(p,'MAX_ARCHIVE',8),patch.object(p,'verify',side_effect=AssertionError('no work')):
            for raw in [b'',bytearray(b'abc'),b'x'*9]:
                self.assertFalse(p.verify_archive(raw,source_commit=p.SELECTED_PROTECTED)['pass'])

    def test_actual_tiny_git_archive_and_coherent_forgery(self):
        root,commit,raw=self.fixture();result=self.invoke(root,commit,raw)
        self.assertTrue(result['pass'],result);self.assertTrue(result['trusted_git_bytes_matched'])
        self.assertEqual(result['source_files'],1);self.assertIs(result['signature_verified'],False)
        for key in p.FALSE_CLAIMS:self.assertIs(result[key],False)
        data=b'forged-source\n'
        metadata={'profile':snapshot.PROFILE,'source_commit':commit,'kind':'development_source_snapshot',
                  'tag_release_validated':False,'installed_dependencies_included':False,
                  'files':[{'path':'a.txt','mode':0o644,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}]}
        out=io.BytesIO()
        with gzip.GzipFile(fileobj=out,mode='wb',filename='',mtime=0) as gz:
            with tarfile.open(fileobj=gz,mode='w',format=tarfile.USTAR_FORMAT) as tar:
                for name,body in [(snapshot.META,json.dumps(metadata,sort_keys=True,separators=(',',':')).encode()),('a.txt',data)]:
                    info=tarfile.TarInfo(snapshot.PREFIX+name);info.mode=0o644;info.size=len(body);tar.addfile(info,io.BytesIO(body))
        forged=out.getvalue();snapshot.inspect(forged,commit)
        result=self.invoke(root,commit,forged);self.assertFalse(result['pass']);self.assertEqual(result['reason'],'archive_refused')

    def test_changed_binding_source_refuses_without_execution(self):
        root,commit,raw=self.fixture();(root/'tools/source_snapshot_binding.py').write_bytes(b'raise RuntimeError("PRIVATE_CANARY")\n')
        result=self.invoke(root,commit,raw);self.assertFalse(result['pass']);self.assertEqual(result['reason'],'foundation_changed')
        self.assertNotIn('PRIVATE_CANARY',json.dumps(result))

    def test_captured_binding_not_reopened_for_execution(self):
        root,commit,raw=self.fixture();marker=root/'poison_executed'
        with patch.object(p,'ROOT',root):owned=p._binding_capture((root/'tools/source_snapshot_binding.py').read_bytes())
        def run(*args,**kwargs):
            (root/'tools/source_snapshot_binding.py').write_text('from pathlib import Path\nPath('+repr(str(marker))+').touch()\n')
            return owned(*args,**kwargs)
        with patch.object(p,'_binding_capture',return_value=run):result=self.invoke(root,commit,raw)
        self.assertFalse(marker.exists());self.assertFalse(result['pass']);self.assertEqual(result['reason'],'source_changed')

    def test_success_aliases_and_wrong_binding_inventory_refuse(self):
        root,commit,raw=self.fixture()
        base={'profile':'source-snapshot-trusted-git-binding/v1','pass':True,'source_commit':commit,
              'source_tree':'1'*40,'source_files':1,'source_bytes':14,'archive_sha256':p.sha(raw),
              'trusted_git_bytes_matched':True,'signature_verified':False,'rights_approved':False,'release_authorized':False}
        for field,value in [('pass',1),('source_files',True),('source_bytes',True),('source_files',2),
                            ('signature_verified',0),('release_authorized',0),('source_commit','0'*40)]:
            body={**base,field:value}
            with patch.object(p,'_binding_capture',return_value=lambda *a,**k:json.dumps(body).encode()):
                result=self.invoke(root,commit,raw)
            self.assertFalse(result['pass'],field)


    def test_archive_stream_transport_preserves_large_input_without_widening_neutral_worker(self):
        import sys,time
        source=(ROOT/'tools/source_snapshot_binding.py').read_bytes()
        capture=p._binding_capture(source);payload=b'x'*1_000_001
        result=capture([sys.executable,'-I','-S','-B','-c',
                        'import sys;data=sys.stdin.buffer.read(1000002);print(len(data))'],
                       payload,time.monotonic()+5,64,new_session=True)
        self.assertEqual(result,b'1000001\n')
        with self.assertRaises(ValueError):
            p.worker()([sys.executable,'-c','raise SystemExit(99)'],input=payload,timeout=5,output_limit=64)


if __name__=='__main__':unittest.main()
