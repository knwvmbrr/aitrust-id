#!/usr/bin/env python3
"""Build bounded exact-source HP input without importing captured source code."""
import hashlib
import json
import os
from pathlib import Path
import secrets
import stat
import sys

ROOT=Path(__file__).absolute().parents[1]
SOURCE_FILES=('tools/hp_device.py','tools/quantitative_observations.py','tools/language_observations.py',
 'protocol/normalization.py','protocol/unicode15-data.json','protocol/corpus.py')
METHOD='literal-quantitative-observations/1.0.1'
LICENSE_FILES=('LICENSE','NOTICE','eval/vectors/unicode/LICENSE.txt')
NORMALIZER_FILES=('protocol/normalization-core.js','protocol/normalization.mjs')
ALL_FILES=(*SOURCE_FILES,*LICENSE_FILES,*NORMALIZER_FILES)
MAX_SOURCE=200000


class HPBuildError(ValueError):pass

class OutputCommitUncertain(HPBuildError):
    output_may_exist=True
    def __init__(self):super().__init__('HP build output may exist; inspect before retrying.')

def need(ok):
    if not ok:raise HPBuildError('HP build inputs or destination unavailable.')


def identity(info):return info.st_dev,info.st_ino,info.st_mode

def snapshot(info):
    return (*identity(info),info.st_nlink,info.st_size,info.st_mtime_ns,info.st_ctime_ns)


class Capture:
    """Hold no-follow ancestor/source descriptors until final prepublication check."""
    def __init__(self,root):
        self.fds=[];self.directories=[];self.files=[];self.output_may_exist=False
        path=Path(root).absolute();need('..' not in path.parts)
        need(all(hasattr(os,n) for n in ('O_DIRECTORY','O_NOFOLLOW','O_NONBLOCK')))
        flags=os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW
        try:
            current=os.open(path.anchor,flags);self.fds.append(current)
            self.anchor=(current,identity(os.fstat(current)))
            for name in path.parts[1:]:current=self.child(current,name)
            self.root=current
        except BaseException:self.close();raise
    def child(self,parent,name,create=False):
        need(name not in ('','.','..') and '/' not in name)
        if create:
            try:os.mkdir(name,mode=0o755,dir_fd=parent)
            except FileExistsError:pass
        fd=os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=parent)
        self.fds.append(fd);info=os.fstat(fd);need(stat.S_ISDIR(info.st_mode))
        self.directories.append((parent,name,fd,identity(info)));return fd
    def parent(self,name,create=False):
        parts=name.split('/');need(all(p not in ('','.','..') for p in parts))
        fd=self.root
        for part in parts[:-1]:fd=self.child(fd,part,create)
        return fd,parts[-1]
    def read(self,name):
        parent,leaf=self.parent(name)
        fd=os.open(leaf,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=parent);self.fds.append(fd)
        before=os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and before.st_nlink==1 and 0<before.st_size<=MAX_SOURCE)
        chunks=[];remaining=MAX_SOURCE+1
        while remaining:
            raw=os.read(fd,remaining)
            if not raw:break
            chunks.append(raw);remaining-=len(raw)
        raw=b''.join(chunks);need(len(raw)==before.st_size and snapshot(os.fstat(fd))==snapshot(before))
        self.files.append((parent,leaf,fd,snapshot(before)));return raw
    def check(self):
        need(identity(os.fstat(self.anchor[0]))==self.anchor[1])
        for parent,name,fd,expected in self.directories:
            need(identity(os.fstat(fd))==expected and identity(os.stat(name,dir_fd=parent,follow_symlinks=False))==expected)
        for parent,name,fd,expected in self.files:
            need(snapshot(os.fstat(fd))==expected and snapshot(os.stat(name,dir_fd=parent,follow_symlinks=False))==expected)
    def close(self):
        owned=self.fds;self.fds=[];error=None
        for fd in reversed(owned):
            try:os.close(fd)
            except BaseException as failure:
                if error is None:error=failure
        if error is not None:
            if self.output_may_exist:raise OutputCommitUncertain() from None
            raise HPBuildError('HP build descriptor cleanup unavailable.') from None
    def __enter__(self):return self
    def __exit__(self,kind,value,traceback):
        try:self.close()
        except BaseException:
            if self.output_may_exist:raise OutputCommitUncertain() from None
            if kind is None:raise
            return False
        if kind is not None and self.output_may_exist:raise OutputCommitUncertain() from None


