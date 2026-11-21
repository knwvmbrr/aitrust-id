#!/usr/bin/env python3
"""Build a new standalone local practice from captured sources and cached runtime."""
import argparse
import copy
import xml.etree.ElementTree as ET
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import stat
import sys

ROOT=Path(__file__).absolute().parents[1]
sys.path.insert(0,str(ROOT))
SOURCES=('tools/mt_choice_device.py','tools/choice_framing.py','tools/language_observations.py',
         'protocol/corpus.py','protocol/normalization.py','protocol/unicode15-data.json')
UI=('mt-choice-practice.html','mt-choice-practice.css','mt-choice-practice.mjs',
    'mt-choice-client.mjs','mt-choice-result.mjs','mt-choice-worker.mjs')
LICENSES=('LICENSE','NOTICE','eval/vectors/unicode/LICENSE.txt')
STATIC=('protocol/normalization-core.js','protocol/normalization.mjs','site/public/camo-q4.svg',
        'docs/mt-choice-browser.md','docs/choice-framing.md','sbom/nested-runtime/pyodide-wasm-release.json',
        'sbom/assets/notices.json','site/package-lock.json','tools/pyodide_js_sources.py',
        'tools/zlib_source_delivery.py','tools/dependency_policy.py','eval/dependency-policy.json',
        'scripts/build-mt-choice-practice.py')
RUNTIME=('pyodide.mjs','pyodide.asm.mjs','pyodide.asm.wasm','python_stdlib.zip','pyodide-lock.json')

class BuildError(ValueError):pass
class BuildUncertain(BuildError):pass

def need(ok):
    if not ok:raise BuildError('Practice build inputs or destination unavailable.')

def sha(raw):return hashlib.sha256(raw).hexdigest()
def identity(i):return i.st_dev,i.st_ino,i.st_mode

def snapshot(i):return(*identity(i),i.st_nlink,i.st_size,i.st_mtime_ns,i.st_ctime_ns)


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


def publish(destination,files,stable,publication):
    need(0<len(files)<=40 and sum(map(len,files.values()))<=32000000)
    path=Path(destination).absolute();need('..'not in path.parts)
    with Capture(path.parent)as parent_capture:
        parent=parent_capture.root;pi=os.fstat(parent);need(pi.st_uid==os.getuid()and not stat.S_IMODE(pi.st_mode)&0o022)
        stable();parent_capture.check()
        try:os.mkdir(path.name,0o700,dir_fd=parent)
        except FileExistsError:raise BuildError('Practice output already exists.')from None
        except BaseException:publication['started']=True;raise
        publication['started']=True;fds=[];dirs=[];owned=[];complete=False
        try:
            base=os.open(path.name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=parent);fds.append(base)
            base_id=identity(os.fstat(base));dirs.append((parent,path.name,base,base_id));cache={'':base}
            for name,raw in sorted(files.items()):
                parts=name.split('/');need(all(p not in ('','.','..')for p in parts)and len(parts)<=3 and type(raw)is bytes and len(raw)<=12000000)
                prefix='';fd=base
                for part in parts[:-1]:
                    key=prefix+'/'+part
                    if key not in cache:
                        os.mkdir(part,0o700,dir_fd=fd);child=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd);fds.append(child)
                        dirs.append((fd,part,child,identity(os.fstat(child))));cache[key]=child
                    fd=cache[key];prefix=key
                leaf=parts[-1];out=os.open(leaf,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=fd);fds.append(out)
                owned.append((fd,leaf,None));owned[-1]=(fd,leaf,identity(os.fstat(out)))
                at=0
                while at<len(raw):written=os.write(out,memoryview(raw)[at:]);need(written>0);at+=written
                os.fsync(out);need(os.fstat(out).st_size==len(raw))
            stable();parent_capture.check()
            for par,name,fd,expected in dirs:need(identity(os.fstat(fd))==expected==identity(os.stat(name,dir_fd=par,follow_symlinks=False)));os.fsync(fd)
            os.fsync(parent);complete=True
        except BaseException:
            for par,name,expected in reversed(owned):
                try:
                    if expected is not None and identity(os.stat(name,dir_fd=par,follow_symlinks=False))==expected:os.unlink(name,dir_fd=par)
                except OSError:pass
            for par,name,fd,expected in reversed(dirs):
                try:
                    if identity(os.stat(name,dir_fd=par,follow_symlinks=False))==expected:os.rmdir(name,dir_fd=par)
                except OSError:pass
            raise
        finally:
            error=None
            for fd in reversed(fds):
                try:os.close(fd)
                except BaseException as e:
                    if error is None:error=e
            if error is not None:raise BuildUncertain('Practice output may remain.')from None


def theme_images(raw):
    """Keep the actual brand paths, with no browser-dependent SVG view fragment."""
    need(len(raw)<=20000);tree=ET.fromstring(raw);namespace='http://www.w3.org/2000/svg'
    allowed={'svg','title','view','defs','path','g','use'}
    need(all(node.tag.rsplit('}',1)[-1]in allowed for node in tree.iter()))
    need(all(value.startswith('#woodland-')for node in tree.iter()for key,value in node.attrib.items()if key.rsplit('}',1)[-1]=='href'))
    definitions=[n for n in tree if n.tag=='{'+namespace+'}defs'];panels=[n for n in tree if n.tag=='{'+namespace+'}svg']
    need(len(definitions)==1 and len(panels)==2)
    ET.register_namespace('',namespace);result={}
    for name,panel in zip(['light','dark'],panels):
        output=ET.Element('{'+namespace+'}svg',{'width':'480','height':'320','viewBox':'0 0 480 320'})
        output.append(copy.deepcopy(definitions[0]))
        for node in panel:output.append(copy.deepcopy(node))
        result['camo-'+name+'.svg']=ET.tostring(output,encoding='utf-8')
    return result


