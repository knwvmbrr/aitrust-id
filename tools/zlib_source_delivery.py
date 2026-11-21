"""Exact selected embedded-zlib source/notice delivery; no whole-route clearance."""
import gzip
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import shutil
import tarfile
import zipfile
from tools import pyodide_js_sources as foundation

ROOT=Path(__file__).resolve().parents[1]
BASE='sbom/reviews/zlib-runtime'
MANIFEST=BASE+'/manifest.json'
PROFILE='selected-zlib-runtime-source-notices/v1'
VERSION='1.3.1'
ARCHIVE_SHA256='17e88863f3600672ab49182f217281b6fc4d3c762bde361935e436a95214d05c'
ARCHIVE_SHA512='8c9642495bafd6fad4ab9fb67f09b268c69ff9af0f4f20cf15dfc18852ff1f312bd8ca41de761b3f8d8e90e77d79f2ccacd3d4c5b19e475ecf09d021fdfe9088'
ARCHIVE_BYTES=1572744
EMSCRIPTEN_COMMIT='285c424dfa9e83b03cf8490c65ceadb7c45f28eb'
EMSCRIPTEN_SHA256='8c8c413026dd7b86b0acf7e4b48cb718956c21a053887f2a628168dd1ba2cb33'
EMSCRIPTEN_BYTES=34477324
RECIPE_SHA256='d3d8ca9a7caac82fa68e4984e47c03386093b8fa2b068e8e9eccedd3aa406926'
EMSCRIPTEN_LICENSE_SHA256='620a78084fc7ca97c0b5dea9abf891f3ffcadfdbf305276f099c9c4e12fc1d86'
LICENSE_SHA256='845efc77857d485d91fb3e0b884aaa929368c717ae8186b66fe1ed2495753243'
HEADER_SOURCE_SHA256='8a5579af72ea4f427ff00a4150f0ccb3fc5c1e4379f726e101133b1ab9fc600c'
HEADER_SHA256='fbab901f75feb30106921191b00a52ed14fb439e49ad0e42bc7b329438c34d24'
WASM_SHA256='cc36e3cab04fdfc9a63ff13eb52eae2b911bf46c025cc7b281f394bd3de1d5e6'
# Actual version probe identity is pinned separately from mutable cohort metadata.
OBSERVATION_SHA256='3fdaedb6b2d1bb6d88754183f94f7af33c17eb3fea084bb12bde3f6321a54089'
SOURCES=('tools/zlib_source_delivery.py','scripts/zlib-source-delivery.py',
         'tools/pyodide_js_sources.py','tools/dependency_policy.py')
NAMES=('ZLIB-SOURCES.zip','NOTICES.txt','index.json')
CLAIMS={k:False for k in ('full_wasm_corresponding_source','compiled_library_rebuilt',
       'publisher_signature_verified','legal_clearance','global_distribution_admitted',
       'complete_project_obligations')}
MAX_OUTPUT=2_000_000


class DeliveryError(ValueError):
    """Fixed refusal only; never private paths or archived data."""


class OutputUncertain(DeliveryError):
    pass


def need(condition):
    if not condition:raise DeliveryError('Selected zlib source/notice check refused')


def sha(raw):return hashlib.sha256(raw).hexdigest()


def canonical(value):return foundation.canonical(value)


def read(root,name,limit=200000):return foundation.read(root,name,limit)


def source_path(digest,suffix):return BASE+'/sources/'+digest+suffix


