"""Synthetic JPEG framing and actual isolated CLI; no pixel-origin claims."""
import copy
import hashlib
import importlib.util
from types import SimpleNamespace
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from tools import jpeg_metadata as j
ROOT=Path(__file__).resolve().parents[1]
CANARY='SYNTHETIC_PRIVATE_JPEG_NAME_GPS_URL_27'

def segment(code,data):return bytes([255,code])+len(data+ b'00').to_bytes(2,'big')+data

def jpeg(metadata=(),components=1,sof=0xC0,width=1,height=1,entropy=None,interval=0,tail_metadata=(),tables=True):
    frame=bytes([8])+height.to_bytes(2,'big')+width.to_bytes(2,'big')+bytes([components])+b''.join(bytes([n,0x11,0])for n in range(1,components+1))
    dc=bytes([0,1])+b'\0'*15+b'\0';ac=bytes([0x10,1])+b'\0'*15+b'\0'
    headers=segment(0xDB,b'\0'+b'\1'*64)+segment(0xC4,dc+ac)if tables else b''
    scan=bytes([components])+b''.join(bytes([n,0])for n in range(1,components+1))+b'\0\x3f\0'
    data=entropy if entropy is not None else bytes([(1<<(8-2*components))-1])
    return b'\xff\xd8'+b''.join(segment(k,v)for k,v in metadata)+headers+segment(sof,frame)+(segment(0xDD,interval.to_bytes(2,'big'))if interval else b'')+segment(0xDA,scan)+data+b''.join(segment(k,v)for k,v in tail_metadata)+b'\xff\xd9'