def build(runtime,destination,root=ROOT):
    from tools import pyodide_js_sources as js_sources,zlib_source_delivery as zlib_sources
    publication={'started':False}
    try:
        with ExitStack()as stack:
            capture=stack.enter_context(Capture(root));rt=stack.enter_context(Capture(runtime))
            names=[*SOURCES,*LICENSES,*STATIC,*('site/src/'+n for n in UI),*('site/public/device-licenses/'+n for n in ['pyodide-MPL-2.0.txt','python-license.txt','source.txt','unicode-license.txt'])]
            for prefix in ['sbom/reviews/pyodide-js','sbom/reviews/zlib-runtime']:
                count=0
                for path in sorted((Path(root)/prefix).rglob('*')):
                    count+=1;need(count<=128)
                    if path.is_file():names.append(path.relative_to(root).as_posix())
            captured={name:capture.read(name,12000000)for name in dict.fromkeys(names)}
            release=json.loads(captured['sbom/nested-runtime/pyodide-wasm-release.json'])
            need(release['pyodide_version']=='314.0.7');pinned=js_sources.reviewed_runtime(release['runtime_members'])
            runtime_files={name:rt.read(name,12000000)for name in RUNTIME}
            need(all(len(raw)==pinned[name]['bytes']and sha(raw)==pinned[name]['sha256']for name,raw in runtime_files.items()))
            expected=('// Generated; run scripts/generate-normalization.py. Unicode data license retained.\nconst TABLES = '+captured['protocol/unicode15-data.json'].decode().strip()+';\n'+captured['protocol/normalization-core.js'].decode()+'\nexport { normalizeNFC, NORMALIZATION_ID };\n').encode()
            need(captured['protocol/normalization.mjs']==expected)
            bundle=(json.dumps({'format':'mt-choice-python-sources/v1','files':{p:captured[p].decode('utf-8','strict')for p in SOURCES}},ensure_ascii=True,sort_keys=True,separators=(',',':'))+'\n').encode();need(len(bundle)<=500000)
            bundle_name='method-'+sha(bundle)+'.json'
            manifest={'format':'mt-choice-practice-manifest/v1','runtime':'314.0.7','python_version':release['python_version'],'runtime_path':'./runtime/','runtime_files':pinned,'method':'caller-bound-choice-framing-observation/1.3.0','normalization_id':'NFC-Unicode-15.0.0/v1','bundle':bundle_name,'bundle_sha256':sha(bundle),'bundle_bytes':len(bundle),'sources':{p:sha(captured[p])for p in SOURCES},'build_inputs':{p:sha(v)for p,v in captured.items()},'experimental':True}
            files={n:captured['site/src/'+n]for n in UI if not n.endswith('.html')};files['index.html']=captured['site/src/mt-choice-practice.html']
            files.update({'normalization.mjs':captured['protocol/normalization.mjs'],'practice-guide.md':captured['docs/mt-choice-browser.md'],'cli-guide.md':captured['docs/choice-framing.md'],bundle_name:bundle,'manifest.json':(json.dumps(manifest,indent=2)+'\n').encode()})
            files.update(theme_images(captured['site/public/camo-q4.svg']))
            files.update({'runtime/'+name:raw for name,raw in runtime_files.items()})
            notices=b'AI Trust ID selected wording practice - project and Unicode notices\n\n'
            for name in LICENSES:notices+=('=== '+name+' ===\n').encode()+captured[name]+b'\n'
            files['licenses/project.txt']=notices
            for name in ['pyodide-MPL-2.0.txt','python-license.txt','source.txt','unicode-license.txt']:files['licenses/'+name]=captured['site/public/device-licenses/'+name]
            for prefix,values in [('runtime-js-sources',js_sources.outputs(root)),('runtime-zlib-sources',zlib_sources.outputs(root))]:files.update({prefix+'/'+name:raw for name,raw in values.items()})
            capture.check();rt.check();publish(destination,files,lambda:(capture.check(),rt.check()),publication)
        return manifest
    except BaseException:
        if publication['started']:raise BuildUncertain('Practice output may remain; inspect before retrying.')from None
        raise


class Parser(argparse.ArgumentParser):
    def error(self,_):raise BuildError('Practice build command refused.')

if __name__=='__main__':
    try:
        parser=Parser(description=__doc__,allow_abbrev=False);parser.add_argument('--runtime',required=True);parser.add_argument('--output',required=True);args=parser.parse_args()
        build(args.runtime,args.output);print('{"state":"PRACTICE_BUILT","experimental":true,"published":false}')
    except BuildUncertain:print('{"state":"UNAVAILABLE","reason":"output_commit_uncertain","output_may_exist":true}',file=sys.stderr);raise SystemExit(2)
    except (ValueError,OSError,UnicodeError,RuntimeError,ImportError,RecursionError):print('Practice build unavailable; no accepted artifact.',file=sys.stderr);raise SystemExit(2)
