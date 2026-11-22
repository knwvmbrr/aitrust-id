"""Supplied-label engineering controls, not independent people or accuracy."""
import contextlib
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools import mt_label_preparation as m
from tools.mt_label_io import Capture,Refused,OutputUncertain


def examples():
    return {'profile':'mt-label-items/v1','language':'en','items':[
        {'id':'PRIVATE_SOURCE_HINT_ONE','text':'Agree now or lose access.','context':'The account offers a pause option and no deadline.'},
        {'id':'PRIVATE_SOURCE_HINT_TWO','text':'Experts agree.','context':'The article quotes the phrase as an example.'},
        {'id':'PRIVATE_SOURCE_HINT_THREE','text':'Cafe\u0301 is open.','context':''}]}


def write(path,value):
    path.write_bytes(m.encode(value));path.chmod(0o600);return path


def fill(form):
    value=copy.deepcopy(form)
    for item in value['items']:
        for axis,row in item['annotations'].items():
            row.update(label=m.AXES[axis][0] if axis!='choice' else 'no_binary_frame',
                       reason='Authored synthetic judgment; no human claim.',text_spans=[[0,1]],context_spans=[])
    return value


class MTLabels(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.base=Path(self.temp.name).resolve();self.base.chmod(0o700)
        self.input=write(self.base/'input.json',examples());self.packet=self.base/'packet'
    def tearDown(self):self.temp.cleanup()
    def prepare(self):return m.freeze(self.input,self.packet)
    def forms(self):
        self.prepare()
        return [fill(json.loads((self.packet/('reviewer-'+s+'.json')).read_bytes())) for s in ('A','B')]
    def test_blank_private_packet_and_source_hints_omitted(self):
        result=self.prepare();self.assertEqual(result['state'],'PREPARED')
        self.assertEqual(stat.S_IMODE(self.packet.stat().st_mode),0o700)
        for p in self.packet.iterdir():self.assertEqual(stat.S_IMODE(p.stat().st_mode),0o600)
        for slot in ('A','B'):
            raw=(self.packet/('reviewer-'+slot+'.json')).read_bytes();self.assertNotIn(b'PRIVATE_SOURCE_HINT',raw)
            form=json.loads(raw);self.assertEqual(form['slot'],slot)
            self.assertTrue(all(a['label'] is None for r in form['items'] for a in r['annotations'].values()))
        self.assertFalse(result['predictions_run']);self.assertFalse(result['human_labels_verified'])
    def test_complete_four_axis_agreement_and_private_queue(self):
        a,b=self.forms();b['items'][0]['annotations']['pressure']['label']='uncertain'
        pa=write(self.base/'a.json',a);pb=write(self.base/'b.json',b)
        self.assertEqual(m.validate(self.input,self.packet,pa,'A')['state'],'RESPONSE_COMPLETE')
        result=m.compare(self.input,self.packet,pa,pb,self.base/'compared')
        self.assertEqual(set(result['axes']),set(m.AXES));self.assertGreater(result['private_review_queue_count'],0)
        self.assertFalse(result['release_approved']);self.assertFalse(result['accuracy_assessed'])
        self.assertNotIn('Unit000',json.dumps(result));self.assertNotIn('Authored synthetic',json.dumps(result))
        matrices=json.loads((self.base/'compared/matrices.json').read_bytes())
        for matrix in matrices.values():m.nominal_agreement(matrix)
    def test_unanimous_uncertainty_is_not_decisive_or_perfect(self):
        a,b=self.forms()
        for form in (a,b):
            for item in form['items']:
                for row in item['annotations'].values():row.update(label='uncertain',text_spans=[])
        result=m.compare(self.input,self.packet,write(self.base/'a',a),write(self.base/'b',b),self.base/'out')
        self.assertEqual(result['private_review_queue_count'],3)
        for summary in result['axes'].values():
            self.assertEqual(summary['state'],'UNAVAILABLE');self.assertIsNone(summary['alpha'])
            self.assertEqual(summary['coverage']['decisive_rating_count'],0)
            self.assertEqual(summary['coverage']['uncertain_rating_count'],6)
    def test_missing_and_uncertain_differ(self):
        a,b=self.forms();a['items'][0]['annotations']['pressure']['label']=None
        with self.assertRaises(Refused):m.validate(self.input,self.packet,write(self.base/'a',a),'A')
        a['items'][0]['annotations']['pressure']['label']='insufficient_context'
        self.assertEqual(m.validate(self.input,self.packet,write(self.base/'a',a),'A')['state'],'RESPONSE_COMPLETE')
    def test_raw_canonical_equivalent_input_edit_refuses(self):
        a,b=self.forms();value=examples();value['items'][2]['text']='Café is open.';write(self.input,value)
        with self.assertRaises(Refused):m.validate(self.input,self.packet,write(self.base/'a',a),'A')
    def test_coherent_packet_rebind_refuses_original_input(self):
        a,b=self.forms();items=json.loads((self.packet/'items.json').read_bytes());items[0]['text']='FORGED'
        write(self.packet/'items.json',items)
        manifest=json.loads((self.packet/'manifest.json').read_bytes());manifest['items_sha256']=m.sha(m.encode(items));write(self.packet/'manifest.json',manifest)
        with self.assertRaises(Refused):m.validate(self.input,self.packet,write(self.base/'a',a),'A')
    def test_unknown_fields_identity_slot_and_duplicate_refuse(self):
        a,b=self.forms();original=copy.deepcopy(a)
        variants=[]
        wrong=copy.deepcopy(a);wrong['predictions']='PRIVATE_CANARY';variants.append(wrong)
        wrong=copy.deepcopy(a);wrong['slot']='B';variants.append(wrong)
        wrong=copy.deepcopy(a);wrong['items'][0]['text']+=' changed';variants.append(wrong)
        wrong=copy.deepcopy(a);wrong['items'][1]=copy.deepcopy(wrong['items'][0]);variants.append(wrong)
        wrong=copy.deepcopy(a);wrong['items'].pop();variants.append(wrong)
        wrong=copy.deepcopy(a);wrong['items'][0]['annotations']['pressure']['confidence']=.99;variants.append(wrong)
        for wrong in variants:
            with self.assertRaises(Refused):m.validate(self.input,self.packet,write(self.base/'a',wrong),'A')
    def test_typed_frozen_identity_cannot_be_boolean_or_float(self):
        a,b=self.forms()
        for value in (False,0.0):
            wrong=copy.deepcopy(a);row=next(x for x in wrong['items'] if x['context']=='')
            row['context_identity']['raw_codepoints']=value
            with self.assertRaises(Refused):m.validate(self.input,self.packet,write(self.base/'a',wrong),'A')
    def test_descriptor_count_refuses_before_open(self):
        c=Capture();c.fds=[None]*256
        with mock.patch('tools.mt_label_io.os.open') as opened:
            with self.assertRaises(Refused):c.parent(self.input,True)
            opened.assert_not_called()
        c.fds=[]
    def test_unexpected_packet_member_refuses_before_response(self):
        a,b=self.forms();write(self.packet/'predictions.json',{'prediction':'SYNTHETIC_ONLY'})
        with self.assertRaises(Refused):m.validate(self.input,self.packet,write(self.base/'a',a),'A')
    def test_span_types_bounds_and_context_anchor(self):
        a,b=self.forms()
        for span in ([False,1],[-1,1],[0,9000],[0,0]):
            value=copy.deepcopy(a);value['items'][0]['annotations']['pressure']['text_spans']=[span]
            with self.assertRaises(Refused):m.validate(self.input,self.packet,write(self.base/'a',value),'A')
        a['items'][0]['annotations']['choice'].update(label='binary_omits_alternative',text_spans=[[0,1]],context_spans=[])
        with self.assertRaises(Refused):m.validate(self.input,self.packet,write(self.base/'a',a),'A')
    def test_source_change_refuses_without_detector(self):
        a,b=self.forms();state=m.source_state
        def forged(capture):return {**state(capture),'tools/reviewer_agreement.py':'0'*64}
        with mock.patch.object(m,'source_state',side_effect=forged):
            with self.assertRaises(Refused):m.validate(self.input,self.packet,write(self.base/'a',a),'A')
    def test_nonprivate_links_fifo_and_size_before_read(self):
        self.input.chmod(0o644)
        with self.assertRaises(Refused):m.freeze(self.input,self.packet)
        self.input.chmod(0o600);link=self.base/'linked';link.symlink_to(self.input)
        with self.assertRaises((Refused,OSError)):m.freeze(link,self.packet)
        fifo=self.base/'fifo';os.mkfifo(fifo,0o600)
        with self.assertRaises(Refused):m.freeze(fifo,self.packet)
        large=self.base/'large';large.write_bytes(b'X'*(m.INPUT_LIMIT+1));large.chmod(0o600)
        with mock.patch('tools.mt_label_io.os.read',side_effect=AssertionError('must not read')):
            with Capture() as capture:
                with self.assertRaises(Refused):capture.read(large,m.INPUT_LIMIT)
    def test_nooverwrite_preserves_existing_packet(self):
        self.prepare();before={p.name:p.read_bytes() for p in self.packet.iterdir()}
        with self.assertRaises(FileExistsError):m.freeze(self.input,self.packet)
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.packet.iterdir()})
    def test_constructor_fault_raw_fd_owned_and_cleanup_uncertain(self):
        real=os.close;closed=[]
        def close(fd):closed.append(fd);return real(fd)
        with mock.patch('tools.mt_label_io.os.fdopen',side_effect=OSError('PRIVATE_CANARY')),mock.patch('tools.mt_label_io.os.close',side_effect=close):
            with self.assertRaises(OutputUncertain):
                with Capture() as capture:capture.create(self.base/'new',{'a.json':b'{}'})
        self.assertEqual(len(closed),len(set(closed)))
        for fd in closed:
            with self.assertRaises(OSError):os.fstat(fd)
    def test_close_after_real_release_never_retries_reused_descriptor(self):
        c=Capture();c.read(self.input,m.INPUT_LIMIT);real=os.close;calls=[];marker=[]
        def close(fd):
            calls.append(fd);real(fd)
            if len(calls)==1:marker.append(os.open(self.input,os.O_RDONLY));raise OSError('PRIVATE_CANARY')
        with mock.patch('tools.mt_label_io.os.close',side_effect=close):
            with self.assertRaises(Refused):c.close()
        self.assertEqual(len(calls),len(set(calls)));os.fstat(marker[0]);os.close(marker[0]);c.close()
    def test_late_git_marker_prepublication_refuses(self):
        with self.assertRaises(Refused):
            with Capture() as capture:
                capture.read(self.input,m.INPUT_LIMIT)
                (self.base/'.git').write_text('synthetic marker only')
                capture.check()
        self.assertFalse((self.base/'new').exists())
    def test_late_git_marker_postpublication_exit_is_uncertain(self):
        with self.assertRaises(OutputUncertain):
            with Capture() as capture:
                capture.create(self.base/'new',{'a.json':b'{}'})
                (self.base/'.git').write_text('synthetic marker only')
                # Exit must check even if the caller performs no explicit check.
        self.assertEqual((self.base/'new/a.json').read_bytes(),b'{}')
    def test_reserved_git_destination_refuses_before_creation_and_positive_recovers(self):
        with Capture() as capture:
            with self.assertRaises(Refused):capture.create(self.base/'.git',{'a.json':b'{}'})
        self.assertFalse((self.base/'.git').exists())
        with Capture() as capture:capture.create(self.base/'new',{'a.json':b'{}'})
        self.assertEqual((self.base/'new/a.json').read_bytes(),b'{}')
    def test_final_close_uncertainty_visible_and_output_retained(self):
        c=Capture();real=os.close;calls=[]
        def close(fd):
            calls.append(fd);real(fd)
            if len(calls)==1:raise OSError('PRIVATE_CANARY')
        with mock.patch('tools.mt_label_io.os.close',side_effect=close):
            with self.assertRaises(OutputUncertain):
                with c:c.create(self.base/'new',{'a.json':b'{}'})
        self.assertEqual((self.base/'new/a.json').read_bytes(),b'{}');self.assertEqual(len(calls),len(set(calls)))
    def test_json_duplicate_nonfinite_depth_and_encoder_boundary(self):
        for raw in (b'{"a":1,"a":2}',b'{"a":NaN}',b'{"a":1e999}',b'['*30+b'0'+b']'*30):
            with self.assertRaises(Refused):m.decode(raw)
        self.assertEqual(m.encode({},3),b'{}\n')
        with self.assertRaises(Refused):m.encode({},2)
    def test_returned_matrices_do_not_mutate_candidate_categories(self):
        items,_,manifest=m.prepared(self.input.read_bytes(),{})
        a=m.response(m.encode(fill(m.blank(items,manifest,'A'))),items,manifest,'A')
        b=m.response(m.encode(fill(m.blank(items,manifest,'B'))),items,manifest,'B')
        _,matrices,_=m.agreement(items,a,b);saved=copy.deepcopy(m.AXES)
        matrices['pressure']['categories'].append('FORGED');self.assertEqual(m.AXES,saved)
    def test_actual_cli_refusal_has_no_private_canary_or_path(self):
        result=subprocess.run([sys.executable,'-I','-S','-B',str(ROOT/'scripts/mt-label-preparation.py'),
            'prepare','--items',str(self.base/'PRIVATE_CANARY'),'--out',str(self.packet)],capture_output=True,timeout=5)
        self.assertEqual(result.returncode,2);self.assertFalse(result.stderr)
        self.assertNotIn(b'PRIVATE_CANARY',result.stdout);self.assertNotIn(str(self.base).encode(),result.stdout)
        self.assertEqual(json.loads(result.stdout)['state'],'UNAVAILABLE')


if __name__=='__main__':unittest.main()