def publish(capture,outputs):
    """Stage all bytes, then recheck captured inputs before replacing any output."""
    pending=[]
    try:
        for name,raw in outputs:
            parent,leaf=capture.parent(name,create=True)
            try:
                info=os.stat(leaf,dir_fd=parent,follow_symlinks=False)
                need(stat.S_ISREG(info.st_mode) and info.st_nlink==1 and info.st_size<=1000000)
            except FileNotFoundError:pass
            temporary='.hp-build-'+secrets.token_hex(16)
            fd=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o644,dir_fd=parent)
            capture.fds.append(fd);pending.append((parent,temporary,leaf))
            with os.fdopen(fd,'wb',closefd=False) as handle:handle.write(raw);handle.flush();os.fsync(handle.fileno())
            capture.files.append((parent,temporary,fd,snapshot(os.fstat(fd))))
        capture.check()
        # Hash-addressed method first; active manifest last. Input refusal above
        # leaves every previous published output unchanged.
        for parent,temporary,leaf in pending:
            capture.output_may_exist=True
            os.replace(temporary,leaf,src_dir_fd=parent,dst_dir_fd=parent);os.fsync(parent)
    finally:
        cleanup_error=None
        for parent,temporary,_ in pending:
            try:os.unlink(temporary,dir_fd=parent)
            except FileNotFoundError:pass
            except BaseException as failure:
                if cleanup_error is None:cleanup_error=failure
        if cleanup_error is not None:
            if capture.output_may_exist:raise OutputCommitUncertain() from None
            raise HPBuildError('HP build temporary cleanup unavailable.') from None


def write(path,raw):
    # Kept as the bounded standalone output helper used by focused controls.
    path=Path(path).absolute()
    with Capture(path.parent) as capture:publish(capture,[(path.name,raw)])


def build(root=ROOT):
    with Capture(root) as capture:
        files={p:capture.read(p) for p in ALL_FILES}
        capture.check()
        expected=('// Generated; run scripts/generate-normalization.py. Unicode data license retained.\nconst TABLES = '+files['protocol/unicode15-data.json'].decode().strip()+';\n'+files['protocol/normalization-core.js'].decode()+'\nexport { normalizeNFC, NORMALIZATION_ID };\n').encode()
        need(files['protocol/normalization.mjs']==expected)
        sources={p:hashlib.sha256(raw).hexdigest() for p,raw in files.items()}
        value={'format':'hp-device-source-bundle/v1','files':{p:raw.decode('utf-8','strict') for p,raw in files.items()}}
        raw=(json.dumps(value,ensure_ascii=True,sort_keys=True,separators=(',',':'))+'\n').encode();need(len(raw)<=1000000)
        digest=hashlib.sha256(raw).hexdigest();path='/hp-device/method-'+digest+'.json'
        manifest={'format':'hp-device-source-manifest/v1','runtime':'314.0.7',
         'runtime_path':'/device/runtime-314.0.7/','path':path,'bundle_sha256':digest,
         'bundle_bytes':len(raw),'sources':sources,'method':METHOD,
         'normalization_id':'NFC-Unicode-15.0.0/v1','max_codepoints':8000,'max_bytes':32000}
        notices=b'AI Trust ID HP literal-detail explorer - original source notices\n\n'
        for name in LICENSE_FILES:notices+=('----- '+name+' -----\n').encode()+files[name]+b'\n'
        outputs=[('site/public'+path,raw),('site/public/hp-device/notices.txt',notices),
                 ('site/src/hp-device-manifest.json',(json.dumps(manifest,indent=2)+'\n').encode())]
        capture.check();publish(capture,outputs);return manifest


if __name__=='__main__':
    try:print(json.dumps(build(),sort_keys=True))
    except OutputCommitUncertain:
        print('{"state":"UNAVAILABLE","reason":"output_commit_uncertain","output_may_exist":true}',file=sys.stderr);raise SystemExit(2)
    except (ValueError,OSError,UnicodeError):
        print('HP build unavailable; source capture was not approved.',file=sys.stderr);raise SystemExit(2)
