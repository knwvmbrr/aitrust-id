"""Bounded local PNG metadata facts; no image-origin, watermark or truth verdict."""
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import signal
import stat
import struct
import subprocess
import sys
import tempfile
import time
import zlib

PROFILE='png-metadata-preflight/1.0.0'
MAX_INPUT=10*1024*1024
MAX_PIXELS=4_000_000
MAX_EXPANDED=32*1024*1024
MAX_METADATA=256*1024
MAX_TEXT=64*1024
MAX_TEXT_FIELDS=128
MAX_CHUNKS=4096
MAX_OUTPUT=8192
WALL_SECONDS=4
ROOT=Path(__file__).resolve().parents[1]
SIGNATURE=b'\x89PNG\r\n\x1a\n'
COLORS={0:('grayscale',1),2:('RGB',3),4:('grayscale_alpha',2),6:('RGBA',4)}
REASONS={'unsupported_format','unsupported_variant','corrupt_container','corrupt_image_data','corrupt_text_metadata','input_limit','metadata_limit','source_unavailable','worker_unavailable','invalid_request'}
META_KEYS=('plain_text','compressed_text','international_text','EXIF_section','ICC_section','C2PA_section','time_section','other_ancillary_sections')
CATEGORIES=('author','software','description','copyright','XMP','other')

class ImageError(ValueError):
    def __init__(self,reason):
        self.reason=reason if reason in REASONS else 'worker_unavailable'
        super().__init__(self.reason)

def need(condition,reason):
    if not condition:raise ImageError(reason)

def inflate(raw,limit,reason):
    try:
        d=zlib.decompressobj();value=d.decompress(raw,limit+1)
        need(len(value)<=limit, 'metadata_limit'if reason=='corrupt_text_metadata'else reason)
        need(d.eof and not d.unused_data and not d.unconsumed_tail,reason)
        return value
    except zlib.error:raise ImageError(reason)from None

def keyword(raw):
    need(1<=len(raw)<=79 and all(32<=x<=126 or 161<=x<=255 for x in raw)and not raw.startswith(b' ')and not raw.endswith(b' ')and b'  'not in raw,'corrupt_text_metadata')
    return raw

def text_info(kind,data,remaining):
    need(b'\0'in data,'corrupt_text_metadata');key,rest=data.split(b'\0',1);keyword(key)
    if kind==b'tEXt':value=rest;encoding='latin-1'
    elif kind==b'zTXt':
        need(rest[:1]==b'\0','corrupt_text_metadata');value=inflate(rest[1:],min(MAX_TEXT,remaining),'corrupt_text_metadata');encoding='latin-1'
    else:
        need(len(rest)>=2 and rest[0]in(0,1)and rest[1]==0,'corrupt_text_metadata');flag=rest[0];parts=rest[2:].split(b'\0',2);need(len(parts)==3,'corrupt_text_metadata');language,translated,value=parts
        need(len(language)<=79 and re.fullmatch(b'[A-Za-z0-9-]*',language)is not None,'corrupt_text_metadata')
        try:translated.decode('utf-8','strict')
        except UnicodeError:raise ImageError('corrupt_text_metadata')from None
        if flag:value=inflate(value,min(MAX_TEXT,remaining),'corrupt_text_metadata')
        encoding='utf-8'
    need(len(value)<=min(MAX_TEXT,remaining),'metadata_limit')
    try:value.decode(encoding,'strict')
    except UnicodeError:raise ImageError('corrupt_text_metadata')from None
    need(b'\0'not in value,'corrupt_text_metadata')
    category={b'Author':'author',b'Software':'software',b'Description':'description',b'Comment':'description',b'Copyright':'copyright',b'XML:com.adobe.xmp':'XMP'}.get(key,'other')
    return category,len(value)

