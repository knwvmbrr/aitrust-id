#!/usr/bin/env python3
"""Capture the exact published choice method; build static assets without executing it.

The descriptor Capture primitive derives from the reviewed published standalone
builder. This adaptation publishes only this fixed owned static namespace; a
failed multi-file publication is uncertain, never treated as an accepted build.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import stat
import sys

ROOT=Path(__file__).absolute().parents[1]
COHORT='integrations/mt-choice-reference/1.3.0'
SOURCE_COMMIT='b896cb4f1c303cb2a2bcd8a5ef5e5ba5a9b7acf8'
RUNTIME_POLICY='sbom/nested-runtime/pyodide-wasm-release.json'
RUNTIME_POLICY_SHA='fda0196c527b3920744261e27ac93cb71637ad36cf127e450aeaf49f425dd86f'
METHOD_FILES=('tools/mt_choice_device.py','tools/choice_framing.py','tools/language_observations.py','protocol/corpus.py','protocol/normalization.py','protocol/unicode15-data.json')
RUNTIME_FILES=('pyodide.mjs','pyodide.asm.mjs','pyodide.asm.wasm','python_stdlib.zip','pyodide-lock.json')
BUILD_FILES=('scripts/build-mt-choice-device.py','site/src/mt-choice-client.mjs','site/src/mt-choice-result.mjs','site/src/mt-choice-worker.mjs','protocol/normalization.mjs','protocol/normalization-core.js')
APPROVED_SOURCE={'tools/mt_choice_device.py': 'e71f7b125abd2084858a73cdb545c31c73b249336ed2dbded74e42575621a189', 'tools/choice_framing.py': '01ec221400300a302d561cfd88e6df7000465040966875a6ece25c6a4f4bbf36', 'tools/language_observations.py': '8b1def1ebda63b80454305217558baf6855e467cb319ff886edfdd5348cc50ec', 'protocol/corpus.py': '826f3c069b5480bc4a17d1aff9c5e0ad03a350da9b115c054a65b30f5f78a67f', 'protocol/normalization.py': 'd949dd32a43762b6d71c7c746430c3ee0fc0d4036885e3b1a2a94deb056f09d1', 'protocol/unicode15-data.json': '76121e982f9338f18905eb69e9c9c4b5268247b91841eb20e999b39e11aa0458', 'LICENSE': 'cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30', 'NOTICE': 'e185f305c76f821aa56011cd201ea03f49e97c57dfc786517f77bfc00c7fecd6', 'eval/vectors/unicode/LICENSE.txt': 'e7a93b009565cfce55919a381437ac4db883e9da2126fa28b91d12732bc53d96'}
COHORT_MANIFEST_SHA='a91443529c521f1ee4a0097eee91ae7da867a319076efd6608ec78cebbdfaad4'

class BuildError(ValueError):pass
class BuildUncertain(BuildError):pass

def need(ok):
    if not ok:raise BuildError('Selected wording source build unavailable.')

def sha(raw):return hashlib.sha256(raw).hexdigest()
def identity(info):return info.st_dev,info.st_ino,info.st_mode
def snapshot(info):return (*identity(info),info.st_nlink,info.st_size,info.st_mtime_ns,info.st_ctime_ns)

class Capture:
    """Adapted from the audited no-follow primitive; no sibling tag import."""
    def __init__(self,root):
        self.fds=[];self.directories=[];self.files=[];self.cache={};self.values={};self.total=0
        path=Path(root).absolute();need('..'not in path.parts)
        try:
            fd=os.open(path.anchor,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_NONBLOCK);self.fds.append(fd)
            self.anchor=(fd,identity(os.fstat(fd)))
            for part in path.parts[1:]:fd=self.child(fd,part)
            self.root=fd
        except BaseException:self.close();raise
    def child(self,parent,name):
        need(name not in ('','.','..')and'/'not in name)
        key=(parent,name)
        if key in self.cache:return self.cache[key]
        fd=os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=parent);self.fds.append(fd)
        info=os.fstat(fd);need(stat.S_ISDIR(info.st_mode));self.directories.append((parent,name,fd,identity(info)));self.cache[key]=fd;return fd
    def parent(self,name):
        parts=name.split('/');need(all(p not in ('','.','..')for p in parts));fd=self.root
        for part in parts[:-1]:fd=self.child(fd,part)
        return fd,parts[-1]
    def read(self,name,limit=200000):
        need(type(limit)is int and 0<limit<=12000000)
        if name in self.values:return self.values[name]
        need(len(self.files)<128);parent,leaf=self.parent(name)
        fd=os.open(leaf,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=parent);self.fds.append(fd);before=os.fstat(fd)
        need(stat.S_ISREG(before.st_mode)and before.st_nlink==1 and 0<before.st_size<=limit and self.total+before.st_size<=64000000)
        chunks=[];size=0
        while True:
            raw=os.read(fd,min(65536,limit+1-size))
            if not raw:break
            chunks.append(raw);size+=len(raw);need(size<=limit)
        need(size==before.st_size and snapshot(before)==snapshot(os.fstat(fd)))
        raw=b''.join(chunks);self.total+=size;self.files.append((parent,leaf,fd,snapshot(before)));self.values[name]=raw;return raw
    def check(self):
        need(identity(os.fstat(self.anchor[0]))==self.anchor[1])
        for parent,name,fd,expected in self.directories:need(identity(os.fstat(fd))==expected==identity(os.stat(name,dir_fd=parent,follow_symlinks=False)))
        for parent,name,fd,expected in self.files:need(snapshot(os.fstat(fd))==expected==snapshot(os.stat(name,dir_fd=parent,follow_symlinks=False)))
    def close(self):
        owned=self.fds;self.fds=[];error=None
        for fd in reversed(owned):
            try:os.close(fd)
            except BaseException as e:
                if error is None:error=e
        if error is not None:raise BuildError('Practice source cleanup unavailable.')from None
    def __enter__(self):return self
    def __exit__(self,*_):self.close()


def publish(destination, files, stable, publication=None):
    path=Path(destination).absolute();need('..'not in path.parts)
    need(len(files)==4 and sum(map(len,files.values()))<=1000000)
    extra=set(files)-{'manifest.json','mt-choice-worker.mjs','project-notices.txt'}
    need(len(extra)==1 and re.fullmatch(r'method-[a-f0-9]{64}[.]json',next(iter(extra)))is not None and {'manifest.json','mt-choice-worker.mjs','project-notices.txt'}<=set(files))
    publication={'started':False}if publication is None else publication
    started=False;staged=[]
    try:
        with Capture(path.parent)as parent:
            pi=os.fstat(parent.root);need(pi.st_uid==os.getuid() and not pi.st_mode&0o022)
            stable();parent.check()
            try:
                os.mkdir(path.name,0o755,dir_fd=parent.root);started=True;publication['started']=True
            except FileExistsError:pass
            except BaseException:
                started=True;publication['started']=True;raise
            with Capture(path)as output:
                fd=output.root;info=os.fstat(fd)
                need(info.st_uid==os.getuid() and not info.st_mode&0o022)
                need(set(os.listdir(fd))<=set(files))
                prior={}
                for name in files:
                    try:
                        st=os.stat(name,dir_fd=fd,follow_symlinks=False)
                        need(stat.S_ISREG(st.st_mode)and st.st_uid==os.getuid()and st.st_nlink==1 and st.st_size<=1000000)
                        prior[name]=snapshot(st)
                    except FileNotFoundError:prior[name]=None
                try:
                    for name,raw in sorted(files.items()):
                        need(type(raw)is bytes and 0<len(raw)<=500000)
                        tmp='.choice-'+secrets.token_hex(16);owned=None;rawfd=None
                        try:
                            rawfd=os.open(tmp,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o644,dir_fd=fd)
                            owned=identity(os.fstat(rawfd));staged.append((tmp,owned))
                            at=0
                            while at<len(raw):
                                n=os.write(rawfd,raw[at:]);need(n>0);at+=n
                            os.fsync(rawfd)
                        finally:
                            released=rawfd;rawfd=None
                            if released is not None:os.close(released)
                    stable();parent.check();output.check()
                    for (name,raw),(tmp,owned)in zip(sorted(files.items()),staged):
                        try:actual=snapshot(os.stat(name,dir_fd=fd,follow_symlinks=False))
                        except FileNotFoundError:actual=None
                        need(actual==prior[name] and identity(os.stat(tmp,dir_fd=fd,follow_symlinks=False))==owned)
                        started=True;publication['started']=True;os.replace(tmp,name,src_dir_fd=fd,dst_dir_fd=fd)
                    os.fsync(fd);stable();parent.check();output.check()
                finally:
                    error=None
                    for tmp,owned in staged:
                        try:
                            actual=os.stat(tmp,dir_fd=fd,follow_symlinks=False)
                            need(identity(actual)==owned);os.unlink(tmp,dir_fd=fd)
                        except FileNotFoundError:pass
                        except BaseException as exc:
                            if error is None:error=exc
                    if error is not None:raise BuildUncertain('Static output cleanup uncertain.')from None
    except BaseException:
        if started:raise BuildUncertain('Static output may remain; inspect before retrying.')from None
        raise


def _build(runtime, destination, root, publication):
    root=Path(root).absolute();default_destination=destination is None
    destination=Path(destination)if destination else root/'site/public/device/mt-choice'
    with Capture(root)as source, Capture(Path(runtime).resolve(strict=True))as cached:
        raw={}
        for name,digest in APPROVED_SOURCE.items():
            key=COHORT+'/'+name;raw[key]=source.read(key)
            need(sha(raw[key])==digest)
        key=COHORT+'/source.json';raw[key]=source.read(key);need(sha(raw[key])==COHORT_MANIFEST_SHA)
        raw[RUNTIME_POLICY]=source.read(RUNTIME_POLICY);need(sha(raw[RUNTIME_POLICY])==RUNTIME_POLICY_SHA)
        release=json.loads(raw[RUNTIME_POLICY]);need(release['pyodide_version']=='314.0.7'and release['python_version']=='3.14.2')
        need(set(release['runtime_members'])==set(RUNTIME_FILES))
        need(sum(p['bytes']for p in release['runtime_members'].values())<=32000000)
        for name in RUNTIME_FILES:
            pin=release['runtime_members'][name];need(type(pin['bytes'])is int and 0<pin['bytes']<=12000000)
            data=cached.read(name,12000000);need(len(data)==pin['bytes']and sha(data)==pin['sha256'])
        for name in BUILD_FILES:raw[name]=source.read(name)
        # Exact published source retains the Unicode data and applicable notices.
        expected=('// Generated; run scripts/generate-normalization.py. Unicode data license retained.\nconst TABLES = '+raw[COHORT+'/protocol/unicode15-data.json'].decode().strip()+';\n'+raw['protocol/normalization-core.js'].decode()+'\nexport { normalizeNFC, NORMALIZATION_ID };\n').encode()
        need(raw['protocol/normalization.mjs']==expected)
        bundle=(json.dumps({'format':'mt-choice-python-sources/v1','files':{p:raw[COHORT+'/'+p].decode('utf-8','strict')for p in METHOD_FILES}},ensure_ascii=True,sort_keys=True,separators=(',',':'))+'\n').encode();need(len(bundle)<=500000)
        bundle_name='method-'+sha(bundle)+'.json'
        manifest={'format':'mt-choice-modal-manifest/v1','runtime':'314.0.7','python_version':release['python_version'],'runtime_path':'/device/runtime-314.0.7/','runtime_files':release['runtime_members'],'method':'caller-bound-choice-framing-observation/1.3.0','normalization_id':'NFC-Unicode-15.0.0/v1','bundle':bundle_name,'bundle_sha256':sha(bundle),'bundle_bytes':len(bundle),'sources':{p:APPROVED_SOURCE[p]for p in METHOD_FILES},'source_commit':SOURCE_COMMIT,'build_inputs':{p:sha(data)for p,data in raw.items()},'experimental':True}
        notices=b'Published selected-wording reference sources and notices; no independent method/accuracy approval.\n\n'
        for name in ['LICENSE','NOTICE','eval/vectors/unicode/LICENSE.txt']:notices+=('=== '+name+' ===\n').encode()+raw[COHORT+'/'+name]+b'\n'
        files={bundle_name:bundle,'manifest.json':(json.dumps(manifest,indent=2)+'\n').encode(),'mt-choice-worker.mjs':raw['site/src/mt-choice-worker.mjs'],'project-notices.txt':notices}
        source.check();cached.check()
        if default_destination:
            # A clean checkout has no generated device directory. Create only
            # this fixed public parent, after all inputs passed, through a held
            # no-follow descriptor; explicit destinations keep existing parents.
            with Capture(root/'site/public')as public:
                info=os.fstat(public.root);need(info.st_uid==os.getuid()and not info.st_mode&0o022)
                try:
                    os.mkdir('device',0o755,dir_fd=public.root);publication['started']=True
                except FileExistsError:pass
                except BaseException:
                    publication['started']=True;raise
                child=public.child(public.root,'device');info=os.fstat(child)
                need(info.st_uid==os.getuid()and not info.st_mode&0o022);public.check()
        publish(destination,files,lambda:(source.check(),cached.check()),publication)
        return manifest

def build(runtime, destination=None, root=ROOT):
    # Publication ownership spans ALL outer source/runtime descriptor closes.
    # A close error may follow a completed close; never retry those descriptors
    # or call a committed build a normal pre-publication refusal.
    publication={'started':False}
    try:
        return _build(runtime,destination,root,publication)
    except BuildUncertain:
        raise
    except BaseException:
        if publication['started']:raise BuildUncertain('Static output may remain; inspect before retrying.')from None
        raise

class Parser(argparse.ArgumentParser):
    def error(self,_):raise BuildError('Selected wording source build unavailable.')

if __name__=='__main__':
    try:
        parser=Parser(description=__doc__,allow_abbrev=False)
        parser.add_argument('--runtime',default=os.environ.get('AITRUST_MT_CHOICE_RUNTIME',str(ROOT/'site/node_modules/pyodide')))
        parser.add_argument('--output');args=parser.parse_args()
        build(args.runtime,args.output);print('{"state":"STATIC_SOURCES_BUILT","experimental":true}')
    except BuildUncertain:
        print('{"state":"UNAVAILABLE","reason":"output_commit_uncertain","output_may_exist":true}',file=sys.stderr);raise SystemExit(2)
    except (ValueError,OSError,UnicodeError,RuntimeError,ImportError,RecursionError,KeyboardInterrupt):
        print('Selected wording static build unavailable.',file=sys.stderr);raise SystemExit(2)