class JPEG(unittest.TestCase):
    def test_minimal_baseline_dimensions_and_three_components_no_color_claim(self):
        for count in (1,3):
            raw=jpeg(components=count);r=j.inspect_bytes(raw);self.assertEqual(r['image'],{'width':1,'height':1,'precision':8,'components':count});self.assertEqual(r['asset_sha256'],hashlib.sha256(raw).hexdigest());self.assertEqual(r['AI_origin'],'unknown');self.assertEqual(r['tags'],[]);self.assertFalse(r['pixels_decoded']);self.assertFalse(r['entropy_framing']['MCU_intervals_verified']);self.assertNotIn('color',r['image']);self.assertEqual(j.validate_record(r,raw),r)
    def test_private_opaque_sections_before_and_after_scan(self):
        metadata=[(0xE1,b'Exif\0\0'+CANARY.encode()),(0xE1,b'http://ns.adobe.com/xap/1.0/\0'+CANARY.encode()),(0xE2,b'ICC_PROFILE\0'+CANARY.encode()),(0xE0,b'JFIF\0'+CANARY.encode()),(0xEB,CANARY.encode()),(0xE3,CANARY.encode())]
        raw=jpeg(metadata,tail_metadata=[(0xFE,CANARY.encode())]);r=j.inspect_bytes(raw);self.assertEqual(r['metadata_sections'],dict.fromkeys(j.META_KEYS,1));self.assertFalse(r['C2PA_inspected']);self.assertFalse(r['watermark_verified']);self.assertFalse(r['content_truth_established'])
        for out in (json.dumps(r),j.text_result(r)):self.assertNotIn(CANARY,out)
        self.assertNotIn(hashlib.sha256(raw).hexdigest(),j.text_result(r))
    def test_valid_unsupported_profiles_abbreviated_and_trailing_data(self):
        for raw in [jpeg(components=4),jpeg(sof=0xC1),jpeg(tables=False),jpeg(height=0,tail_metadata=[(0xDC,b'\0\1')])]:
            with self.assertRaises(j.ImageError)as e:j.inspect_bytes(raw)
            self.assertEqual(e.exception.reason,'unsupported_variant')
        with self.assertRaises(j.ImageError)as e:j.inspect_bytes(jpeg()+jpeg())
        self.assertEqual(e.exception.reason,'trailing_data')
        with self.assertRaises(j.ImageError)as e:j.inspect_bytes(b'not JPEG')
        self.assertEqual(e.exception.reason,'unsupported_format')
    def test_truncated_lengths_marker_order_and_invalid_tables_refuse(self):
        raw=jpeg();bad=[raw[:-1],raw[:-2],b'\xff\xd8\xff\xe1\0\1',b'\xff\xd8\xff\xe1\xff\xffx',raw[:2]+segment(0xDB,b'\0'+b'\0'*64)+raw[2:],raw[:2]+segment(0xC4,b'\0'+b'\2'+b'\0'*15+b'\0\1')+raw[2:],raw[:2]+b'\xff\xd8'+raw[2:],raw[:2]+b'\xff\xd0'+raw[2:],raw[:2]+b'\xff\0'+raw[2:]]
        for value in bad:
            with self.assertRaises(j.ImageError):j.inspect_bytes(value)
    def test_entropy_framing_stuffing_and_restart_limits_not_decoding(self):
        r=j.inspect_bytes(jpeg(entropy=b'\xff\0'));self.assertEqual(r['entropy_framing']['data_bytes'],1);self.assertFalse(r['entropy_framing']['decoded'])
        raw=jpeg(width=16,height=8,interval=1,entropy=b'\x3f\xff\xd0\x3f');self.assertEqual(j.inspect_bytes(raw)['entropy_framing']['restart_markers'],1)
        for value in [jpeg(entropy=b''),jpeg(entropy=b'\xff'),jpeg(entropy=b'\x3f\xff\xd0\x3f'),jpeg(interval=1,entropy=b'\x3f\xff\xd1\x3f'),jpeg(interval=1,entropy=b'\x3f\xff\xd0\xff\xd1\x3f'),jpeg(interval=1,entropy=b'\x3f\xff\xd0')]:
            with self.assertRaises(j.ImageError):j.inspect_bytes(value)
    def test_resource_caps_are_before_unbounded_metadata_or_iteration(self):
        for raw,reason in [(b'x'*(j.MAX_INPUT+1),'input_limit'),(jpeg(width=65535,height=65535),'input_limit'),(jpeg([(0xFE,b'')]*129),'metadata_limit'),(jpeg([(0xE1,b'x'*65533)]*5),'metadata_limit')]:
            with self.assertRaises(j.ImageError)as e:j.inspect_bytes(raw)
            self.assertEqual(e.exception.reason,reason)
        with patch.object(j,'MAX_MARKERS',3):
            with self.assertRaises(j.ImageError)as e:j.inspect_bytes(jpeg())
            self.assertEqual(e.exception.reason,'input_limit')
        with patch.object(j,'MAX_TABLES',1):
            with self.assertRaises(j.ImageError)as e:j.inspect_bytes(jpeg())
            self.assertEqual(e.exception.reason,'input_limit')
    def test_closed_exact_result_refuses_raw_values_counts_identity_and_tags(self):
        raw=jpeg();r=j.inspect_bytes(raw)
        for fault in ['extra','hash','count','image','origin','tags','decoded','boolean']:
            v=copy.deepcopy(r)
            if fault=='extra':v['raw_metadata']=CANARY
            elif fault=='hash':v['asset_sha256']='0'*64
            elif fault=='count':v['metadata_sections']['comment']=1
            elif fault=='image':v['image']['width']=2
            elif fault=='origin':v['AI_origin']='human'
            elif fault=='tags':v['tags']=['FA']
            elif fault=='decoded':v['entropy_framing']['decoded']=True
            else:v['marker_count']=True
            with self.assertRaises(j.ImageError):j.validate_record(v,raw)
        r['tags'].append('FA');self.assertEqual(j.inspect_bytes(raw)['tags'],[])
    def test_actual_CLI_default_privacy_JSON_unsupported_failure_recovery(self):
        with tempfile.TemporaryDirectory()as d:
            path=Path(d).resolve()/(CANARY+'.jpg');raw=jpeg([(0xFE,CANARY.encode())]);path.write_bytes(raw)
            for mode in ('text','json'):
                result=subprocess.run([sys.executable,'-I','-S','-B',str(ROOT/'scripts/inspect-jpeg-metadata.py'),'--image',str(path),'--format',mode],capture_output=True,timeout=7);self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(result.stderr,b'');self.assertNotIn(CANARY.encode(),result.stdout)
                if mode=='json':self.assertEqual(json.loads(result.stdout)['asset_sha256'],hashlib.sha256(raw).hexdigest())
                else:self.assertNotIn(hashlib.sha256(raw).hexdigest().encode(),result.stdout)
            for raw,reason in [(jpeg(components=4),'unsupported_variant'),(jpeg()[:-1],'malformed_structure')]:
                path.write_bytes(raw);result=subprocess.run([sys.executable,'-I','-S','-B',str(ROOT/'scripts/inspect-jpeg-metadata.py'),'--image',str(path),'--format','json'],capture_output=True,timeout=7);self.assertEqual(result.returncode,2);self.assertEqual(json.loads(result.stdout)['reason'],reason);self.assertNotIn(CANARY.encode(),result.stdout+result.stderr)
            path.write_bytes(jpeg());self.assertEqual(j.inspect_file(path)['state'],'OBSERVED')
    def test_implementation_digest_is_bounded_and_does_not_follow_links(self):
        spec=importlib.util.spec_from_file_location('jpeg_cli_test',ROOT/'scripts/inspect-jpeg-metadata.py');cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)
        with tempfile.TemporaryDirectory()as d:
            root=Path(d).resolve();source=root/'source';source.write_bytes(b'owned code');link=root/'link';link.symlink_to(source);fifo=root/'fifo';os.mkfifo(fifo);large=root/'large';large.write_bytes(b'x'*1_000_001)
            self.assertEqual(cli.implementation_digest(SimpleNamespace(__file__=source,identity=j.identity)),hashlib.sha256(b'owned code').hexdigest())
            for selected in (link,fifo,large):
                with self.assertRaises((ValueError,OSError)):cli.implementation_digest(SimpleNamespace(__file__=selected,identity=j.identity))

    def test_no_follow_parent_leaf_FIFO_and_exact_opened_subject_drift(self):
        with tempfile.TemporaryDirectory()as d:
            root=Path(d).resolve();path=root/'image';path.write_bytes(jpeg());leaf=root/'link';leaf.symlink_to(path);parent=root/'parent-link';parent.symlink_to(root,target_is_directory=True);fifo=root/'pipe';os.mkfifo(fifo)
            for value in [leaf,parent/'image',fifo,root/'missing']:
                with self.assertRaises(j.ImageError)as e:j.inspect_file(value)
                self.assertEqual(e.exception.reason,'source_unavailable')
            read=os.read;changed=[]
            def drift(fd,n):
                value=read(fd,n)
                if not changed:path.write_bytes(jpeg([(0xFE,b'changed')]));changed.append(True)
                return value
            with patch.object(os,'read',side_effect=drift):
                with self.assertRaises(j.ImageError)as e:j.inspect_file(path)
                self.assertEqual(e.exception.reason,'source_unavailable')
    def test_actual_worker_timeout_overflow_nonzero_and_known_reaped_ownership(self):
        real=subprocess.Popen;children=[]
        with tempfile.TemporaryDirectory()as d:
            path=Path(d).resolve()/'image';path.write_bytes(jpeg())
            def launch(program,postwait=False):
                def make(args,**kwargs):
                    self.assertEqual(args,[sys.executable,'-I','-S','-B',str(ROOT/'scripts/inspect-jpeg-metadata.py'),'--worker'])
                    self.assertIsInstance(kwargs['stdin'],int)
                    child=real([sys.executable,'-I','-S','-c',program],**kwargs);children.append(child)
                    if postwait:
                        wait=child.wait
                        def complete(*a,**kw):wait(*a,**kw);raise OSError('SYNTHETIC_POSTWAIT')
                        child.wait=complete
                    return child
                return make
            for program in ['import time;time.sleep(20)','import sys;sys.stdout.buffer.write(b"x"*9000)','raise SystemExit(3)']:
                with patch.object(j.subprocess,'Popen',side_effect=launch(program)),patch.object(j,'WALL_SECONDS',.08):
                    with self.assertRaises(j.ImageError):j.inspect_file(path)
                self.assertIsNotNone(children[-1].returncode)
            with patch.object(j.subprocess,'Popen',side_effect=launch('print("{}")',True)),patch.object(j.os,'killpg')as kill:
                with self.assertRaises(j.ImageError):j.inspect_file(path)
                self.assertEqual(children[-1].returncode,0);kill.assert_not_called()
if __name__=='__main__':unittest.main()