def inspect_bytes(raw):
    need(type(raw)is bytes,'invalid_request');need(len(raw)<=MAX_INPUT,'input_limit');need(raw.startswith(SIGNATURE),'unsupported_format')
    offset=8;count=0;idat=bytearray();after_idat=False;started=False;ended=False;palette=False
    metadata=dict.fromkeys(META_KEYS,0);categories=dict.fromkeys(CATEGORIES,0);stored=expanded=0;text_fields=0;header=None
    while offset+12<=len(raw):
        need(count<MAX_CHUNKS,'input_limit');size=struct.unpack('>I',raw[offset:offset+4])[0];kind=raw[offset+4:offset+8];end=offset+12+size
        need(size<=MAX_INPUT and end<=len(raw)and re.fullmatch(b'[A-Za-z]{4}',kind)is not None,'corrupt_container')
        need(not(kind[2]&32),'unsupported_variant');data=raw[offset+8:end-4]
        need(zlib.crc32(kind+data)==struct.unpack('>I',raw[end-4:end])[0],'corrupt_container')
        if count==0:
            need(kind==b'IHDR'and size==13,'corrupt_container');width,height,depth,color,compression,filtering,interlace=struct.unpack('>IIBBBBB',data)
            need(width>0 and height>0,'corrupt_container');need(width*height<=MAX_PIXELS,'input_limit')
            need(depth==8 and color in COLORS and compression==0 and filtering==0 and interlace==0,'unsupported_variant')
            header={'width':width,'height':height,'bit_depth':depth,'color':COLORS[color][0]}
        elif kind==b'IHDR':raise ImageError('corrupt_container')
        if kind in (b'acTL',b'fcTL',b'fdAT'):raise ImageError('unsupported_variant')
        if kind==b'IDAT':
            need(not after_idat,'corrupt_container');started=True;need(len(idat)+size<=MAX_INPUT,'input_limit');idat.extend(data)
        elif started:after_idat=True
        if kind==b'PLTE':
            need(not started and not palette and color in(2,6)and size>0 and size<=768 and size%3==0,'corrupt_container');palette=True
        elif kind==b'IEND':
            need(size==0 and end==len(raw)and started,'corrupt_container');ended=True;offset=end;count+=1;break
        elif kind not in (b'IHDR',b'IDAT'):
            need(bool(kind[0]&32),'unsupported_variant')
            stored+=size;need(stored<=MAX_METADATA,'metadata_limit')
            if kind in (b'tEXt',b'zTXt',b'iTXt'):
                text_fields+=1;need(text_fields<=MAX_TEXT_FIELDS,'metadata_limit');category,length=text_info(kind,data,MAX_METADATA-expanded);expanded+=length;categories[category]+=1
                metadata[{b'tEXt':'plain_text',b'zTXt':'compressed_text',b'iTXt':'international_text'}[kind]]+=1
            else:metadata[{b'eXIf':'EXIF_section',b'iCCP':'ICC_section',b'caBX':'C2PA_section',b'tIME':'time_section'}.get(kind,'other_ancillary_sections')]+=1
        count+=1;offset=end
    need(ended and offset==len(raw),'corrupt_container')
    row=width*COLORS[color][1]+1;expected=row*height;need(expected<=MAX_EXPANDED,'input_limit')
    pixels=inflate(bytes(idat),expected,'corrupt_image_data');need(len(pixels)==expected and all(x<=4 for x in pixels[::row]),'corrupt_image_data')
    return {'profile':PROFILE,'state':'OBSERVED','asset_sha256':hashlib.sha256(raw).hexdigest(),'asset_bytes':len(raw),'image':header,'chunk_count':count,'stored_metadata_bytes':stored,'expanded_text_bytes':expanded,'metadata_sections':metadata,'text_categories':categories,'image_data_check':'bounded_zlib_scanlines','metadata_values_returned':False,'watermark_verified':False,'C2PA_inspected':False,'AI_origin':'unknown','content_truth_established':False,'tags':[]}

def unavailable(reason,raw=None):
    r={'profile':PROFILE,'state':'UNAVAILABLE','reason':reason if reason in REASONS else'worker_unavailable','metadata_values_returned':False,'watermark_verified':False,'C2PA_inspected':False,'AI_origin':'unknown','content_truth_established':False,'tags':[]}
    if type(raw)is bytes and len(raw)<=MAX_INPUT:r.update(asset_sha256=hashlib.sha256(raw).hexdigest(),asset_bytes=len(raw))
    return r

