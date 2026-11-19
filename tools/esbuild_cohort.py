"""Offline esbuild source/notice evidence; never executes a reviewed binary."""
import base64
from datetime import datetime,timezone
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import tarfile
import zipfile

from protocol.evidence import read_evidence

ROOT=Path(__file__).resolve().parents[1]
PROFILE='esbuild-platform-source-observations/1.0.0'
MANIFEST='sbom/reviews/esbuild-source.json'
PREFIX='node_modules/@esbuild/'
MAGIC=b'\xff Go buildinf:'
MAX_ARCHIVE=64*1024*1024
MAX_TOTAL=300*1024*1024
MAX_BINARY=32*1024*1024
FILES=('tools/esbuild_cohort.py','scripts/verify-esbuild-cohort.py','tests/test_esbuild_cohort.py','docs/esbuild-source-review.md')

def need(ok):
    if not ok:raise ValueError('esbuild source evidence refused')

def sha(raw):return hashlib.sha256(raw).hexdigest()
def encoded(row):return json.dumps(row,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()
def read(path,limit=MAX_ARCHIVE):
    path=Path(path);need(not any(p.is_symlink() for p in [path,*path.parents]) and path.is_file())
    with path.open('rb') as f:raw=f.read(limit+1)
    need(len(raw)<=limit);return raw

def safe(name):
    need(type(name) is str and 0<len(name)<=512 and not name.startswith('/') and '\\' not in name
         and all(ord(c)>=32 for c in name) and not any(x in ('','.','..') for x in name.rstrip('/').split('/')))

def tar_members(raw,allowed_links=None):
    need(type(raw) is bytes and 0<len(raw)<=MAX_ARCHIVE)
    rows={};total=0
    with tarfile.open(fileobj=io.BytesIO(raw),mode='r|gz') as archive:
        for member in archive:
            safe(member.name);need(member.name not in rows and len(rows)<100000)
            need(member.isdir() or member.isfile() or allowed_links is not None and member.issym() and allowed_links.get(member.name)==member.linkname);need(0<=member.size<=MAX_BINARY)
            total+=member.size;need(total<=MAX_TOTAL)
            data=archive.extractfile(member).read() if member.isfile() else None
            need(data is None or len(data)==member.size);rows[member.name]=data
    return rows

def selected(root):
    locked=read_evidence(root/'site/package-lock.json')['packages']
    native=read_evidence(root/'sbom/native/manifest.json',limit=8_000_000)['artifacts']
    notices=read_evidence(root/'sbom/notices/manifest.json',limit=8_000_000)['npm']
    names=sorted(n for n in locked if n.startswith(PREFIX));need(len(names)==26)
    result=[]
    for name in names:
        lock=locked[name];need(lock['version']=='0.28.1')
        rows=[r for r in native if r['lock']=='site/package-lock.json' and r['package_path']==name]
        license_rows=[r for r in notices if r['lock']=='site/package-lock.json' and r['package_path']==name]
        need(len(rows)==len(license_rows)==1)
        row=rows[0];notice=license_rows[0]
        need(all(row[k]==lock[k] for k in ['version','integrity']) and notice['resolved']==lock['resolved'])
        need(row['artifact_sha256']==notice['artifact_sha256'] and row['license_declared']==lock.get('license'))
        need(1<=len(row['native_candidates'])<=2)
        result.append({'package_path':name,'lock':lock,'native':row,'notice':notice})
    return result

def literal_versions(raw):
    values=sorted({x.decode('ascii') for x in re.findall(rb'go1\.[0-9]{1,3}\.[0-9]{1,3}(?:rc[0-9]{1,3}|beta[0-9]{1,3})?',raw)})
    need(len(values)<=32);return values

def build_info(raw):
    """Modern inline layout only; whole-byte search is not an executable loader."""
    need(type(raw) is bytes and 0<len(raw)<=MAX_BINARY)
    count=raw.count(MAGIC)
    result={'profile':'go-inline-build-info-observation/v1','marker_count':count,
            'status':'unavailable','reason':'marker_absent','toolchain_version':None,
            'module_metadata_sha256':None,'embedded_version_literals':literal_versions(raw),
            'publisher_authenticated':False}
    if not count:return result
    if count!=1:result['reason']='ambiguous_marker';return result
    pos=raw.index(MAGIC)
    if pos%16 or len(raw)<pos+32:result['reason']='unsupported_header';return result
    ptr,flags=raw[pos+14:pos+16]
    if ptr not in (4,8) or flags&~3 or not flags&2 or any(raw[pos+16:pos+32]):
        result['reason']='unsupported_layout';return result
    def string(offset):
        value=0;start=offset
        for shift in range(0,70,7):
            need(offset<len(raw));byte=raw[offset];offset+=1
            need(shift!=63 or byte<=1);value|=(byte&127)<<shift
            if not byte&128:
                need(offset-start==1 or byte!=0);need(value<=65536 and offset+value<=len(raw))
                return raw[offset:offset+value],offset+value
        raise ValueError('Unsupported inline length')
    try:
        version,end=string(pos+32);module,_=string(end)
        version=version.decode('utf-8','strict');module.decode('utf-8','strict')
        need(re.fullmatch(r'go1[.][0-9]{1,3}[.][0-9]{1,3}(?:rc[0-9]{1,3}|beta[0-9]{1,3})?',version))
    except (ValueError,UnicodeError):result['reason']='malformed_inline_data';return result
    result.update(status='inline_metadata_observed',reason=None,toolchain_version=version,module_metadata_sha256=sha(module))
    return result

def inspect_archive(raw,row):
    lock=row['lock'];algorithm,value=lock['integrity'].split('-',1)
    need(algorithm in ('sha256','sha512') and hashlib.new(algorithm,raw).digest()==base64.b64decode(value,validate=True))
    need(sha(raw)==row['native']['artifact_sha256']);members=tar_members(raw)
    need(all(n.startswith('package/') or n=='package' for n in members))
    package=json.loads(members['package/package.json'].decode('utf-8'))
    need(package['name']==row['package_path'].removeprefix('node_modules/') and package['version']=='0.28.1')
    binaries=[]
    for binary in row['native']['native_candidates']:
        data=members.get(binary['member']);need(type(data) is bytes)
        need(len(data)==binary['bytes'] and sha(data)==binary['sha256'])
        script=binary['format']=='script'
        if script:need(data.startswith(b'#!/usr/bin/env node'))
        binaries.append({'member':binary['member'],'sha256':sha(data),'bytes':len(data),'format':binary['format'],
                         'build_info':None if script else build_info(data),'declared_interpreter':'node' if script else None})
    return {'package_path':row['package_path'],'archive_sha256':sha(raw),'archive_bytes':len(raw),
            'members':binaries,'declared_node_engine':package.get('engines',{}).get('node'),'binary_executed':False}

def zip_members(raw,prefix):
    need(0<len(raw)<=MAX_ARCHIVE);rows={};total=0
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        for member in archive.infolist():
            safe(member.filename);need(member.filename.startswith(prefix) and member.filename not in rows and len(rows)<100000)
            kind=(member.external_attr>>16)&0o170000;need(kind in (0,0o040000,0o100000))
            total+=member.file_size;need(0<=member.file_size<=MAX_BINARY and total<=MAX_TOTAL)
            data=None if member.is_dir() else archive.read(member)
            need(data is None or len(data)==member.file_size);rows[member.filename]=data
    return rows

def module_h1(members):
    h=hashlib.sha256()
    for name,data in sorted(members.items()):
        if data is not None:h.update((sha(data)+'  '+name+'\n').encode())
    return 'h1:'+base64.b64encode(h.digest()).decode()

def source_members(raw,entry):
    if entry['format']=='tar-gzip':
        # Exact source-only browser test link: counted, never followed/extracted.
        links={'esbuild-bb9db84c02433fbe37b3509f53f9f3e3cc48725e/scripts/browser/esbuild.wasm.bagel':'../../npm/esbuild-wasm/esbuild.wasm'} if entry['filename']=='esbuild-source.tar.gz' else None
        return tar_members(raw,links)
    if entry['format']=='module-zip':return zip_members(raw,entry['prefix'])
    need(entry['format']=='json');return {'metadata.json':raw}

def excerpt(raw,lines):
    if lines is None:return raw
    need(type(lines) is list and len(lines)==2 and all(type(v) is int for v in lines) and 1<=lines[0]<=lines[1])
    rows=raw.splitlines(keepends=True);need(lines[1]<=len(rows));return b''.join(rows[lines[0]-1:lines[1]])

def verify(root=ROOT,archive_dir=None,source_dir=None):
    value=read_evidence(root/MANIFEST,limit=2_000_000)
    need(set(value)=={'profile','captured_at','status','source_commit','sources','selected_inputs_sha256','platform_artifacts','upstream_archives','source_texts','source_relationships','limits','permission_cleared','release_approved','reproducible_build_verified','publisher_signature_verified'})
    need(value['profile']==PROFILE and value['status']=='bounded_source_and_notice_evidence')
    stamp=datetime.fromisoformat(value['captured_at']);need(stamp.tzinfo is not None and stamp<=datetime.now(timezone.utc))
    need(re.fullmatch('[a-f0-9]{40}',value['source_commit']))
    need(all(value[k] is False for k in ['permission_cleared','release_approved','reproducible_build_verified','publisher_signature_verified']))
    need(value['sources']=={name:sha(read(root/name,2_000_000)) for name in FILES})
    rows=selected(root);need(sha(encoded(rows))==value['selected_inputs_sha256'])
    observed=value['platform_artifacts'];need(len(observed)==26 and [x['package_path'] for x in observed]==[x['package_path'] for x in rows])
    for row,item in zip(rows,observed):
        need(set(item)=={'package_path','archive_sha256','archive_bytes','members','declared_node_engine','binary_executed'})
        need(item['archive_sha256']==row['native']['artifact_sha256'] and item['binary_executed'] is False)
        need(type(item['archive_bytes']) is int and 0<item['archive_bytes']<=MAX_ARCHIVE)
        need(len(item['members'])==len(row['native']['native_candidates']))
        for binary,member in zip(row['native']['native_candidates'],item['members']):
            need(set(member)=={'member','sha256','bytes','format','build_info','declared_interpreter'})
            need(all(member[k]==binary[k] for k in ['member','sha256','bytes','format']))
            info=member['build_info']
            if binary['format']=='script':need(info is None and member['declared_interpreter']=='node');continue
            need(member['declared_interpreter'] is None)
            need(set(info)=={'profile','marker_count','status','reason','toolchain_version','module_metadata_sha256','embedded_version_literals','publisher_authenticated'})
            need(info['profile']=='go-inline-build-info-observation/v1' and info['status']=='unavailable' and info['reason']=='marker_absent')
            need(type(info['marker_count']) is int and info['marker_count']==0 and info['toolchain_version'] is None and info['module_metadata_sha256'] is None)
            need(info['embedded_version_literals']==['go1.26.4'] and info['publisher_authenticated'] is False)
        if archive_dir is not None:
            filename=sha(row['lock']['integrity'].encode())+'.tgz'
            need(inspect_archive(read(Path(archive_dir)/filename),row)==item)
    need(len(value['upstream_archives'])==4 and {x['filename'] for x in value['upstream_archives']}=={'esbuild-source.tar.gz','xsys-source.zip','go-source.tar.gz','go-download-metadata.json'})
    need(all(x['publisher_signature_verified'] is False for x in value['upstream_archives']))
    need(value['source_relationships']['binary_to_source_reproduced'] is False and value['source_relationships']['actual_compiler_identity_verified'] is False)
    need(type(value['source_texts']) is list and 1<=len(value['source_texts'])<=128)
    paths=set()
    for text in value['source_texts']:
        need(re.fullmatch('[a-f0-9]{64}',text['sha256']))
        need(text['archive'] in {x['filename'] for x in value['upstream_archives']})
        safe(text['member'])
        path='sbom/reviews/sources/'+text['sha256']+'.txt';need(text['path']==path)
        raw=read(root/path,2_000_000);need(sha(raw)==text['sha256'] and len(raw)==text['bytes']);raw.decode('utf-8','strict');paths.add(path)
    replayed={}
    if source_dir is not None:
        total=0
        for entry in value['upstream_archives']:
            need(re.fullmatch('[a-z0-9.-]+',entry['filename']))
            raw=read(Path(source_dir)/entry['filename']);total+=len(raw);need(total<=MAX_TOTAL)
            need(sha(raw)==entry['sha256'] and len(raw)==entry['bytes'])
            replayed[entry['filename']]=source_members(raw,entry)
        for text in value['source_texts']:
            full=replayed[text['archive']][text['member']];need(type(full) is bytes and sha(full)==text['member_sha256'])
            need(excerpt(full,text['lines'])==read(root/text['path'],2_000_000))
        rel=value['source_relationships']
        need(module_h1(replayed['xsys-source.zip'])==rel['xsys_module_h1'])
        module_sum=next(t for t in value['source_texts'] if t['role']=='esbuild_go_sum')
        need(rel['xsys_module_h1'].encode() in read(root/module_sum['path']))
        metadata=json.loads(replayed['go-download-metadata.json']['metadata.json'])
        downloads=[f for release in metadata if release['version']=='go1.26.4' for f in release['files'] if f['filename']=='go1.26.4.src.tar.gz']
        go=next(x for x in value['upstream_archives'] if x['filename']=='go-source.tar.gz')
        need(len(downloads)==1 and downloads[0]['sha256']==go['sha256'] and downloads[0]['size']==go['bytes'])
    return {'pass':True,'profile':PROFILE,'platform_archives':26,'binary_bytes_replayed':archive_dir is not None,
            'upstream_archives_replayed':source_dir is not None,'source_texts':len(value['source_texts']),
            'build_info_unavailable':sum(m['build_info'] is not None and m['build_info']['status']=='unavailable' for x in observed for m in x['members']),
            'members_observed':sum(len(x['members']) for x in observed),
            'node_launchers_observed':sum(m['declared_interpreter']=='node' for x in observed for m in x['members']),
            'permission_cleared':False,'release_approved':False,'reproducible_build_verified':False,'publisher_signature_verified':False}
