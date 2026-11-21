"""Synthetic-only PNG facts, strict failures and real isolated CLI controls."""
import copy
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import zlib
from tools import png_metadata as p
ROOT=Path(__file__).resolve().parents[1]
CANARY='PRIVATE_PNG_AUTHOR_DO_NOT_SHARE_17'

def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data))
def image(extra=(),width=2,height=2,color=2,depth=8,interlace=0,scanlines=None,compressed=None):
    channels={0:1,2:3,3:1,4:2,6:4}.get(color,3)
    rows=scanlines if scanlines is not None else(b'\0'+bytes([33])*(width*channels))*height
    return p.SIGNATURE+chunk(b'IHDR',struct.pack('>IIBBBBB',width,height,depth,color,0,0,interlace))+b''.join(chunk(k,v)for k,v in extra)+chunk(b'IDAT',compressed if compressed is not None else zlib.compress(rows))+chunk(b'IEND',b'')

class Metadata(unittest.TestCase):
    def test_plain_compressed_international_and_opaque_sections_are_private(self):
        raw=image([(b'tEXt',b'Author\0'+CANARY.encode()),(b'zTXt',b'Software\0\0'+zlib.compress(b'SYNTHETIC AI EDITOR')),(b'iTXt',b'XML:com.adobe.xmp\0\0\0en\0\0'+('<x>'+CANARY+'</x>').encode()),(b'eXIf',b'opaque private GPS '+CANARY.encode()),(b'caBX',b'not a verified manifest')])
        r=p.inspect_bytes(raw);self.assertEqual(r['image'],{'width':2,'height':2,'bit_depth':8,'color':'RGB'});self.assertEqual(r['asset_sha256'],hashlib.sha256(raw).hexdigest());self.assertEqual(r['text_categories'],{'author':1,'software':1,'description':0,'copyright':0,'XMP':1,'other':0});self.assertEqual(r['metadata_sections']['EXIF_section'],1);self.assertEqual(r['metadata_sections']['C2PA_section'],1)
        for output in [json.dumps(r),p.text_result(r)]:
            self.assertNotIn(CANARY,output);self.assertNotIn('SYNTHETIC AI EDITOR',output);self.assertNotIn('opaque private GPS',output)
        self.assertEqual(r['AI_origin'],'unknown');self.assertFalse(r['watermark_verified']);self.assertFalse(r['C2PA_inspected']);self.assertEqual(r['tags'],[])
    def test_no_metadata_is_not_human_or_AI_origin(self):
        r=p.inspect_bytes(image());self.assertEqual(sum(r['metadata_sections'].values()),0);self.assertEqual(r['AI_origin'],'unknown');self.assertFalse(r['content_truth_established']);self.assertIn('Other identifying information may still be present',p.text_result(r))
    def test_all_supported_color_types_and_filter_bytes(self):
        for color,channels in [(0,1),(2,3),(4,2),(6,4)]:
            for filter_byte in range(5):
                r=p.inspect_bytes(image(width=1,height=1,color=color,scanlines=bytes([filter_byte])+b'\0'*channels));self.assertEqual(r['state'],'OBSERVED')
    def test_valid_unsupported_variants_are_not_corrupt(self):
        # These three fixtures are valid for their unsupported PNG profiles.
        variants=[image(depth=16,scanlines=(b'\0'+b'\0'*12)*2),image(extra=[(b'PLTE',b'\0\0\0')],color=3,scanlines=(b'\0\0\0')*2),image(width=1,height=1,interlace=1)]
        for raw in variants:
            with self.assertRaises(p.ImageError)as e:p.inspect_bytes(raw)
            self.assertEqual(e.exception.reason,'unsupported_variant')
        for kind in [b'acTL',b'fcTL',b'fdAT',b'ABCD']:
            with self.assertRaises(p.ImageError)as e:p.inspect_bytes(image([(kind,b'\0'*8)]))
            self.assertEqual(e.exception.reason,'unsupported_variant')
        with self.assertRaises(p.ImageError)as e:p.inspect_bytes(b'\xff\xd8\xff JPEG')
        self.assertEqual(e.exception.reason,'unsupported_format')
    def test_structural_CRC_trailing_and_order_damage(self):
        source=image();cases=[source[:-1],source+b'private',source[:30]+bytes([source[30]^1])+source[31:],p.SIGNATURE+chunk(b'IDAT',b'')+source[8:],source[:-12]+chunk(b'tEXt',b'Comment\0a')+chunk(b'IDAT',b'')+source[-12:]]
        for raw in cases:
            with self.assertRaises(p.ImageError)as e:p.inspect_bytes(raw)
            self.assertEqual(e.exception.reason,'corrupt_container')
    def test_image_zlib_corruption_lengths_filters_and_trailing_stream(self):
        for compressed in [b'not zlib',zlib.compress(b'\0x'),zlib.compress(b'\5'+b'\0'*12),zlib.compress(b'\0'+b'\0'*6)*2,zlib.compress(b'\0'+b'\0'*6)+b'junk',zlib.compress(b'x'*1000000)]:
            with self.assertRaises(p.ImageError)as e:p.inspect_bytes(image(compressed=compressed))
            self.assertEqual(e.exception.reason,'corrupt_image_data')
    def test_text_corruption_and_inflate_limits(self):
        cases=[(b'tEXt',b' Author\0x'),(b'tEXt',b'Author\0x\0y'),(b'zTXt',b'Comment\0\1x'),(b'zTXt',b'Comment\0\0broken'),(b'iTXt',b'Comment\0\0\0en\0\0\xff')]
        for x in cases:
            with self.assertRaises(p.ImageError)as e:p.inspect_bytes(image([x]))
            self.assertEqual(e.exception.reason,'corrupt_text_metadata')
        for raw in [image([(b'zTXt',b'Comment\0\0'+zlib.compress(b'a'*(p.MAX_TEXT+1)))]),image([(b'tEXt',b'Comment\0x')]*(p.MAX_TEXT_FIELDS+1)),image([(b'abCD',b'x'*(p.MAX_METADATA+1))])]:
            with self.assertRaises(p.ImageError)as e:p.inspect_bytes(raw)
            self.assertEqual(e.exception.reason,'metadata_limit')
    def test_size_pixel_chunk_and_integer_limits(self):
        for raw in [b'x'*(p.MAX_INPUT+1),image(width=p.MAX_PIXELS+1,height=1,scanlines=b'\0x')]:
            with self.assertRaises(p.ImageError)as e:p.inspect_bytes(raw)
            self.assertEqual(e.exception.reason,'input_limit')
        with patch.object(p,'MAX_CHUNKS',3):
            with self.assertRaises(p.ImageError)as e:p.inspect_bytes(image([(b'abCD',b'')]))
            self.assertEqual(e.exception.reason,'input_limit')
        with self.assertRaises(p.ImageError):p.inspect_bytes(bytearray(image()))
    def test_closed_worker_result_and_exact_subject_header_binding(self):
        raw=image();r=p.inspect_bytes(raw);self.assertEqual(p.validate_record(r,raw),r)
        changed=[]
        q=copy.deepcopy(r);q['raw_input']=CANARY;changed.append(q)
        q=copy.deepcopy(r);q['image']['width']=1;changed.append(q)
        q=copy.deepcopy(r);q['asset_sha256']='0'*64;changed.append(q)
        q=copy.deepcopy(r);q['metadata_sections']['plain_text']=True;changed.append(q)
        q=copy.deepcopy(r);q['AI_origin']='AI';changed.append(q)
        q=copy.deepcopy(r);q['tags']=['FA'];changed.append(q)
        q=copy.deepcopy(r);q['text_categories']['author']=1;changed.append(q)
        for q in changed:
            with self.assertRaises(p.ImageError):p.validate_record(q,raw)
        q=copy.deepcopy(r);q['image']['color']=CANARY
        with self.assertRaises(p.ImageError):p.text_result(q)
    def test_actual_stdlib_only_CLI_default_privacy_JSON_and_error_recovery(self):
        with tempfile.TemporaryDirectory()as d:
            root=Path(d).resolve();path=root/(CANARY+'.png');raw=image([(b'tEXt',b'Author\0'+CANARY.encode())]);path.write_bytes(raw)
            for mode in ['text','json']:
                r=subprocess.run([sys.executable,'-I','-S','-B',str(ROOT/'scripts/inspect-png-metadata.py'),'--image',str(path),'--format',mode],capture_output=True,timeout=7);self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(r.stderr,b'');self.assertNotIn(CANARY.encode(),r.stdout)
                if mode=='json':self.assertEqual(json.loads(r.stdout)['asset_sha256'],hashlib.sha256(raw).hexdigest())
                else:self.assertNotIn(hashlib.sha256(raw).hexdigest().encode(),r.stdout)
            path.write_bytes(image(compressed=b'broken'))
            r=subprocess.run([sys.executable,'-I','-S','-B',str(ROOT/'scripts/inspect-png-metadata.py'),'--image',str(path),'--format','json'],capture_output=True,timeout=7);self.assertEqual(r.returncode,2);self.assertEqual(json.loads(r.stdout)['reason'],'corrupt_image_data');self.assertNotIn('metadata_sections',json.loads(r.stdout))
            path.write_bytes(image());self.assertEqual(p.inspect_file(path)['state'],'OBSERVED')
    def test_missing_symlink_FIFO_and_drift_never_echo_a_path(self):
        with tempfile.TemporaryDirectory()as d:
            root=Path(d).resolve();source=root/'source.png';source.write_bytes(image());link=root/'link';link.symlink_to(source);fifo=root/'pipe';os.mkfifo(fifo)
            for path in [root/CANARY,link,fifo]:
                with self.assertRaises(p.ImageError)as e:p.inspect_file(path)
                self.assertEqual(e.exception.reason,'source_unavailable');self.assertNotIn(str(path),str(e.exception))
            real=os.read;mutated=[]
            def read(fd,n):
                b=real(fd,n)
                if not mutated:source.write_bytes(image([(b'tEXt',b'Comment\0changed')]));mutated.append(True)
                return b
            with patch.object(os,'read',side_effect=read):
                with self.assertRaises(p.ImageError)as e:p.inspect_file(source)
            self.assertEqual(e.exception.reason,'source_unavailable')
    def test_real_owned_worker_timeout_output_and_nonzero_refusal_reap(self):
        real=subprocess.Popen
        with tempfile.TemporaryDirectory()as d:
            source=Path(d).resolve()/'image.png';source.write_bytes(image());children=[]
            def launched(program):
                def make(args,**kwargs):
                    child=real([sys.executable,'-I','-S','-c',program],**kwargs);children.append(child);return child
                return make
            for program in ['import time;time.sleep(20)','import sys;sys.stdout.buffer.write(b"x"*9000)','raise SystemExit(3)']:
                with patch.object(p.subprocess,'Popen',side_effect=launched(program)),patch.object(p,'WALL_SECONDS',.08):
                    with self.assertRaises(p.ImageError):p.inspect_file(source)
                self.assertIsNotNone(children[-1].returncode)
    def test_known_reaped_worker_is_not_signaled_after_wait_error(self):
        real=subprocess.Popen;children=[]
        with tempfile.TemporaryDirectory()as d:
            source=Path(d).resolve()/'image.png';source.write_bytes(image())
            def make(args,**kwargs):
                child=real(args,**kwargs);children.append(child);wait=child.wait
                def postwait(*a,**kw):
                    wait(*a,**kw)
                    raise OSError('SYNTHETIC_POST_REAP_FAILURE')
                child.wait=postwait
                return child
            with patch.object(p.subprocess,'Popen',side_effect=make),patch.object(p.os,'killpg')as kill:
                with self.assertRaises(p.ImageError):p.inspect_file(source)
            self.assertEqual(children[0].returncode,0)
            kill.assert_not_called()

    def test_bad_image_does_not_disable_existing_PS(self):
        r=subprocess.run([sys.executable,'-I','-S','-B',str(ROOT/'scripts/check-ps.py'),'--json'],input=b'An ordinary sentence.',capture_output=True,timeout=12)
        self.assertEqual(r.returncode,0,r.stderr);self.assertNotIn(CANARY.encode(),r.stdout)
if __name__=='__main__':unittest.main()