def validate_shape(record):
    need(type(record)is dict and record.get('profile')==PROFILE and type(record.get('asset_sha256'))is str and re.fullmatch('[a-f0-9]{64}',record['asset_sha256'])is not None and type(record.get('asset_bytes'))is int and 0<=record['asset_bytes']<=MAX_INPUT,'worker_unavailable')
    fixed={'profile','state','asset_sha256','asset_bytes','metadata_values_returned','watermark_verified','C2PA_inspected','AI_origin','content_truth_established','tags'}
    need(record.get('metadata_values_returned')is False and record.get('watermark_verified')is False and record.get('C2PA_inspected')is False and record.get('AI_origin')=='unknown'and record.get('content_truth_established')is False and record.get('tags')==[],'worker_unavailable')
    if record['state']=='UNAVAILABLE':need(set(record)==fixed|{'reason'}and record['reason']in REASONS,'worker_unavailable');return record
    need(record['state']=='OBSERVED'and set(record)==fixed|{'image','chunk_count','stored_metadata_bytes','expanded_text_bytes','metadata_sections','text_categories','image_data_check'},'worker_unavailable')
    image=record['image'];need(type(image)is dict and set(image)=={'width','height','bit_depth','color'}and image['bit_depth']==8 and type(image['bit_depth'])is int and image['color']in [x[0]for x in COLORS.values()],'worker_unavailable')
    need(all(type(image[n])is int and 1<=image[n]<=MAX_PIXELS for n in ['width','height'])and image['width']*image['height']<=MAX_PIXELS,'worker_unavailable')
    for name,maximum in [('chunk_count',MAX_CHUNKS),('stored_metadata_bytes',MAX_METADATA),('expanded_text_bytes',MAX_METADATA)]:need(type(record[name])is int and 0<=record[name]<=maximum,'worker_unavailable')
    for name,keys in [('metadata_sections',META_KEYS),('text_categories',CATEGORIES)]:
        value=record[name];maximum=MAX_TEXT_FIELDS if name=='text_categories'else MAX_CHUNKS;need(type(value)is dict and set(value)==set(keys)and all(type(x)is int and 0<=x<=maximum for x in value.values()),'worker_unavailable')
    meta=record['metadata_sections'];need(sum(record['text_categories'].values())==sum(meta[x]for x in ['plain_text','compressed_text','international_text'])<=MAX_TEXT_FIELDS and sum(meta.values())<=record['chunk_count']and record['image_data_check']=='bounded_zlib_scanlines','worker_unavailable')
    return record

def validate_record(record,raw):
    validate_shape(record)
    need(record['asset_sha256']==hashlib.sha256(raw).hexdigest()and record['asset_bytes']==len(raw),'worker_unavailable')
    if record['state']=='OBSERVED':
        need(len(raw)>=33 and raw.startswith(SIGNATURE)and raw[12:16]==b'IHDR','worker_unavailable')
        width,height,depth,color,_,_,_=struct.unpack('>IIBBBBB',raw[16:29])
        need(color in COLORS and record['image']=={'width':width,'height':height,'bit_depth':depth,'color':COLORS[color][0]},'worker_unavailable')
    return record

def identity(info):return info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns,info.st_ctime_ns

