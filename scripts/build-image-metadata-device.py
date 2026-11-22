#!/usr/bin/env python3
"""Capture the exact published image metadata methods; build static assets without executing it.

The descriptor Capture primitive derives from the reviewed published standalone
builder. This adaptation publishes only this fixed owned static namespace; a
failed multi-file publication is uncertain, never treated as an accepted build.
"""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import stat
import sys

ROOT=Path(__file__).absolute().parents[1]
COHORT='integrations/image-metadata-reference/1.0.0'
SOURCE_COMMIT='8e1b1a23a1bef0659bf1ec567ceef647b5cd76a5'
RUNTIME_POLICY='sbom/nested-runtime/pyodide-wasm-release.json'
RUNTIME_POLICY_SHA='fda0196c527b3920744261e27ac93cb71637ad36cf127e450aeaf49f425dd86f'
RUNTIME_FILES=('pyodide.mjs','pyodide.asm.mjs','pyodide.asm.wasm','python_stdlib.zip','pyodide-lock.json')
BUILD_FILES=('scripts/build-image-metadata-device.py','site/src/image-metadata-client.mjs','site/src/image-metadata-result.mjs','site/src/image-metadata-worker.mjs')
APPROVED_SOURCE={'tools/png_metadata.py': 'addd35028617f2d5c2cd01dc19106cec9946686cfe35139beb923af3973d6994', 'tools/jpeg_metadata.py': 'c7e8fcb58acd2087a35c886a32b7df1fa390c74c52c023e9b137bdf1dd90872a', 'LICENSE': 'cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30', 'NOTICE': 'e185f305c76f821aa56011cd201ea03f49e97c57dfc786517f77bfc00c7fecd6'}
COHORT_MANIFEST_SHA='3e66d919b4a6a289772266bd5cf5f6bfbfe9b144caf490b30c7c63dec902feeb'
PROJECTION_MANIFEST_SHA='1b52bfa875ae2bbc638aca600c49ceb66e2eb6d73cff5755db2e32720cfe1dea'
PROJECTION_MODULE_SHA={'png': '2b7ab18234c672eb703ba31535035a5d44b3709e70ddae28439596ab9ac55a91', 'jpeg': '6fc21838560e78eeb235ced484643edde274ed5717655bf8ef6767fc255a466c'}

class BuildError(ValueError):pass
class BuildUncertain(BuildError):pass

def need(ok):
    if not ok:raise BuildError('Image metadata source build unavailable.')

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
        if error is not None:raise BuildError('Image source cleanup unavailable.')from None
    def __enter__(self):return self
    def __exit__(self,*_):self.close()


def publish(destination, files, stable, publication=None):
    path=Path(destination).absolute();need('..'not in path.parts)
    need(len(files)==4 and sum(map(len,files.values()))<=1000000)
    extra=set(files)-{'manifest.json','image-metadata-worker.mjs','project-notices.txt'}
    need(len(extra)==1 and re.fullmatch(r'method-[a-f0-9]{64}[.]json',next(iter(extra)))is not None and {'manifest.json','image-metadata-worker.mjs','project-notices.txt'}<=set(files))
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
                        tmp='.image-'+secrets.token_hex(16);owned=None;rawfd=None
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


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode('ascii')

def node_name(node):
    if isinstance(node,(ast.FunctionDef,ast.ClassDef)):return node.name
    if isinstance(node,ast.Assign):
        need(all(isinstance(t,ast.Name)for t in node.targets));return ','.join(t.id for t in node.targets)
    if isinstance(node,ast.Import):return ','.join(a.name for a in node.names)
    if isinstance(node,ast.ImportFrom):return (node.module or '')+':'+','.join(a.name for a in node.names)
    if isinstance(node,ast.Expr)and isinstance(node.value,ast.Constant)and isinstance(node.value.value,str):return '__doc__'
    raise BuildError('Image projection unavailable.')

def project(raw,spec,kind):
    need(kind in ('png','jpeg')and sha(canonical(spec))==PROJECTION_MODULE_SHA[kind])
    need(type(raw)is bytes and sha(raw)==APPROVED_SOURCE['tools/'+kind+'_metadata.py']==spec['source_sha256'])
    text=raw.decode('utf-8','strict');nodes=ast.parse(text).body;need(len(nodes)==len(spec['nodes']))
    parts=[]
    for index,(node,entry)in enumerate(zip(nodes,spec['nodes'])):
        segment=ast.get_source_segment(text,node);need(type(segment)is str)
        actual={'index':index,'kind':type(node).__name__,'name':node_name(node),'sha256':sha(segment.encode()),'include':entry['include']}
        need(actual==entry and type(entry['include'])is bool)
        if entry['include']:parts.append(segment)
    result=('\n\n'.join(parts)+'\n').encode();need(len(result)==spec['projection_bytes']and sha(result)==spec['projection_sha256'])
    return result

