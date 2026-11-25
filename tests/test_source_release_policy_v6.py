"""Finite V6 refusal and custody controls; inert fixtures are not release authority."""
import copy
import hashlib
import json
import os
from pathlib import Path
import signal
import tempfile
import types
import unittest
from unittest.mock import patch

from tools import source_release_policy_v6 as v

ROOT=Path(__file__).resolve().parents[1]


class SourceCopyV6(unittest.TestCase):
    def data(self):
        return v.policy((ROOT/v.POLICY).read_bytes())

    def fixture(self, changes=None):
        blobs={}
        def row(raw):
            oid=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
            blobs[oid]=raw
            return ('100644',oid,len(raw))
        before={n:row(raw)for n,raw in {'LICENSE':b'Apache project license\n',
            'tools/dependency_policy.py':b'# immutable\n',
            'owned.py':b'# SPDX-License-Identifier: Apache-2.0\nold=1\n'}.items()}
        observed=dict(before)
        for n,raw in (changes or {}).items():observed[n]=row(raw)
        data={'project_files':['new.py','owned.py'],'maintained_project_files':['owned.py'],
            'project_limits':{'new.py':10000,'owned.py':10000},
            'foundations':{'tools/dependency_policy.py':{}},'legacy_v5_copied_files':[]}
        reads=[]
        def read(item):reads.append(item);return blobs[item[1]]
        return data,before,observed,read,reads

    def classify(self,*args):return v.classify(*args,v.Clock())

    def synthetic_baseline(self):
        return {'profile':'source-copy-additions/v5','pass':True,'status':'SOURCE_COPY_PROFILE_SATISFIED',
            'source_copy_profile_satisfied':True,'source_commit':v.BASELINE,'source_tree':v.BASELINE_TREE,
            'files':v.BASELINE_FILES,'source_bytes':v.BASELINE_BYTES,'method_sha256':v.V5_METHOD_SHA,
            'policy_sha256':v.V5_POLICY_SHA,'baseline_v4_verified':True,
            'baseline_cleanup_acknowledged':True,'inspected_body_charge':v.BASELINE_RESERVATION,
            **dict.fromkeys(v.FALSE_CLAIMS,False)}

    def test_literal_tranche_preserves_historical_charges(self):
        d=self.data();self.assertEqual(len(d['project_files']),158)
        self.assertEqual(len(d['legacy_v5_project_names']),139)
        self.assertEqual(len(d['legacy_v4_names']),159)
        self.assertEqual(len(d['legacy_v5_copied_files'][0]['anchors']),95)
        prior=set(d['legacy_v5_project_names'])|{x['path']for x in d['legacy_v5_copied_files']}
        self.assertEqual(len(prior|set(d['project_files'])),268)
        self.assertGreater(len(prior|set(d['project_files'])),v.MAX_PROJECT)
        self.assertTrue(all(x is False for x in d['claims'].values()))

    def test_old_method_and_grant_tables_are_byte_pinned(self):
        for name,row in v.FOUNDATION_PINS.items():
            raw=(ROOT/name).read_bytes()
            self.assertEqual(len(raw),row['bytes']);self.assertEqual(v.sha(raw),row['sha256'])
        self.assertEqual(v.FOUNDATION_PINS['tools/dependency_policy.py']['sha256'],
            'e72e478a7508e6c3e6e000803ee4d583900f626cc219870fd1ad140131608408')

    def test_one_legacy_metadata_role_only(self):
        name='eval/dependencies/source-snapshot-release.json'
        fixed={name:(ROOT/name).read_bytes()}
        self.assertEqual(v.metadata_maintenance_eligibility(fixed),
            {'services/anonymizer/replay_metadata.py'})

    def test_legacy_metadata_missing_or_duplicate_refuses(self):
        name='eval/dependencies/source-snapshot-release.json'
        legacy=json.loads((ROOT/name).read_bytes())
        row=next(x for x in legacy['files']if x[0]=='services/anonymizer/replay_metadata.py')
        for rows in ([],[row,row]):
            with self.assertRaises(v.Refused)as error:
                v.metadata_maintenance_eligibility({name:v.canonical({'files':rows})})
            self.assertEqual(error.exception.code,'grant_unavailable')

    def test_legacy_metadata_exact_tuple_and_no_neighbor_expansion(self):
        name='eval/dependencies/source-snapshot-release.json'
        legacy=json.loads((ROOT/name).read_bytes())
        row=next(x for x in legacy['files']if x[0]=='services/anonymizer/replay_metadata.py')
        neighbor=list(row);neighbor[0]='services/anonymizer/unknown.py'
        self.assertEqual(v.metadata_maintenance_eligibility({name:v.canonical({'files':[row,neighbor]})}),{row[0]})
        for index,value in ((1,'100755'),(2,'0'*40),(3,1787),(4,'copied-text'),(5,'0'*64)):
            changed=list(row);changed[index]=value
            with self.assertRaises(v.Refused)as error:
                v.metadata_maintenance_eligibility({name:v.canonical({'files':[changed]})})
            self.assertEqual(error.exception.code,'grant_unavailable')

    def test_tiny_changed_and_new_source_positive_has_no_release_claim(self):
        d,b,o,read,_=self.fixture({'new.py':b'# SPDX-License-Identifier: Apache-2.0\nx=1\n',
            'owned.py':b'# SPDX-License-Identifier: Apache-2.0\nx=2\n'})
        result=self.classify(d,b,o,read)
        self.assertEqual(result['introduced_named_project_text_files'],1)
        self.assertEqual(result['changed_named_project_text_files'],1)
        self.assertNotIn('release_authorized',result)

    def test_unknown_denominator_refuses_before_any_body_read(self):
        d,b,o,read,reads=self.fixture({'unknown.py':b'data'})
        with self.assertRaises(v.Refused)as error:self.classify(d,b,o,read)
        self.assertEqual(error.exception.code,'unknown_path');self.assertEqual(reads,[])

    def test_missing_baseline_member_refuses_before_body(self):
        d,b,o,read,reads=self.fixture();o.pop('LICENSE')
        with self.assertRaises(v.Refused)as error:self.classify(d,b,o,read)
        self.assertEqual(error.exception.code,'missing_path');self.assertEqual(reads,[])

    def test_immutable_foundation_cannot_be_relabelled_project(self):
        d,b,o,read,_=self.fixture({'tools/dependency_policy.py':b'changed'})
        d['project_files'].append('tools/dependency_policy.py')
        with self.assertRaises(v.Refused)as error:self.classify(d,b,o,read)
        self.assertEqual(error.exception.code,'foundation_changed')

    def test_copied_body_and_anchor_are_not_recycled_as_project(self):
        for changed in ['LICENSE','owned.py']:
            d,b,o,read,_=self.fixture({changed:b'changed'})
            d['legacy_v5_copied_files']=[{'path':'owned.py','anchors':{'LICENSE':{}}}]
            with self.assertRaises(v.Refused)as error:self.classify(d,b,o,read)
            self.assertEqual(error.exception.code,'grant_changed')

    def test_current_path_requires_explicit_maintenance(self):
        d,b,o,read,_=self.fixture({'owned.py':b'# SPDX-License-Identifier: Apache-2.0\nx=3\n'})
        d['maintained_project_files']=[]
        with self.assertRaises(v.Refused):self.classify(d,b,o,read)

    def test_existing_and_new_foreign_license_markers_refuse(self):
        for n,raw in [('owned.py',b'# SPDX-License-Identifier: MIT\nx=1\n'),
            ('new.py',b'# Copyright unrelated publisher\nx=1\n')]:
            d,b,o,read,_=self.fixture({n:raw})
            with self.assertRaises(v.Refused)as error:self.classify(d,b,o,read)
            self.assertEqual(error.exception.code,'license_declaration_changed')

    def test_bool_or_link_mode_source_rows_refuse(self):
        for item in [('100644','a'*40,True),('120000','a'*40,1)]:
            d,b,o,read,_=self.fixture();o['owned.py']=item
            with self.assertRaises(v.Refused):self.classify(d,b,o,read)

    def test_literal_161_and_exact_member_cap_refuse(self):
        d,b,o,read,_=self.fixture();d['project_files']=['p'+str(i)for i in range(161)]
        with self.assertRaises(v.Refused):self.classify(d,b,o,read)
        d,b,o,read,_=self.fixture({'new.py':b'abc'})
        d['project_limits']['new.py']=2
        with self.assertRaises(v.Refused)as error:self.classify(d,b,o,read)
        self.assertEqual(error.exception.code,'resource_limit')

    def test_inherited_read_charge_is_not_reset_or_reused(self):
        blob=b'x';oid=hashlib.sha1(b'blob 1\0x').hexdigest();reads=[]
        def git(args,limit):reads.append(args);return blob
        bodies=v.Bodies(git,v.Clock(),reserved=v.MAX_INSPECTED-2)
        self.assertEqual(bodies.read(('100644',oid,1)),blob)
        self.assertEqual(bodies.read(('100644',oid,1)),blob);self.assertEqual(len(reads),1)
        with self.assertRaises(v.Refused):bodies.charge(1)

    def test_serial_baseline_receives_same_original_clock(self):
        clock=v.Clock();original=(clock.start,clock.work,clock.end);seen=[]
        def check(root,commit,received):
            seen.append((root,commit,received));return self.synthetic_baseline()
        result=v.baseline(types.SimpleNamespace(_verify=check),clock)
        self.assertIs(seen[0][2],clock);self.assertEqual(seen[0][1],v.BASELINE)
        self.assertEqual((clock.start,clock.work,clock.end),original)
        self.assertEqual(result['inspected_body_charge'],40242180)

    def test_baseline_wrong_identity_grant_charge_or_cleanup_refuses(self):
        for key,value in [('source_tree','0'*40),('release_authorized',True),
            ('inspected_body_charge',40242181),('baseline_cleanup_acknowledged',False)]:
            result=self.synthetic_baseline();result[key]=value
            with self.assertRaises(v.Refused):v.baseline(types.SimpleNamespace(_verify=lambda *a:result),v.Clock())

    def test_baseline_cannot_restart_or_exhaust_cumulative_clock(self):
        def reset(root,commit,clock):clock.work+=1;return self.synthetic_baseline()
        with self.assertRaises(v.Refused)as error:v.baseline(types.SimpleNamespace(_verify=reset),v.Clock())
        self.assertEqual(error.exception.code,'deadline')
        with patch.object(v.time,'monotonic',side_effect=[0.,1.,26.]):
            clock=v.Clock()
            with self.assertRaises(v.Refused):v.baseline(types.SimpleNamespace(_verify=lambda *a:self.synthetic_baseline()),clock)

    def test_clock_backwards_and_nonfinite_are_sticky(self):
        with patch.object(v.time,'monotonic',side_effect=[100.,101.,99.,102.]):
            clock=v.Clock();clock.now()
            with self.assertRaises(v.Refused):clock.now()
            with self.assertRaises(v.Refused):clock.now()
        with patch.object(v.time,'monotonic',return_value=float('nan')):
            with self.assertRaises(v.Refused):v.Clock()

    def test_joined_descriptor_ceiling_refuses_without_a_new_child(self):
        with patch.object(v,'fd_room',return_value=32):self.assertEqual(v.spawn_room(),32)
        with patch.object(v,'fd_room',return_value=33):
            with self.assertRaises(v.Refused):v.spawn_room()
        self.assertEqual(v.MAX_FDS,80)

    def test_regular_capture_hardlink_fifo_and_symlink_refuse(self):
        with tempfile.TemporaryDirectory()as temp:
            root=Path(temp).resolve();p=root/'x';p.write_bytes(b'one')
            self.assertEqual(v.capture(p,3,v.Clock()),b'one')
            with self.assertRaises(v.Refused):v.capture(p,2,v.Clock())
            linked=root/'linked';os.link(p,linked)
            with self.assertRaises(v.Refused):v.capture(p,3,v.Clock())
            linked.unlink();p.unlink();os.mkfifo(p)
            with self.assertRaises(v.Refused):v.capture(p,3,v.Clock())
            p.unlink();(root/'target').write_bytes(b'x');p.symlink_to(root/'target')
            with self.assertRaises(v.Refused):v.capture(p,3,v.Clock())

    def test_original_alarm_handler_restored_on_setup_failure(self):
        original=signal.getsignal(signal.SIGALRM)
        with patch.object(v.signal,'setitimer',side_effect=[OSError('setup'),None]):
            with self.assertRaises(OSError):
                with v.original_clock(v.Clock()):pass
        self.assertEqual(signal.getsignal(signal.SIGALRM),original)

    def test_current_catalogue_does_not_change_other_thirteen_routes(self):
        import subprocess
        previous=json.loads(subprocess.check_output(['git','show',v.BASELINE+':eval/dependency-policy.json']))
        current=json.loads((ROOT/'eval/dependency-policy.json').read_bytes())
        for key in current:
            if key!='components':self.assertEqual(current[key],previous[key])
        for key in current['components']:
            if key!= 'source-snapshot-unreviewed':self.assertEqual(current['components'][key],previous['components'][key])
        old_source=copy.deepcopy(previous['components']['source-snapshot-unreviewed'])
        new_source=copy.deepcopy(current['components']['source-snapshot-unreviewed'])
        old_source.pop('files');new_source.pop('files');self.assertEqual(old_source,new_source)


if __name__=='__main__':unittest.main()