def inspect_file(path):
    """One opened descriptor and captured subject; worker never receives a path."""
    try:
        selected=Path(path).expanduser().absolute()
        need(not any(p.is_symlink()for p in selected.parents),'source_unavailable')
        fd=os.open(selected,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    except (OSError,ValueError):raise ImageError('source_unavailable')from None
    try:
        before=os.fstat(fd);need(stat.S_ISREG(before.st_mode),'source_unavailable');need(before.st_size<=MAX_INPUT,'input_limit')
        raw=bytearray()
        while True:
            chunk=os.read(fd,min(65536,MAX_INPUT-len(raw)+1))
            if not chunk:break
            raw.extend(chunk);need(len(raw)<=MAX_INPUT,'input_limit')
        raw=bytes(raw);need(identity(before)==identity(os.fstat(fd)),'source_unavailable');os.lseek(fd,0,os.SEEK_SET)
        result=worker_record(fd)
        need(identity(before)==identity(os.fstat(fd)),'source_unavailable')
        return validate_record(result,raw)
    except OSError:raise ImageError('source_unavailable')from None
    finally:owned=fd;fd=None;os.close(owned)

def worker_record(fd):
    selector=selectors.DefaultSelector();child=None;complete=False;output=bytearray();deadline=time.monotonic()+WALL_SECONDS
    try:
        with tempfile.TemporaryDirectory(prefix='aitrust-png-')as directory:
            os.chmod(directory,0o700)
            child=subprocess.Popen([sys.executable,'-I','-S','-B',str(ROOT/'scripts/inspect-png-metadata.py'),'--worker'],stdin=fd,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,cwd=directory,env={'PATH':os.defpath,'LANG':'C.UTF-8'},start_new_session=True,close_fds=True)
            os.set_blocking(child.stdout.fileno(),False);selector.register(child.stdout,selectors.EVENT_READ)
            eof=False
            while not eof:
                remaining=deadline-time.monotonic();need(remaining>0,'worker_unavailable')
                for key,_ in selector.select(min(.1,remaining)):
                    try:chunk=os.read(key.fd,min(65536,MAX_OUTPUT-len(output)+1))
                    except BlockingIOError:continue
                    if not chunk:eof=True;break
                    output.extend(chunk);need(len(output)<=MAX_OUTPUT,'worker_unavailable')
            remaining=deadline-time.monotonic();need(remaining>0,'worker_unavailable');code=child.wait(timeout=remaining);complete=True;need(code==0,'worker_unavailable')
        def unique(pairs):
            r={}
            for k,v in pairs:need(k not in r,'worker_unavailable');r[k]=v
            return r
        try:return json.loads(output,object_pairs_hook=unique,parse_constant=lambda _:(_ for _ in ()).throw(ImageError('worker_unavailable')))
        except (ValueError,UnicodeError,RecursionError):raise ImageError('worker_unavailable')from None
    finally:
        if child is not None:
            # wait() can reap successfully and then raise in surrounding I/O.
            # A known-reaped numeric process/group ID is no longer ours to signal.
            if not complete and child.returncode is None:
                try:os.killpg(child.pid,signal.SIGKILL)
                except ProcessLookupError:pass
                child.wait(timeout=5)
            child.stdout.close()
        selector.close()

def text_result(record):
    # Render fixed literals/numeric fields only, never a stored metadata string.
    if record.get('state')=='OBSERVED' or 'asset_sha256'in record:validate_shape(record)
    else:need(type(record)is dict and record==unavailable(record.get('reason')),'worker_unavailable')
    lines=['AI TRUST ID · PNG details']
    if record.get('state')!='OBSERVED':
        reason=record.get('reason');messages={'unsupported_format':'This file format is not supported. Choose a PNG.','unsupported_variant':'This PNG variant is not supported by this reader.','corrupt_container':'The PNG structure could not be read.','corrupt_image_data':'The PNG image data could not be read.','corrupt_text_metadata':'A stored text section could not be read.','input_limit':'This image exceeds the supported size limits.','metadata_limit':'The stored metadata exceeds the supported limits.','source_unavailable':'The selected regular file could not be read.','worker_unavailable':'The image check did not complete.','invalid_request':'Choose a supported local PNG file.'}
        lines.append(messages.get(reason,'The image check did not complete.'))
    else:
        i=record['image'];lines.append(f"PNG · {i['width']} × {i['height']} pixels · {i['color']}")
        m=record['metadata_sections'];lines.append('Stored text sections: '+str(sum(m[n]for n in ['plain_text','compressed_text','international_text'])))
        for name,label in [('EXIF_section','EXIF-shaped section'),('ICC_section','Color-profile section'),('C2PA_section','Content Credential-shaped section')]:
            if m[name]:lines.append(label+': present; contents not verified.')
        for name,label in [('author','Author-labelled text fields'),('software','Software-labelled text fields'),('XMP','XMP-labelled text fields')]:
            if record['text_categories'][name]:lines.append(label+': '+str(record['text_categories'][name])+' (values hidden; not authorship proof).')
        lines.append('Stored text, names, GPS and URLs are not shown. Other identifying information may still be present.')
    lines+=['AI origin: Unknown. No watermark or Content Credential is verified here.','No tag issued. Image contents and authorship are not verified.']
    return '\n'.join(lines)