def _build(runtime,destination,root,publication):
    root=Path(root).absolute();default=destination is None
    destination=Path(destination)if destination else root/'site/public/device/image-metadata'
    with Capture(root)as source,Capture(Path(runtime).resolve(strict=True))as cached:
        raw={}
        for name,digest in APPROVED_SOURCE.items():
            key=COHORT+'/'+name;raw[key]=source.read(key);need(sha(raw[key])==digest)
        for name,digest in [('source.json',COHORT_MANIFEST_SHA),('projection.json',PROJECTION_MANIFEST_SHA)]:
            key=COHORT+'/'+name;raw[key]=source.read(key);need(sha(raw[key])==digest)
        projection=json.loads(raw[COHORT+'/projection.json'])
        need(projection['format']=='image-metadata-fixed-projection/v1'and projection['source_commit']==SOURCE_COMMIT and set(projection['modules'])=={'png','jpeg'})
        projected={kind:project(raw[COHORT+'/tools/'+kind+'_metadata.py'],projection['modules'][kind],kind).decode()for kind in ('png','jpeg')}
        raw[RUNTIME_POLICY]=source.read(RUNTIME_POLICY);need(sha(raw[RUNTIME_POLICY])==RUNTIME_POLICY_SHA)
        release=json.loads(raw[RUNTIME_POLICY]);need(release['pyodide_version']=='314.0.7'and release['python_version']=='3.14.2'and set(release['runtime_members'])==set(RUNTIME_FILES))
        need(sum(p['bytes']for p in release['runtime_members'].values())<=32000000)
        for name in RUNTIME_FILES:
            pin=release['runtime_members'][name];need(type(pin['bytes'])is int and 0<pin['bytes']<=12000000)
            data=cached.read(name,12000000);need(len(data)==pin['bytes']and sha(data)==pin['sha256'])
        for name in BUILD_FILES:raw[name]=source.read(name)
        bundle=canonical({'format':'image-metadata-projected-python/v1','files':projected})+b'\n';need(len(bundle)<=200000)
        name='method-'+sha(bundle)+'.json'
        manifest={'format':'image-metadata-device-manifest/v1','source_commit':SOURCE_COMMIT,'runtime':'314.0.7','python_version':release['python_version'],'runtime_path':'/device/runtime-314.0.7/','runtime_files':release['runtime_members'],'bundle':name,'bundle_sha256':sha(bundle),'bundle_bytes':len(bundle),'parsers':{kind:{'source_sha256':APPROVED_SOURCE['tools/'+kind+'_metadata.py'],'projection_sha256':projection['modules'][kind]['projection_sha256'],'projection_bytes':projection['modules'][kind]['projection_bytes'],'profile':'png-metadata-preflight/1.0.0'if kind=='png'else'jpeg-metadata-observation/1.0.0'}for kind in ('png','jpeg')},'max_input_bytes':10485760,'build_inputs':{p:sha(v)for p,v in raw.items()},'experimental':True}
        notices=b'Exact selected image metadata source projections; not origin, validity or accuracy verification.\n\n'
        for key in ['LICENSE','NOTICE']:notices+=('=== '+key+' ===\n').encode()+raw[COHORT+'/'+key]+b'\n'
        files={name:bundle,'manifest.json':json.dumps(manifest,indent=2).encode()+b'\n','image-metadata-worker.mjs':raw['site/src/image-metadata-worker.mjs'],'project-notices.txt':notices}
        source.check();cached.check()
        if default:
            with Capture(root/'site/public')as public:
                info=os.fstat(public.root);need(info.st_uid==os.getuid()and not info.st_mode&0o022)
                try:os.mkdir('device',0o755,dir_fd=public.root);publication['started']=True
                except FileExistsError:pass
                except BaseException:publication['started']=True;raise
                fd=public.child(public.root,'device');info=os.fstat(fd);need(info.st_uid==os.getuid()and not info.st_mode&0o022);public.check()
        publish(destination,files,lambda:(source.check(),cached.check()),publication)
        return manifest

def build(runtime,destination=None,root=ROOT):
    publication={'started':False}
    try:return _build(runtime,destination,root,publication)
    except BuildUncertain:raise
    except BaseException:
        if publication['started']:raise BuildUncertain('Static image output may remain; inspect before retrying.')from None
        raise

class Parser(argparse.ArgumentParser):
    def error(self,_):raise BuildError('Image source build unavailable.')

if __name__=='__main__':
    try:
        parser=Parser(description=__doc__,allow_abbrev=False)
        parser.add_argument('--runtime',default=os.environ.get('AITRUST_IMAGE_RUNTIME',str(ROOT/'site/node_modules/pyodide')))
        parser.add_argument('--output');args=parser.parse_args()
        build(args.runtime,args.output);print('{"state":"STATIC_SOURCES_BUILT","experimental":true}')
    except BuildUncertain:
        print('{"state":"UNAVAILABLE","reason":"output_commit_uncertain","output_may_exist":true}',file=sys.stderr);raise SystemExit(2)
    except (ValueError,OSError,UnicodeError,RuntimeError,ImportError,RecursionError,KeyboardInterrupt):
        print('Image metadata static build unavailable.',file=sys.stderr);raise SystemExit(2)
