"""Finite V3 controls. Synthetic grants test mechanics, not actual publisher rights."""
import copy
import gzip
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('source_copy_v3',ROOT/'tools/source_release_policy_v3.py')
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
def oid(raw):return hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()


class SourceCopyV3(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v2,_=p.pinned_v2();cls.old=(ROOT/cls.v2.POLICY).read_bytes()
        cls.legacy_raw=(ROOT/cls.v2.LEGACY).read_bytes()
        cls.d2,cls.legacy,cls.base=cls.v2.policy(cls.old,cls.legacy_raw)
        cls.actual=json.loads((ROOT/p.POLICY).read_bytes())
        cls.observed={n:r[:3] for n,r in cls.base.items()}
        cls.baseline_bodies={}
        for name in [*p.METADATA_LEAVES,'tools/dependency_policy.py']:
            identity=cls.base[name][1]
            cls.baseline_bodies[identity]=subprocess.check_output(['/usr/bin/git','-C',str(ROOT),'cat-file','blob',identity])

    def synthetic(self):
        d=copy.deepcopy(self.actual);d['copied_files']=[]
        d['project_files']=['tools/source_release_policy_v3.py',d['metadata_transitions']['evidence']['path']]
        d['origins']={'synthetic':{'license':'Synthetic fixture only; not a real grant',
          'source_evidence':'Inert test bytes','copy_scope':'Unit boundary only',
          'required_anchors':[{'path':'synthetic/LICENSE','sha256':p.sha(b'Synthetic full grant\n')}],
          'unresolved':[]}}
        bodies={}
        for name,raw in [('synthetic/LICENSE',b'Synthetic full grant\n'),('synthetic/description.txt',b'Copied fixture prose\n')]:
            bodies[oid(raw)]=raw;d['copied_files'].append({'path':name,'mode':'100644','git_blob_oid':oid(raw),
             'sha256':p.sha(raw),'bytes':len(raw),'origin':'synthetic'})
        raw=json.dumps(d).encode()
        with patch.object(p,'POLICY_SHA256',p.sha(raw)):
            parsed,copied,project=p.overlay(raw,self.base,self.v2)
        def reader(identity,size):
            self.assertEqual(len(bodies[identity]),size);return bodies[identity]
        return parsed,copied,project,bodies,reader

    def checked(self,d,copied,project,observed,reader,tick=lambda:None):
        def combined_reader(identity,size):
            if identity in self.baseline_bodies:
                raw=self.baseline_bodies[identity];self.assertEqual(len(raw),size);return raw
            return reader(identity,size)
        return p.check(self.v2,self.d2,self.legacy,self.base,d,copied,project,observed,combined_reader,tick)

    def transition_fixture(self,new=True):
        # Synthetic complete metadata, not an actual producer or a grant adoption.
        source_path='tools/dependency_policy.py';old_code=b'old producer\n';new_code=b'new producer\n'
        old_sha,new_sha=p.sha(old_code),p.sha(new_code)
        old_map={source_path:old_sha,'synthetic/unchanged-source':'a'*64}
        new_map={**old_map,source_path:new_sha}
        namespace=lambda m:'urn:aitrustid:spdx:web-npm:'+p.sha(json.dumps(m,sort_keys=True,ensure_ascii=True,allow_nan=False,separators=(',',':')).encode())
        old_objects=[{'producer_sha256':old_map,'notice':'Retained grant','claims':{'legal_clearance':False}},
                     {'sources_sha256':old_map,'packages':[{'notice':'Retained author'}]},
                     {'documentNamespace':namespace(old_map),'licenseDeclared':'MIT'}]
        new_objects=copy.deepcopy(old_objects)
        new_objects[0]['producer_sha256']=new_map;new_objects[1]['sources_sha256']=new_map
        new_objects[2]['documentNamespace']=namespace(new_map)
        bodies={oid(old_code):old_code,oid(new_code):new_code};base={};observed={};rows=[];delta=[]
        for name,old_value,new_value in zip(p.METADATA_LEAVES,old_objects,new_objects):
            old_raw=json.dumps(old_value,sort_keys=True).encode();new_raw=json.dumps(new_value,sort_keys=True).encode()
            bodies[oid(old_raw)]=old_raw;bodies[oid(new_raw)]=new_raw
            old={'mode':'100644','git_blob_oid':oid(old_raw),'bytes':len(old_raw),'sha256':p.sha(old_raw),
                 'category':'other-retained-terms','origin':'synthetic-retained-origin'}
            current={'mode':'100644','git_blob_oid':oid(new_raw),'bytes':len(new_raw),'sha256':p.sha(new_raw)}
            leaf=list(p.METADATA_LEAVES[name]);before,after=old_value,new_value
            for key in leaf:before,after=before[key],after[key]
            rows.append({'path':name,'old':old,'new':current,'json_path':leaf,'old_value':before,'new_value':after})
            base[name]=('100644',oid(old_raw),len(old_raw),'other-retained-terms',None)
            chosen=current if new else old;observed[name]=(chosen['mode'],chosen['git_blob_oid'],chosen['bytes'])
            delta.append([name,'100644',oid(old_raw),len(old_raw),'other-retained-terms','synthetic-retained-origin',None])
        base[source_path]=('100644',oid(old_code),len(old_code),'project-text',None)
        chosen_code=new_code if new else old_code;observed[source_path]=('100644',oid(chosen_code),len(chosen_code))
        evidence=b'Actual fixture observation only\n';evidence_path='runs/synthetic-producer.json'
        bodies[oid(evidence)]=evidence;observed[evidence_path]=('100644',oid(evidence),len(evidence))
        additions={'metadata_transitions':{'producer_path':source_path,'old_producer_sha256':old_sha,
          'new_producer_sha256':new_sha,'evidence':{'path':evidence_path,'sha256':p.sha(evidence)},'rows':rows}}
        p.transition_schema(additions['metadata_transitions'],base,{evidence_path},self.v2)
        def read(identity,size):
            raw=bodies[identity];self.assertEqual(len(raw),size);return raw
        return additions,{'delta':delta},base,observed,bodies,read

    def metadata_check(self,fixture):
        additions,d2,base,observed,bodies,read=fixture
        return p.metadata_expected(self.v2,d2,{'grant_anchors':{}},base,additions,observed,read,lambda:None)

    def test_exact_generated_transition_and_all_old_keep_original_category(self):
        for new in (False,True):
            f=self.transition_fixture(new);expected,count=self.metadata_check(f)
            self.assertEqual(count,3 if new else 0)
            for name in p.METADATA_LEAVES:self.assertEqual(expected[name][3:],f[2][name][3:])
        f=self.transition_fixture(False);d=f[0]['metadata_transitions']
        raw=b'new producer\n';f[3][d['producer_path']]=('100644',oid(raw),len(raw))
        with self.assertRaises(p.Refused):self.metadata_check(f)

    def test_coherent_unrelated_notice_or_typed_claim_change_refuses(self):
        for mutate in (lambda x:x.update(notice='Deleted grant'),lambda x:x['claims'].update(legal_clearance=0)):
            f=self.transition_fixture();row=f[0]['metadata_transitions']['rows'][0]
            doc=json.loads(f[4][row['new']['git_blob_oid']]);mutate(doc);raw=json.dumps(doc,sort_keys=True).encode()
            row['new'].update(git_blob_oid=oid(raw),bytes=len(raw),sha256=p.sha(raw))
            f[3][row['path']]=('100644',oid(raw),len(raw));f[4][oid(raw)]=raw
            with self.assertRaises(p.Refused) as e:self.metadata_check(f)
            self.assertEqual(e.exception.code,'grant_changed')

    def test_partial_transition_wrong_producer_and_receipt_refuse(self):
        for kind in ('mixed','producer','receipt'):
            f=self.transition_fixture();d=f[0]['metadata_transitions']
            if kind=='mixed':
                r=d['rows'][0];old=r['old'];f[3][r['path']]=(old['mode'],old['git_blob_oid'],old['bytes'])
            elif kind=='producer':f[3][d['producer_path']]=f[2][d['producer_path']][:3]
            else:del f[3][d['evidence']['path']]
            with self.assertRaises(p.Refused):self.metadata_check(f)

    def test_transition_schema_and_origin_cannot_reclassify_retained_terms(self):
        for kind in ('category','bool_size','leaf','origin'):
            f=self.transition_fixture();d=f[0]['metadata_transitions'];r=d['rows'][0]
            if kind=='category':r['old']['category']='project-text'
            elif kind=='bool_size':r['new']['bytes']=True
            elif kind=='leaf':r['json_path']=['notice']
            else:r['old']['origin']='invented-origin'
            with self.assertRaises(p.Refused):
                p.transition_schema(d,f[2],{d['evidence']['path']},self.v2);self.metadata_check(f)

    def test_real_protected_base_and_all_nonclaims(self):
        r=p.verify(source_commit=p.BASE);self.assertIs(r['pass'],True,r)
        self.assertEqual((r['files'],r['source_bytes']),(13502,142114658))
        self.assertEqual(r['present_optional_copied_files'],0)
        self.assertIs(r['selected_profile_base_is_protected_release'],True)
        for k in p.FALSE_CLAIMS:self.assertIs(r[k],False)

    def test_immutable_v2_and_v1_anchors(self):
        self.assertEqual(p.sha((ROOT/'tools/source_release_policy_v2.py').read_bytes()),p.V2_METHOD_SHA256)
        self.assertEqual(p.sha(self.old),p.V2_POLICY_SHA256)
        self.assertEqual(p.sha(self.legacy_raw),self.v2.LEGACY_SHA256)
        self.assertEqual(self.v2.POLICY_SHA256,p.V2_POLICY_SHA256)

    def test_optional_absence_keeps_whole_base_denominator(self):
        d,c,project,bodies,reader=self.synthetic();r=self.checked(d,c,project,self.observed,reader)
        self.assertEqual(r['files'],13502);self.assertEqual(r['present_optional_copied_files'],0)

    def test_exact_present_optional_copy_requires_actual_anchor(self):
        d,c,project,bodies,reader=self.synthetic();observed=dict(self.observed)
        observed.update({n:(r['mode'],r['git_blob_oid'],r['bytes']) for n,r in c.items()})
        r=self.checked(d,c,project,observed,reader);self.assertEqual(r['files'],13504)
        self.assertEqual(r['present_optional_copied_files'],2)
        del observed['synthetic/LICENSE']
        with self.assertRaises(p.Refused) as e:self.checked(d,c,project,observed,reader)
        self.assertEqual(e.exception.code,'missing_path')

    def test_present_unresolved_metadata_never_becomes_permission(self):
        d,c,project,bodies,reader=self.synthetic();d['origins']['synthetic']['unresolved']=['Actual grant unavailable']
        observed=dict(self.observed);r=c['synthetic/description.txt'];observed[r['path']]=(r['mode'],r['git_blob_oid'],r['bytes'])
        with self.assertRaises(p.Refused) as e:self.checked(d,c,project,observed,lambda *a:self.fail('no decode'))
        self.assertEqual(e.exception.code,'grant_unavailable')

    def test_unknown_path_checked_before_any_phase_filter(self):
        d,c,project,bodies,reader=self.synthetic();observed={**self.observed,'future/unreviewed.md':('100644','1'*40,0)}
        with self.assertRaises(p.Refused) as e:self.checked(d,c,project,observed,lambda *a:self.fail('unknown decoded'))
        self.assertEqual(e.exception.code,'unknown_path')

    def test_missing_base_refuses_even_with_all_optional_rows_absent(self):
        d,c,project,bodies,reader=self.synthetic();observed=dict(self.observed);del observed['README.md']
        with self.assertRaises(p.Refused) as e:self.checked(d,c,project,observed,reader)
        self.assertEqual(e.exception.code,'missing_path')

    def test_changed_copied_metadata_refuses_before_decode(self):
        d,c,project,bodies,reader=self.synthetic();observed=dict(self.observed);r=c['synthetic/description.txt']
        observed[r['path']]=(r['mode'],'0'*40,r['bytes'])
        with self.assertRaises(p.Refused) as e:self.checked(d,c,project,observed,lambda *a:self.fail('changed decoded'))
        self.assertEqual(e.exception.code,'third_party_or_asset_changed')

    def test_changed_grant_anchor_sha_refuses(self):
        d,c,project,bodies,reader=self.synthetic();d['origins']['synthetic']['required_anchors'][0]['sha256']='0'*64
        observed={**self.observed,**{n:(r['mode'],r['git_blob_oid'],r['bytes']) for n,r in c.items()}}
        with self.assertRaises(p.Refused) as e:self.checked(d,c,project,observed,reader)
        self.assertEqual(e.exception.code,'grant_changed')

    def test_named_project_text_and_foreign_declaration(self):
        d,c,project,bodies,reader=self.synthetic();name='tools/source_release_policy_v3.py'
        for raw,good in [(b'# SPDX-License-Identifier: Apache-2.0\n',True),(b'# Copyright Unreviewed Third Party\n',False)]:
            observed={**self.observed,name:('100644',oid(raw),len(raw))}
            if good:self.assertEqual(self.checked(d,c,project,observed,lambda *a:raw)['introduced_named_project_text_files'],1)
            else:
                with self.assertRaises(p.Refused):self.checked(d,c,project,observed,lambda *a:raw)

    def test_full_observed_type_and_source_total_caps(self):
        d,c,project,bodies,reader=self.synthetic()
        for row in [('100644','1'*40,True),('120000','1'*40,0),('100644','1'*40,self.v2.MAX_FILE+1)]:
            observed={**self.observed,'tools/source_release_policy_v3.py':row}
            with self.assertRaises(p.Refused):self.checked(d,c,project,observed,reader)
        with patch.object(self.v2,'MAX_FILES',2),self.assertRaises(p.Refused):
            self.checked(d,c,project,self.observed,reader)
        with patch.object(self.v2,'MAX_TOTAL',142114657),self.assertRaises(p.Refused):
            self.checked(d,c,project,self.observed,reader)

    def test_overlay_digest_and_coherent_rebinding(self):
        d=copy.deepcopy(self.actual);d['origins'][next(iter(d['origins']))]['license']='Invented grant'
        with self.assertRaises(p.Refused) as e:p.overlay(json.dumps(d).encode(),self.base,self.v2)
        self.assertEqual(e.exception.code,'policy_changed')

    def test_typed_false_claims_candidate_flag_and_copied_fields(self):
        for mutate in [lambda d:d['claims'].update(legal_clearance=0),
                       lambda d:d['source_observation'].update(candidate_is_protected=0),
                       lambda d:d['copied_files'][0].update(bytes=True),
                       lambda d:d['origins'][next(iter(d['origins']))].update(unresolved=False),
                       lambda d:d.update(project_files=['unreviewed/name-'+str(i)+'.txt' for i in range(p.MAX_PROJECT+1)])]:
            d=copy.deepcopy(self.actual);mutate(d);raw=json.dumps(d).encode()
            with patch.object(p,'POLICY_SHA256',p.sha(raw)),self.assertRaises((ValueError,TypeError)):
                p.overlay(raw,self.base,self.v2)

    def test_one_shared_blob_budget_across_phase_uses(self):
        caps=types.SimpleNamespace(MAX_CHANGED_TEXT=8,MAX_INSPECTED_TEXT=12)
        bodies=[b'baseaa',b'copied',b'p'];calls=[]
        def git(args,limit):calls.append(args);return next(b for b in bodies if oid(b)==args[-1])
        read=p._blob_reader(caps,git,lambda:None)
        self.assertEqual(read(oid(bodies[0]),6),bodies[0]);self.assertEqual(read(oid(bodies[1]),6),bodies[1])
        self.assertEqual(read(oid(bodies[0]),6),bodies[0])  # same verified bytes need no second allocation
        with self.assertRaises(p.Refused) as e:read(oid(bodies[2]),1)
        self.assertEqual(e.exception.code,'resource_limit');self.assertEqual(len(calls),2)
        with self.assertRaises(p.Refused):read('1'*40,9)

    def test_same_tick_is_used_by_every_phase(self):
        d,c,project,bodies,reader=self.synthetic();called=[]
        def tick():called.append(True);raise p.Refused('deadline')
        with self.assertRaises(p.Refused) as e:self.checked(d,c,project,self.observed,reader,tick)
        self.assertEqual(e.exception.code,'deadline');self.assertEqual(len(called),1)

    def test_captured_v2_does_not_mutate_module_cache_or_global_policy(self):
        poisoned=types.ModuleType('tools.source_release_policy_v2');poisoned.verify=lambda **k:self.fail('module used')
        before=dict(sys.modules)
        with patch.dict(sys.modules,{'tools.source_release_policy_v2':poisoned}):
            a,_=p.pinned_v2();b,_=p.pinned_v2();self.assertIsNot(a.verify.__globals__,b.verify.__globals__)
            self.assertEqual(a.POLICY_SHA256,p.V2_POLICY_SHA256)
        self.assertEqual(set(sys.modules),set(before))

    def test_rights_refusal_precedes_archive_interpretation(self):
        with patch.object(p,'verify',return_value={'pass':False,'reason':'unknown_path'}), \
             patch.object(p,'pinned_v2',side_effect=AssertionError('binding executed')):
            r=p.verify_archive(b'not a gzip',source_commit=p.BASE)
        self.assertFalse(r['pass']);self.assertEqual(r['reason'],'unknown_path');self.assertNotIn('source_files',r)

    def archive_fixture(self):
        from scripts import source_snapshot_v3 as snapshot
        temp=tempfile.TemporaryDirectory(prefix='copy-v3-binding-');self.addCleanup(temp.cleanup)
        root=Path(temp.name).resolve()
        def git(*args):
            return subprocess.check_output(['/usr/bin/git','-C',str(root),*args],stderr=subprocess.DEVNULL)
        git('init','-q');git('config','user.name','Synthetic Engineering')
        git('config','user.email','fixture@example.invalid')
        (root/'a.txt').write_bytes(b'actual-source\n');git('add','a.txt');git('commit','-qm','Synthetic source')
        commit=git('rev-parse','HEAD').decode().strip();tree=git('rev-parse','HEAD^{tree}').decode().strip()
        raw=snapshot.build(root,commit)
        for name in [p.POLICY,self.v2.POLICY,self.v2.LEGACY,'tools/source_release_policy.py',
          'tools/source_release_policy_v2.py','tools/source_snapshot_binding.py','scripts/worker_process.py',
          'scripts/source_snapshot.py','scripts/source_snapshot_v2.py','scripts/source_snapshot_v3.py']:
            dest=root/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,dest)
        return root,commit,tree,raw,snapshot

    def invoke_archive(self,root,commit,tree,raw):
        # Isolate only source-copy classification; captured binder, child, Git and received bytes are real.
        with patch.object(p,'ROOT',root),patch.object(p,'verify',return_value={
          'pass':True,'source_tree':tree,'files':1,'source_bytes':14}):
            return p.verify_archive(raw,source_commit=commit)

    def test_real_tiny_git_archive_and_coherent_forgery(self):
        root,commit,tree,raw,snapshot=self.archive_fixture()
        result=self.invoke_archive(root,commit,tree,raw)
        self.assertTrue(result['pass'],result);self.assertTrue(result['trusted_git_bytes_matched'])
        self.assertEqual((result['source_tree'],result['source_files'],result['source_bytes']),(tree,1,14))
        for key in (*p.FALSE_CLAIMS,'signature_verified'):self.assertIs(result[key],False)
        forged_source=b'forged-source\n'
        metadata={'profile':snapshot.PROFILE,'source_commit':commit,'kind':'development_source_snapshot',
          'tag_release_validated':False,'installed_dependencies_included':False,
          'files':[{'path':'a.txt','mode':0o644,'bytes':len(forged_source),
                    'sha256':hashlib.sha256(forged_source).hexdigest()}]}
        out=io.BytesIO()
        with gzip.GzipFile(fileobj=out,mode='wb',filename='',mtime=0) as gz:
            with tarfile.open(fileobj=gz,mode='w',format=tarfile.USTAR_FORMAT) as tar:
                for name,body in [(snapshot.META,json.dumps(metadata,sort_keys=True,separators=(',',':')).encode()),
                                  ('a.txt',forged_source)]:
                    info=tarfile.TarInfo(snapshot.PREFIX+name);info.mode=0o644;info.size=len(body)
                    tar.addfile(info,io.BytesIO(body))
        forged=out.getvalue();snapshot.inspect(forged,commit)
        result=self.invoke_archive(root,commit,tree,forged)
        self.assertFalse(result['pass']);self.assertEqual(result['reason'],'archive_refused')

    def test_binding_type_tree_and_security_aliases_refuse(self):
        root,commit,tree,raw,_=self.archive_fixture()
        body={'profile':'source-snapshot-trusted-git-binding/v1','pass':True,'source_commit':commit,
          'source_tree':tree,'source_files':1,'source_bytes':14,'archive_sha256':p.sha(raw),
          'trusted_git_bytes_matched':True,'signature_verified':False,'rights_approved':False,'release_authorized':False}
        with patch.object(p,'ROOT',root):v2,v2_raw=p.pinned_v2()
        for field,value in [('pass',1),('source_tree','1'*40),('source_files',True),('source_bytes',True),
                            ('trusted_git_bytes_matched',1),('signature_verified',0),('rights_approved',0),
                            ('release_authorized',0),('source_commit','0'*40),('archive_sha256','0'*64)]:
            candidate={**body,field:value}
            with patch.object(p,'pinned_v2',return_value=(v2,v2_raw)),patch.object(
              v2,'_binding_capture',return_value=lambda *a,**k:json.dumps(candidate).encode()):
                result=self.invoke_archive(root,commit,tree,raw)
            self.assertFalse(result['pass'],field);self.assertEqual(result['reason'],'archive_refused',field)

    def test_actual_isolated_invalid_cli_has_fixed_private_diagnostics(self):
        script=str(ROOT/'tools/source_release_policy_v3.py')
        for args in [['--unknown=PRIVATE_ARGUMENT_CANARY'],['--source-commit','PRIVATE_ARGUMENT_CANARY']]:
            r=subprocess.run([sys.executable,'-I','-S','-B',script,*args],cwd='/tmp',capture_output=True,timeout=35)
            self.assertEqual(r.returncode,2);self.assertEqual(r.stderr,b'')
            self.assertNotIn(b'PRIVATE_ARGUMENT_CANARY',r.stdout);self.assertIs(json.loads(r.stdout)['pass'],False)


if __name__=='__main__':unittest.main()
