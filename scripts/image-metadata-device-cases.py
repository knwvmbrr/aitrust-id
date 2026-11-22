#!/usr/bin/env python3
"""Fixed invented bytes only; unchanged canonical parsers are the reference."""
import base64
import importlib.util
import json
from pathlib import Path
import struct
import zlib
ROOT=Path(__file__).resolve().parents[1]
COHORT=ROOT/'integrations/image-metadata-reference/1.0.0'
CANARY=b'PRIVATE_IMAGE_NAME_GPS_URL_CANARY_31'

def module(kind):
    spec=importlib.util.spec_from_file_location('reference_'+kind,COHORT/'tools'/f'{kind}_metadata.py')
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value

def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data))
def png(extra=(),color=2,depth=8,interlace=0,compressed=None):
    channels={0:1,2:3,3:1,4:2,6:4}[color]
    width=height=1 if interlace else 2
    rows=(b'\0'+b'\0'*(width*channels*(2 if depth==16 else 1)))*height
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',width,height,depth,color,0,0,interlace))+b''.join(chunk(k,v)for k,v in extra)+chunk(b'IDAT',compressed if compressed is not None else zlib.compress(rows))+chunk(b'IEND',b'')
def segment(code,data):return bytes([255,code])+(len(data)+2).to_bytes(2,'big')+data
def jpeg(extra=(),components=1,sof=0xC0,tail=b''):
    frame=b'\x08\0\x01\0\x01'+bytes([components])+b''.join(bytes([n,0x11,0])for n in range(1,components+1))
    tables=segment(0xDB,b'\0'+b'\1'*64)+segment(0xC4,bytes([0,1])+b'\0'*16+bytes([0x10,1])+b'\0'*16)
    scan=bytes([components])+b''.join(bytes([n,0])for n in range(1,components+1))+b'\0\x3f\0'
    return b'\xff\xd8'+b''.join(segment(k,v)for k,v in extra)+tables+segment(sof,frame)+segment(0xDA,scan)+bytes([(1<<(8-2*components))-1])+b'\xff\xd9'+tail

def cases():
    rows=[('png_rgb','png',png()),('png_rgba','png',png(color=6)),('png_gray','png',png(color=0)),
      ('png_private','png',png([(b'tEXt',b'Author\0'+CANARY),(b'zTXt',b'Software\0\0'+zlib.compress(CANARY)),(b'eXIf',CANARY),(b'caBX',CANARY)])),
      ('png_palette_unsupported','png',png([(b'PLTE',b'\0\0\0')],color=3)),('png_16_unsupported','png',png(depth=16)),
      ('png_interlace_unsupported','png',png(interlace=1)),('png_truncated','png',png()[:-1]),
      ('png_bad_zlib','png',png(compressed=b'not zlib')),('png_text_corrupt','png',png([(b'zTXt',b'Comment\0\0bad')])),
      ('jpeg_gray','jpeg',jpeg()),('jpeg_three','jpeg',jpeg(components=3)),
      ('jpeg_private','jpeg',jpeg([(0xE1,b'Exif\0\0'+CANARY),(0xE2,b'ICC_PROFILE\0'+CANARY),(0xEB,CANARY),(0xFE,CANARY)])),
      ('jpeg_extended_unsupported','jpeg',jpeg(sof=0xC1)),('jpeg_truncated','jpeg',jpeg()[:-1]),
      ('jpeg_trailing','jpeg',jpeg(tail=b'private trailing'))]
    result=[]
    for name,kind,raw in rows:
        m=module(kind)
        try:record=m.inspect_bytes(raw)
        except m.ImageError as e:record=m.unavailable(e.reason,raw)
        m.validate_record(record,raw)
        result.append({'id':name,'kind':kind,'bytes_base64':base64.b64encode(raw).decode(),'expected':record})
    return result
if __name__=='__main__':print(json.dumps(cases(),sort_keys=True,separators=(',',':')))
