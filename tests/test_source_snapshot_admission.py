"""Copy permission cannot be manufactured from a packet or a status flag."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import source_snapshot_admission as a
from tools import dependency_policy as p

ROOT = Path(__file__).resolve().parents[1]
LEGACY_6D = '6d752cd0ae127e7d1ebe93499ab6fd83f55dcafd'
LEGACY_Q='9c98ac5000a2784df66d8e1f5bf17d34cb0f53b7'
SELECTED='898dc254ff8d4c924d699afe732d3c1bbfe1bb01'


class SourceSnapshotAdmission(unittest.TestCase):
    def rows(self):
        policy = json.loads((ROOT / p.POLICY).read_bytes())
        # In-memory row fixture for unit refusal controls; real admission tests
        # below continue to use the actual installed registry.
        component=policy['components'][a.COMPONENT]
        import hashlib
        component['files']=[{'path':n,'bytes':(ROOT/n).stat().st_size,'sha256':hashlib.sha256((ROOT/n).read_bytes()).hexdigest()}for n in sorted(a.COMPONENT_FILES)]
        return component,policy['routes']['source-snapshot']

    def status(self,component,route):
        with patch.object(a,'_rows',return_value=self.rows()[0]['files']):return a.component_status(component,route)

    def test_real_current_source_copy_not_runtime_accuracy_or_signature(self):
        from tools import source_release_policy_v3 as legacy
        from tools import source_release_policy_v5 as current
        historical = legacy.verify(source_commit=LEGACY_6D)
        self.assertIs(historical['pass'], True)
        self.assertEqual(historical['profile'], legacy.PROFILE)
        self.assertEqual(historical['source_commit'], LEGACY_6D)
        self.assertEqual(historical['files'], 13502)
        self.assertEqual(historical['source_bytes'], 142114658)
        for key in legacy.FALSE_CLAIMS:
            self.assertIs(historical[key], False)
        from tools import source_release_policy_v4 as previous
        prior=previous.verify(source_commit=LEGACY_Q)
        self.assertIs(prior['pass'],True);self.assertEqual(prior['files'],13747);self.assertEqual(prior['source_bytes'],147265706)
        result = a.review(source_commit=SELECTED)
        self.assertIs(result['pass'], True)
        self.assertEqual(result['profile'], current.PROFILE)
        self.assertEqual(result['source_commit'], SELECTED)
        self.assertEqual(result['files'],13888)
        self.assertEqual(result['source_bytes'],151697171)
        for key in ('legal_clearance', 'compiled_runtime_permission',
                    'source_archive_admitted', 'release_authorized', 'accuracy',
                    'complete_F057_X02'):
            self.assertIs(result[key], False)

    def test_source_admission_requires_actual_finite_classifier(self):
        component, route = self.rows()
        with patch.object(a, 'review', side_effect=ValueError('unavailable')) as check:
            self.assertEqual(self.status(component, route)[0], 'blocked_unknown')
            check.assert_called_once()

    def test_altered_source_hash_and_updated_status_flag_do_not_bypass(self):
        component, route = self.rows()
        row = next(row for row in component['files'] if row['path'] == 'LICENSE')
        row['sha256'] = '0' * 64
        with patch.object(a, 'review', side_effect=AssertionError('must refuse first')):
            self.assertEqual(self.status(component, route)[0], 'blocked_unknown')

    def test_foreign_route_or_extra_entrypoint_cannot_inherit_copy_rights(self):
        component, route = self.rows()
        for field, value in (('kind', 'bundled-runtime'),
                             ('entrypoints', ['services/evaluator/app.py']),
                             ('prerequisites', ['All runtimes approved'])):
            altered = copy.deepcopy(route)
            altered[field] = value
            with patch.object(a, 'review', side_effect=AssertionError('must refuse first')):
                self.assertEqual(self.status(component, altered)[0], 'blocked_unknown')

    def test_paid_and_closed_cannot_be_relabelled_as_copy_only(self):
        component, route = self.rows()
        for field, value, state in (('required_processing_payment', True, 'paid'),
                                    ('source_available', False, 'prohibited')):
            altered = copy.deepcopy(component)
            altered[field] = value
            with patch.object(a, 'review', side_effect=AssertionError('must refuse first')):
                self.assertEqual(self.status(altered, route)[0], state)

    def test_missing_notice_unknown_member_or_boolean_number_refuses(self):
        component, route = self.rows()
        for field, value in (('notice_paths', []), ('required_processing_payment', 0),
                             ('source_available', 1)):
            altered = copy.deepcopy(component)
            altered[field] = value
            self.assertEqual(self.status(altered, route)[0], 'blocked_unknown')
        altered = copy.deepcopy(component)
        altered['files'].append({'path': 'unreviewed.py', 'sha256': '0' * 64, 'bytes': 1})
        self.assertEqual(self.status(altered, route)[0], 'blocked_unknown')

    def test_caller_chosen_checkout_cannot_supply_approval(self):
        with tempfile.TemporaryDirectory() as name:
            with self.assertRaises(ValueError):
                a.review(root=Path(name), source_commit=SELECTED)

    def test_unavailable_copy_route_never_disables_standalone_ps(self):
        before = p.require_route('ps-source')
        with patch.object(a, 'component_status', return_value=('blocked_unknown', 'test_unavailable')):
            self.assertIs(p.evaluate('source-snapshot')['release_allowed'], False)
            self.assertEqual(p.require_route('ps-source'), before)

    def test_received_copy_report_with_forged_authority_or_commit_refuses(self):
        from contextlib import contextmanager
        baseline=a.review(source_commit=SELECTED)  # one real active positive first
        self.assertIs(baseline['pass'],True);real=a._captured_copy
        for key,value in(('pass',1),('source_copy_profile_satisfied',1),('source_commit','0'*40),('release_authorized',True),('files',True),('accuracy',True),('method_sha256','0'*64)):
            altered=copy.deepcopy(baseline);altered[key]=value
            @contextmanager
            def injected(root):
                with real(root)as(namespace,method,table):
                    namespace.verify=lambda **unused:altered  # result boundary only, not real authority
                    yield namespace,method,table
            with patch.object(a,'_captured_copy',injected):
                with self.assertRaises(ValueError):a.review(source_commit=SELECTED)

    def test_source_spdx_retains_every_identity_and_edge_when_prose_is_deduplicated(self):
        from tools import distribution_artifacts as artifacts
        nodes = [{'key': 'git:' + name, 'name': name, 'version': None,
                  'origin': 'committed-git-blob', 'evidence': 'scripts/source_snapshot_v3.py',
                  'checksums': [], 'details': {'git_blob_oid': oid, 'mode': '100644'}}
                 for name, oid in (('LICENSE', 'a' * 40), ('scripts/check-ps.py', 'b' * 40))]
        graph = {'nodes': nodes, 'relationships': [], 'source_sha256': {'LICENSE': 'c' * 64}}
        document = artifacts.spdx('source-snapshot', {'sha256': 'd' * 64}, graph,
                                  '2026-11-23T18:00:00Z')
        components = document['packages'][1:]
        self.assertEqual({row['name'] for row in components}, {row['name'] for row in nodes})
        self.assertEqual(len(document['relationships']), 3)
        for node in nodes:
            component = next(row for row in components if row['name'] == node['name'])
            self.assertIn(node['details']['git_blob_oid'], component['sourceInfo'])
            self.assertIn('mode 100644', component['sourceInfo'])
            self.assertNotIn('checksums', component)
            self.assertEqual(component['licenseConcluded'], 'NOASSERTION')
            self.assertTrue(any(row.get('relatedSpdxElement') == component['SPDXID'] and
                                row['relationshipType'] == 'OTHER'
                                for row in document['relationships']))
        self.assertIn('not a containment or permission claim', document['comment'])
        self.assertTrue(all(row.get('comment') == 'Source evidence'
                            for row in document['relationships']
                            if row['relationshipType'] == 'OTHER'))


class SourceCallerLifecycle(unittest.TestCase):
    """Owned FS controls only; no simulated result grants production rights."""
    def fixture(self):
        import hashlib,os
        t=tempfile.TemporaryDirectory(dir=Path(tempfile.gettempdir()).resolve());self.addCleanup(t.cleanup)
        root=Path(t.name);root.chmod(0o700);path=root/'member';path.write_bytes(b'one');path.chmod(0o600)
        return root,path,{path:hashlib.sha256(b'one').hexdigest()}
    def snapshot(self,root,path,expected,private=False):
        from tools.artifact_evidence_io import Capture
        with Capture()as capture:
            capture.read(path,16_000_000,private=private)
            result=a._SourceReadset.from_capture(capture,expected,anchors=(root,))
        self.addCleanup(result.close);return result
    def test_closed_phase_positive_and_one_read_ledger(self):
        root,path,expected=self.fixture();proof=self.snapshot(root,path,expected)
        self.assertEqual(proof.total,3);proof.check();self.assertEqual(proof.total,6)
        proof.total=64_000_000
        with self.assertRaises(ValueError):proof.check()
    def test_changed_body_and_equal_bytes_successor_refuse(self):
        import os
        root,path,expected=self.fixture();proof=self.snapshot(root,path,expected);path.write_bytes(b'two')
        with self.assertRaises(ValueError):proof.check()
        proof.close();path.write_bytes(b'one');proof=self.snapshot(root,path,expected)
        original=root/'original';path.rename(original);path.write_bytes(b'one');path.chmod(0o600)
        with self.assertRaises(ValueError):proof.check()
        self.assertTrue(original.exists())
    def test_parent_successor_and_late_private_git_refuse(self):
        import os
        root,path,expected=self.fixture();proof=self.snapshot(root,path,expected,True);(root/'.git').write_text('marker')
        with self.assertRaises(ValueError):proof.check()
        self.assertTrue((root/'.git').exists());proof.close();(root/'.git').unlink()
        child=root/'dir';child.mkdir();leaf=child/'x';leaf.write_bytes(b'one')
        import hashlib
        proof=self.snapshot(root,leaf,{leaf:hashlib.sha256(b'one').hexdigest()});child.rename(root/'retained');child.mkdir();(child/'x').write_bytes(b'one')
        with self.assertRaises(ValueError):proof.check()
    def test_unexpected_capture_member_refuses_no_leaked_anchor(self):
        import os
        from tools.artifact_evidence_io import Capture
        root,path,expected=self.fixture();other=root/'other';other.write_bytes(b'one')
        before=a._source_room(0)
        with Capture()as capture:
            capture.read(path,100,private=False);capture.read(other,100,private=False)
            with self.assertRaises(ValueError):a._SourceReadset.from_capture(capture,expected,anchors=(root,))
        self.assertEqual(a._source_room(0),before)
    def test_close_attempts_all_once_and_is_idempotent(self):
        import os
        root,path,expected=self.fixture();other=root/'dir';other.mkdir()
        proof=a._SourceReadset(expected,anchors=(root,other));fds=[r[1]for r in proof.anchors];real=os.close;closed=[]
        def close(fd):
            real(fd);closed.append(fd)
            if len(closed)==1:raise OSError('after close')
        with patch.object(a.os,'close',side_effect=close):
            with self.assertRaises(OSError):proof.close()
        self.assertEqual(set(closed),set(fds));self.assertEqual(len(closed),len(fds));proof.close()
    def test_anchor_identity_fault_after_real_dup_closes_registered_fd(self):
        import os
        root,path,expected=self.fixture();before=a._source_room(0);duplicate=os.dup;fstat=os.fstat;held=[]
        def dup(fd):
            value=duplicate(fd);held.append(value);return value
        def fail(fd):
            if fd in held:raise OSError('POST_DUP_IDENTITY_FAULT')
            return fstat(fd)
        with patch.object(a.os,'dup',side_effect=dup),patch.object(a.os,'fstat',side_effect=fail):
            with self.assertRaises(OSError):a._SourceReadset(expected,anchors=(root,))
        self.assertEqual(len(held),1)
        with self.assertRaises(OSError):os.fstat(held[0])
        self.assertEqual(a._source_room(0),before)
    def test_actual_pending_alarm_open_adoption_closes_owned_fd(self):
        import os,signal
        root,path,expected=self.fixture();before=a._source_room(0);old=signal.getsignal(signal.SIGALRM);real=os.open;first=True
        class Cancelled(BaseException):pass
        def stop(*unused):raise Cancelled()
        def open_file(*args,**kw):
            nonlocal first
            fd=real(*args,**kw)
            if first:first=False;signal.raise_signal(signal.SIGALRM)
            return fd
        try:
            signal.signal(signal.SIGALRM,stop)
            with patch.object(a.os,'open',side_effect=open_file):
                with self.assertRaises(Cancelled):a._SourceReadset(expected,anchors=(root,))
        finally:signal.signal(signal.SIGALRM,old)
        self.assertEqual(a._source_room(0),before)
    def test_captured_active_method_ignores_poisoned_module_cache(self):
        import hashlib,sys,types
        rows=[{'path':n,'bytes':(ROOT/n).stat().st_size,'sha256':hashlib.sha256((ROOT/n).read_bytes()).hexdigest()}for n in sorted(a.COMPONENT_FILES)]
        poison=types.ModuleType('tools.source_release_policy_v5');poison.verify=lambda **kw:(_ for _ in()).throw(AssertionError('cached code'))
        with patch.dict(sys.modules,{'tools.source_release_policy_v5':poison}),patch.object(a,'_rows',return_value=rows):
            with a._captured_copy(ROOT)as(copy,method,table):
                self.assertIsNot(copy,poison);self.assertEqual(copy.verify.__code__.co_filename,'<captured-active-source-copy-v5>')
                self.assertEqual(method,hashlib.sha256((ROOT/'tools/source_release_policy_v5.py').read_bytes()).hexdigest())
                self.assertEqual(table,copy.POLICY_SHA256)

if __name__ == '__main__':
    unittest.main()