def preflight_recipe_tar(raw):
    """Bound expanded tar and metadata BEFORE tarfile can parse PAX records."""
    need(type(raw) is bytes and 0<len(raw)<=35_000_000)
    count=expanded=metadata=0
    with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
        def take(size):
            nonlocal expanded
            need(type(size) is int and 0<=size<=16384)
            data=stream.read(size);expanded+=len(data)
            need(expanded<=150_000_000 and len(data)==size);return data
        while True:
            header=take(512)
            if not any(header):
                need(not any(take(512)))
                while True:
                    block=stream.read(16384)
                    if not block:break
                    expanded+=len(block);need(expanded<=150_000_000 and not any(block))
                break
            count+=1;need(count<=16384)
            size_field=header[124:136].strip(b' \0');checksum=header[148:156].strip(b' \0')
            need(bool(size_field) and re.fullmatch(b'[0-7]+',size_field)
                 and bool(checksum) and re.fullmatch(b'[0-7]+',checksum))
            need(int(checksum,8)==sum(header[:148])+8*32+sum(header[156:]))
            size=int(size_field,8);kind=header[156:157]
            need(kind in (b'0',b'\0',b'1',b'2',b'5',b'x',b'g',b'L',b'K') and size<=16_000_000)
            if kind in (b'x',b'g',b'L',b'K'):
                metadata+=size;need(size<=16384 and metadata<=1_000_000)
            remaining=((size+511)//512)*512
            while remaining:
                n=min(16384,remaining);take(n);remaining-=n


def recipe_members(raw):
    need(len(raw)==EMSCRIPTEN_BYTES and sha(raw)==EMSCRIPTEN_SHA256)
    preflight_recipe_tar(raw)
    prefix='emscripten-'+EMSCRIPTEN_COMMIT+'/'
    wanted={'LICENSE','tools/ports/zlib.py'};found={};seen=set()
    with tarfile.open(fileobj=io.BytesIO(raw),mode='r|gz') as archive:
        for count,entry in enumerate(archive):
            need(count<16384 and len(entry.name)<=4096 and entry.name not in seen)
            seen.add(entry.name);need(not entry.name.startswith('/') and '\\' not in entry.name
                and '..' not in PurePosixPath(entry.name).parts)
            if entry.name.startswith(prefix) and entry.name[len(prefix):] in wanted:
                name=entry.name[len(prefix):];need(entry.isfile() and 0<entry.size<=200000 and name not in found)
                with archive.extractfile(entry) as file:value=file.read(entry.size+1)
                need(len(value)==entry.size);found[name]=value
    need(set(found)==wanted and sha(found['LICENSE'])==EMSCRIPTEN_LICENSE_SHA256
         and sha(found['tools/ports/zlib.py'])==RECIPE_SHA256)
    return found


def check_recipe(recipe):
    need(sha(recipe)==RECIPE_SHA256)
    text=recipe.decode('utf-8','strict')
    need(re.findall(r"^VERSION = '([^']+)'$",text,re.M)==[VERSION]
         and re.findall(r"^HASH = '([^']+)'$",text,re.M)==[ARCHIVE_SHA512]
         and "https://github.com/madler/zlib/archive/refs/tags/v" in text)


def archive_members(raw):
    need(type(raw) is bytes and len(raw)==ARCHIVE_BYTES and sha(raw)==ARCHIVE_SHA256
         and hashlib.sha512(raw).hexdigest()==ARCHIVE_SHA512)
    files=foundation.selected_tar(raw,'zlib-'+VERSION+'/',{'LICENSE','zlib.h'})
    need(sha(files['LICENSE'])==LICENSE_SHA256 and sha(files['zlib.h'])==HEADER_SOURCE_SHA256)
    header=files['zlib.h'].split(b'*/',1)[0]+b'*/'
    need(sha(header)==HEADER_SHA256)
    return files,header


def inputs(root):
    release,_,bindings=foundation.release_inputs(root)
    need(release['runtime_members']['pyodide.asm.wasm']=={'bytes':9598218,'sha256':WASM_SHA256}
         and release['emscripten_commit']==EMSCRIPTEN_COMMIT
         and release['archives']['emscripten.tar.gz']=={
          'url':'https://codeload.github.com/emscripten-core/emscripten/tar.gz/'+EMSCRIPTEN_COMMIT,
          'bytes':EMSCRIPTEN_BYTES,'sha256':EMSCRIPTEN_SHA256})
    return release,bindings


def expected_manifest(root,raw,recipe,em_license,observation):
    files,header=archive_members(raw);check_recipe(recipe)
    need(sha(em_license)==EMSCRIPTEN_LICENSE_SHA256 and sha(observation)==OBSERVATION_SHA256)
    observed=foundation.parse(observation)
    need(observed['exit']==0 and observed['result']['pass'] is True
         and observed['result']['zlib_runtime_version']==VERSION
         and observed['result']['pyodide_runtime_version']=='314.0.7'
         and observed['result']['network_attempts']==0 and observed['result']['source_stable'] is True)
    release,bindings=inputs(root)
    need(observed['result']['runtime_sha256']=={name:row['sha256'] for name,row in release['runtime_members'].items()})
    rows=[('zlib_archive',raw,'.tar.gz'),('zlib_license',files['LICENSE'],'.txt'),
          ('zlib_header_source',files['zlib.h'],'.h'),('zlib_header_notice',header,'.txt'),
          ('emscripten_recipe',recipe,'.py'),('emscripten_recipe_license',em_license,'.txt'),
          ('runtime_observation',observation,'.json')]
    retained={source_path(sha(value),suffix):value for _,value,suffix in rows}
    value={'profile':PROFILE,'version':VERSION,'runtime_version':'314.0.7',
      'runtime_members':release['runtime_members'],'input_sha256':bindings,
      'producer_sha256':{p:sha(read(root,p)) for p in SOURCES},
      'evidence':{name:{'path':source_path(sha(v),suffix),'bytes':len(v),'sha256':sha(v)} for name,v,suffix in rows},
      'zlib_source_url':'https://github.com/madler/zlib/archive/refs/tags/v1.3.1.tar.gz',
      'source_sha512':ARCHIVE_SHA512,'recipe_origin':{
        'commit':EMSCRIPTEN_COMMIT,'archive_sha256':EMSCRIPTEN_SHA256,
        'recipe_url':'https://raw.githubusercontent.com/emscripten-core/emscripten/'+EMSCRIPTEN_COMMIT+'/tools/ports/zlib.py',
        'license_url':'https://raw.githubusercontent.com/emscripten-core/emscripten/'+EMSCRIPTEN_COMMIT+'/LICENSE'},
      'claims':CLAIMS}
    return value,retained


def replay_cached(directory,root=ROOT):
    directory=Path(directory).absolute()
    raw=read(directory,'zlib-1.3.1.tar.gz',ARCHIVE_BYTES)
    emscripten=read(directory,'emscripten.tar.gz',EMSCRIPTEN_BYTES)
    upstream=recipe_members(emscripten)
    observation=read(root,source_path(OBSERVATION_SHA256,'.json'))
    return expected_manifest(root,raw,upstream['tools/ports/zlib.py'],upstream['LICENSE'],observation)


def checked(root=ROOT):
    manifest_raw=read(root,MANIFEST);value=foundation.parse(manifest_raw)
    raw=read(root,source_path(ARCHIVE_SHA256,'.tar.gz'),ARCHIVE_BYTES)
    recipe=read(root,source_path(RECIPE_SHA256,'.py'))
    license=read(root,source_path(EMSCRIPTEN_LICENSE_SHA256,'.txt'))
    observation=read(root,source_path(OBSERVATION_SHA256,'.json'))
    expected,retained=expected_manifest(root,raw,recipe,license,observation)
    need(canonical(value)==canonical(expected))
    for name,data in retained.items():need(read(root,name,max(len(data),200000))==data)
    need(read(root,MANIFEST)==manifest_raw);retained[MANIFEST]=manifest_raw
    return value,retained


def outputs(root=ROOT):
    value,retained=checked(root);evidence=value['evidence']
    notices=(b'Selected zlib1.3.1 source and exact upstream notices\n'
      b'This includes the unmodified zlib source archive, its full LICENSE and\n'
      b'zlib.h notice, plus the exact Emscripten port recipe and its license.\n'
      b'The selected WASM reports zlib1.3.1; compiler/linkage reproduction and\n'
      b'full WASM/project obligations or global distribution clearance are NOT claimed.\n'
      b'Source: ZLIB-SOURCES.zip; identities and scope: index.json\n\n')
    for name in ['zlib_license','zlib_header_notice','emscripten_recipe_license']:
        raw=retained[evidence[name]['path']];label=('=== '+name+' ===\n').encode()
        need(len(label)+len(raw)+1<=20000-len(notices));notices+=label+raw+b'\n'
    members={'NOTICES.txt':notices,'upstream/zlib-1.3.1.tar.gz':retained[evidence['zlib_archive']['path']],
      'source/LICENSE':retained[evidence['zlib_license']['path']],
      'source/zlib.h':retained[evidence['zlib_header_source']['path']],
      'evidence/emscripten-zlib-port.py':retained[evidence['emscripten_recipe']['path']]}
    index={'profile':PROFILE,'version':VERSION,'runtime_members':value['runtime_members'],
      'cohort_manifest_sha256':sha(retained[MANIFEST]),'source_archive_sha256':ARCHIVE_SHA256,
      'emscripten_recipe_sha256':RECIPE_SHA256,'runtime_observation_sha256':OBSERVATION_SHA256,
      'claims':CLAIMS,'members':[{'path':name,'bytes':len(raw),'sha256':sha(raw)} for name,raw in sorted(members.items())]}
    members['index.json']=canonical(index)+b'\n';need(sum(map(len,members.values()))<=MAX_OUTPUT)
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w',compression=zipfile.ZIP_STORED,allowZip64=False) as archive:
        for name,raw in sorted(members.items()):
            foundation.safe_relative(name);info=zipfile.ZipInfo(name,(1980,1,1,0,0,0));info.create_system=3;info.external_attr=0o100644<<16
            archive.writestr(info,raw)
    bundle=stream.getvalue();need(len(bundle)<=MAX_OUTPUT)
    return {'ZLIB-SOURCES.zip':bundle,'NOTICES.txt':notices,'index.json':members['index.json']}


def export(destination,root=ROOT):
    expected=outputs(root);target=Path(destination).absolute();parent=target.parent
    need(parent.resolve()==parent and parent.is_dir() and not parent.is_symlink())
    status=parent.stat();need(status.st_uid==os.getuid() and not status.st_mode&0o022)
    existing=target.exists() or target.is_symlink()
    if existing:
        need(not target.is_symlink() and target.is_dir() and set(p.name for p in target.iterdir())==set(NAMES))
        if all(read(target,name,MAX_OUTPUT)==raw for name,raw in expected.items()):return expected
    stage=parent/('.zlib-stage-'+secrets.token_hex(12));backup=parent/('.zlib-old-'+secrets.token_hex(12));stage.mkdir(mode=0o755);moved=committed=False
    try:
        for name,raw in expected.items():
            fd=os.open(stage/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o644)
            try:
                # The raw descriptor stays owned here even if wrapper creation fails.
                with os.fdopen(fd,'wb',closefd=False) as file:file.write(raw);file.flush();os.fsync(file.fileno())
            finally:
                owned_fd=fd;fd=None
                # Relinquish ownership before one close attempt; never retry a
                # close error against a numeric descriptor that may be reused.
                os.close(owned_fd)
        need(expected==outputs(root))
        if existing:os.rename(target,backup);moved=True
        os.rename(stage,target);committed=True
        if moved:shutil.rmtree(backup)
    except BaseException:
        if moved or committed:raise OutputUncertain('Zlib output commit uncertain') from None
        raise
    finally:
        if stage.exists():
            try:shutil.rmtree(stage)
            except BaseException:
                if moved or committed:raise OutputUncertain('Zlib output commit uncertain') from None
                raise DeliveryError('Zlib staging cleanup unavailable') from None
    return expected


def check_built(directory,root=ROOT):
    directory=Path(directory).absolute();expected=outputs(root);value,_=checked(root)
    runtime='device/runtime-314.0.7';delivery='runtime-zlib-sources'
    for relative,names in [(runtime,set(value['runtime_members'])),(delivery,set(NAMES))]:
        path=directory/relative;need(path.resolve()==path and path.is_dir() and not path.is_symlink()
             and {p.name for p in path.iterdir()}==names)
    for name,row in value['runtime_members'].items():
        raw=read(directory,runtime+'/'+name,12_000_000);need(len(raw)==row['bytes'] and sha(raw)==row['sha256'])
    for name,raw in expected.items():need(read(directory,delivery+'/'+name,MAX_OUTPUT)==raw)
    need(expected==outputs(root))
    return {'pass':True,'profile':PROFILE,'zlib_version':VERSION,'runtime_members_checked':5,
      'delivery_artifacts_checked':3,'bundle_sha256':sha(expected['ZLIB-SOURCES.zip']),**CLAIMS}
