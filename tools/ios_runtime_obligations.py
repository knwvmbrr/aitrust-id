"""Exact iOS App/Share notice projection and selected-resource inspection.

This source-only helper does not sign, admit an IPA, execute publisher code,
interpret provisioning profiles, or validate a native UI. See the versioned plan.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import struct
import time
import zipfile
from tools import artifact_evidence_io as evidence
from tools import web_runtime_obligations as web

ROOT = Path(__file__).resolve().parents[1]
PROFILE = 'ios-runtime-obligations/v1'
MAX_READS, MAX_LOGICAL, MAX_FDS = 160, 64_000_000, 128
MAX_CACHE, MAX_OUTPUT, DEADLINE = 16_000_000, 8_000_000, 60
MAX_IPA, MAX_CENTRAL, MAX_ENTRIES = 64*1024**2, 262_144, 256
MAX_EXPANDED, MAX_MEMBER = 128*1024**2, 12*1024**2
DISK_FLOOR = 2*1024**3 + 128*1024**2
PINS = {
 'tools/web_runtime_obligations.py': (17553, '597ac7cc8f53750e723e1119076d63c3363e400e5a7c0ee65bb9cf2ccc52ba7b'),
 'tools/artifact_evidence_io.py': (12720, '2d8089a460d0b70c7725ce8bfdecda88b798c70d3335cfbb22c8fe5b31ea0b4e'),
 'LICENSE': (11358, 'cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30'),
 'NOTICE': (1134, 'e185f305c76f821aa56011cd201ea03f49e97c57dfc786517f77bfc00c7fecd6')}
MAPPING = {
 **{'device-licenses/'+n: 'Notices/'+n for n in (
 'pyodide-MPL-2.0.txt', 'python-license.txt', 'source.txt', 'unicode-license.txt', 'python-stdlib-notices.txt')},
 **{'runtime-js-sources/'+n: 'Notices/RuntimeJS/'+n for n in ('NOTICES.txt','index.json','PYODIDE-JS-SOURCES.zip')},
 **{'runtime-zlib-sources/'+n: 'Notices/RuntimeZlib/'+n for n in ('NOTICES.txt','index.json','ZLIB-SOURCES.zip')},
 **{'runtime-obligations/'+n: 'Notices/RuntimeEmbedded/'+n for n in ('NOTICES.txt','obligations.json','HIWIRE-SOURCES.zip')}}
SOURCE_OFFERS = b'''Bundled runtime notices and preferred source\n\nThis public material is available offline in both the app and Share checker.\nOpen Privacy & notices, then choose a notice or an explicit source ZIP action.\nA source action offers ONLY that bundled public ZIP through the system share\nsheet. It does not include your selected text, check result or original items.\nNothing is automatically saved, uploaded or checked by opening these notices.\n\nPyodide JavaScript and its CPython patches: RuntimeJS/PYODIDE-JS-SOURCES.zip\nZlib preferred source: RuntimeZlib/ZLIB-SOURCES.zip\nHiwire preferred source/build context: RuntimeEmbedded/HIWIRE-SOURCES.zip\nThese paths are relative to the bundled Notices folder, not web URLs. Existing\nsource.txt retains its original publisher/web context; use the actions above\nfor the local copies. No covered source was changed by this layout projection.\n\nProject-NOTICE.txt carries the full, unchanged repository attribution notice.\nIts Nunito font and SPDX schema references describe repository context; neither\nis a member of this PS-only native runtime. It is not an iOS component census.\nRuntimeEmbedded/NOTICES.txt and its companion index describe the selected\nCPython/Emscripten/external runtime notices. This finite carrying check does not\nprove compiler reproduction, complete binary closure, legal clearance, Apple\napproval, safety, accuracy, authorship or authenticity.\n'''
CLAIMS = {'distribution_route_admitted': False, 'signature_verified': False,
 'whole_ipa_inspected': False, 'native_ui_verified': False, 'legal_clearance': False,
 'accuracy_validated': False, 'compiler_reproduced': False}


class Unavailable(ValueError):
    def __init__(self): super().__init__('Selected iOS runtime carrying unavailable.')


class IncompleteCarrying(Unavailable):
    """A refused old cohort can expose counts, never a partial pass flag."""
    def __init__(self, missing):
        super().__init__()
        self.runtime_files_verified = 10
        self.missing_required_resources = missing


class OutputUncertain(Unavailable):
    output_may_exist = True
    def __init__(self): ValueError.__init__(self, 'Private runtime output may remain; inspect before retrying.')


def need(ok):
    if not ok: raise Unavailable()


def sha(raw): return hashlib.sha256(raw).hexdigest()
def row(raw): return {'bytes': len(raw), 'sha256': sha(raw)}
def encoded(value): return json.dumps(value, sort_keys=True, ensure_ascii=True, allow_nan=False, separators=(',', ':')).encode('ascii')


def safe(name, directory=False):
    need(type(name) is str and 0 < len(name) <= 256 and name.isascii())
    if directory and name.endswith('/'): name = name[:-1]
    need(not name.startswith('/') and '\\' not in name and '\x00' not in name
         and all(p and p not in ('.','..') for p in name.split('/'))
         and all(c.isalnum() or c in '._-/+ @~' for c in name))
    return name


class Budget:
    def __init__(self):
        self.started = time.monotonic()
        self.reads = self.logical = self.cache = self.peak_fds = 0
        self.archive_hash_bytes = self.selected_compressed_bytes = 0
        self.sources = {}
        self.directories = {}
        self.memberships = {}

    def tick(self): need(time.monotonic()-self.started < DEADLINE)
    def operation(self):
        self.tick(); need(self.reads < MAX_READS); self.reads += 1
    def charge(self, size):
        self.tick(); need(type(size) is int and size >= 0 and self.logical+size <= MAX_LOGICAL); self.logical += size
    def capacity(self, c, path, file=True):
        missing = sum(1 for i in range(1,len(Path(path).absolute().parts)) if Path(path).absolute().parts[:i] not in c.directory_cache)
        need(len(c.fds)+missing+int(file) <= MAX_FDS)
        self.peak_fds = max(self.peak_fds,len(c.fds)+missing+int(file))
    def remember(self, c):
        paths = {fd: Path(*parts) for parts,(fd,_) in c.directory_cache.items()}
        for parts,(_,identity) in c.directory_cache.items(): self.directories[Path(*parts)] = identity
        for parent,name,_,snapshot in c.files: self.sources[paths[parent]/name] = snapshot
    def recheck(self):
        self.tick()
        with evidence.Capture() as c:
            for path, expected in self.directories.items():
                if path == Path(path.anchor):
                    fd,_ = c.parent(path/'_relation',private=False)
                    need(evidence.identity(os.fstat(fd)) == expected)
                else:
                    self.capacity(c,path,file=False)
                    parent,name = c.parent(path,private=False)
                    need(evidence.identity(os.stat(name,dir_fd=parent,follow_symlinks=False)) == expected)
                self.tick()
            for path, expected in self.sources.items():
                self.capacity(c,path,file=False); parent,name = c.parent(path,private=False)
                need(evidence.snapshot(os.stat(name,dir_fd=parent,follow_symlinks=False)) == expected); self.tick()
            for path,expected in self.memberships.items():
                self.capacity(c,path,file=False); parent,name=c.parent(path,private=False)
                need(evidence.snapshot(os.stat(name,dir_fd=parent,follow_symlinks=False))==expected); self.tick()
            c.check(); self.tick()


def _project(root, b):
    root = Path(root).absolute(); own = {}
    need(Path(web.__file__).absolute() == root/'tools/web_runtime_obligations.py'
         and Path(evidence.__file__).absolute() == root/'tools/artifact_evidence_io.py')
    with evidence.Capture() as c:
        for name,(size,digest) in PINS.items():
            b.capacity(c,root/name); b.operation(); b.charge(size)
            raw = c.read(root/name,size,private=False); need(len(raw)==size and sha(raw)==digest)
            own[name] = raw
        c.check(); b.remember(c); b.tick()
    source = web.Budget(root)
    # The producer's own caps remain intact; the earlier outer deadline also
    # applies INSIDE its read/parse/generation operations, not only between calls.
    original_tick = source.tick
    def tick(): b.tick(); original_tick()
    source.tick = tick
    original_charge = source.charge
    def charge(size):
        b.operation(); b.charge(size); original_charge(size)
    source.charge = charge
    try:
        m = source.initialize(); outputs = web.expected(source,m); source.finish()
        need(set(outputs)==set(MAPPING))
        need(b.reads <= MAX_READS)
        b.cache = source.cache_bytes + sum(map(len,own.values()))
        b.peak_fds = max(b.peak_fds,len(source.capture.fds)); need(b.peak_fds<=MAX_FDS)
        b.remember(source.capture)
        result = {MAPPING[name]:raw for name,raw in outputs.items()}
        result['Notices/Project-NOTICE.txt'] = own['NOTICE']
        result['Notices/SourceOffers.txt'] = SOURCE_OFFERS
        index = {'profile': PROFILE,'runtime_manifest_sha256': web.MANIFEST_SHA256,
            'runtime': m['runtime'],'source_layout': MAPPING,
            'resources': {n:row(raw) for n,raw in sorted(result.items())},'claims': CLAIMS}
        result['Notices/native-runtime-index.json'] = encoded(index)+b'\n'
        need(len(result)==17 and sum(map(len,result.values()))<=MAX_OUTPUT)
        # Conservative live payload accounting, not measured RSS. Source cached
        # bytes, projected bytes, central/tail, stream and duplicate-encoding headroom.
        reservation = web.PAYLOAD_RESERVATION + 262144 + 65557 + 2*65536
        need(reservation <= 128_000_000 and b.cache<=MAX_CACHE)
        b.tick()
        return result,own['LICENSE'],m['runtime']
    finally: source.close()


def _report(b, notices, received=0, artifact=None):
    b.tick()
    return {'profile':PROFILE,'pass':True,'required_notices':17,'source_offers':3,
        'received_files_verified':received,'selected_scope_only':True,
        'notices':{n:row(raw) for n,raw in sorted(notices.items())},
        'artifact':artifact,'claims':CLAIMS.copy(),
        'resources':{'logical_operations':b.reads,'logical_read_bytes':b.logical,
          'cached_source_bytes':b.cache,'peak_held_fds':b.peak_fds,
          'whole_archive_hash_bytes':b.archive_hash_bytes,
          'selected_compressed_bytes':b.selected_compressed_bytes,
          'physical_compressed_io_excluded_from_logical_bytes':True}}


def boundary(function):
    def run(*args,**kwargs):
        try: return function(*args,**kwargs)
        except (Unavailable,OutputUncertain): raise
        except Exception: raise Unavailable() from None
    return run


@boundary
def projection(root=ROOT):
    """Trusted source-only payload; no dependency installation or output writes."""
    b=Budget(); notices,license_raw,_=_project(root,b); b.recheck()
    return {'notices':notices,'license':license_raw,'report':_report(b,notices)}


def _open(c,path,b,limit):
    b.capacity(c,path); parent,name=c.parent(path,private=False)
    fd=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=parent); c.fds.append(fd)
    info=os.fstat(fd)
    need(stat.S_ISREG(info.st_mode) and info.st_nlink==1 and 0<info.st_size<=limit)
    c.files.append((parent,name,fd,evidence.snapshot(info)))
    return fd,info


def _hash(fd,size,b,archive=False):
    digest=hashlib.sha256(); length=0
    while length<size:
        b.tick(); chunk=os.pread(fd,min(65536,size-length),length); need(chunk)
        length+=len(chunk); digest.update(chunk)
        if not archive: b.charge(len(chunk))
    need(not os.pread(fd,1,size)); b.tick()
    if archive: b.archive_hash_bytes+=length; need(b.archive_hash_bytes<=2*MAX_IPA)
    return {'bytes':length,'sha256':digest.hexdigest()}


def _members(c,base,names,b):
    """Exact finite selected subtree; no unbounded rglob/entry list."""
    groups={}
    for name in names:
        parts=name.split('/')
        for i,part in enumerate(parts): groups.setdefault('/'.join(parts[:i]),set()).add(part)
    for parent,wanted in groups.items():
        directory=base/parent; b.capacity(c,directory/'_membership',file=False)
        fd,_=c.parent(directory/'_membership',private=False)
        need(len(c.fds)+1<=MAX_FDS); b.peak_fds=max(b.peak_fds,len(c.fds)+1)
        before=evidence.snapshot(os.fstat(fd))
        need(b.memberships.setdefault(directory,before)==before)
        seen=set()
        with os.scandir(fd) as entries:
            for entry in entries:
                b.tick(); need(entry.name in wanted and entry.name not in seen and len(seen)<len(wanted)); seen.add(entry.name)
        need(seen==wanted and evidence.snapshot(os.fstat(fd))==before)


def _target_identity(c,base,b):
    b.capacity(c,base/'_target',file=False)
    fd,_=c.parent(base/'_target',private=False)
    info=os.fstat(fd)
    return info.st_dev,info.st_ino


def _wanted(notices,license_raw,runtime):
    return {**{n:row(raw) for n,raw in notices.items()},
      **{'Assets/runtime/'+n:meta for n,meta in runtime.items()},'AppLicense.txt':row(license_raw)}


@boundary
def check_directories(app,share,root=ROOT):
    b=Budget(); notices,license_raw,runtime=_project(root,b); wanted=_wanted(notices,license_raw,runtime)
    need(Path(app).absolute()!=Path(share).absolute())
    targets=(Path(app).absolute(),Path(share).absolute());identities=set()
    for base in targets:
        with evidence.Capture() as c:
            identity=_target_identity(c,base,b);need(identity not in identities);identities.add(identity)
            for group in ('Notices','Assets/runtime'):
                _members(c,base/group,{n.removeprefix(group+'/') for n in wanted if n.startswith(group+'/')},b)
            for name,expected in sorted(wanted.items()):
                b.operation(); fd,info=_open(c,base/name,b,min(MAX_MEMBER,expected['bytes']))
                need(info.st_size==expected['bytes'] and _hash(fd,info.st_size,b)==expected)
            for group in ('Notices','Assets/runtime'):
                _members(c,base/group,{n.removeprefix(group+'/') for n in wanted if n.startswith(group+'/')},b)
            c.check(); b.remember(c); b.tick()
    # Revisit each exact selected tree after both byte-reading phases, then
    # check all original file and membership snapshots with fresh nofollow FDs.
    for base in targets:
        with evidence.Capture() as c:
            for group in ('Notices','Assets/runtime'):
                _members(c,base/group,{n.removeprefix(group+'/') for n in wanted if n.startswith(group+'/')},b)
            c.check(); b.tick()
    b.recheck(); return _report(b,notices,46)


def _central(fd,size,b):
    """Bound central allocation/count BEFORE constructing stdlib ZipFile."""
    tail=os.pread(fd,min(size,65557),max(0,size-65557)); b.tick()
    at=tail.rfind(b'PK\x05\x06'); need(at>=0 and at+22<=len(tail))
    sig,disk,start_disk,disk_count,count,cdsize,offset,comment=struct.unpack_from('<4s4H2LH',tail,at)
    eocd=size-len(tail)+at
    need(disk==start_disk==0 and disk_count==count and 0<count<=MAX_ENTRIES
      and count!=65535 and offset!=0xffffffff and cdsize!=0xffffffff
      and 0<cdsize<=MAX_CENTRAL and comment<=4096 and at+22+comment==len(tail)
      and offset+cdsize==eocd)
    raw=os.pread(fd,cdsize,offset); need(len(raw)==cdsize)
    result={}; pos=0; expanded=0
    while pos<len(raw):
        b.tick(); need(len(result)<count and pos+46<=len(raw))
        fields=struct.unpack_from('<4s6H3L5H2L',raw,pos)
        need(fields[0]==b'PK\x01\x02')
        flags,method,crc,compressed,decoded=fields[3],fields[4],fields[7],fields[8],fields[9]
        nl,el,cl,entrydisk,external,local=fields[10],fields[11],fields[12],fields[13],fields[15],fields[16]
        end=pos+46+nl+el+cl
        need(0<nl<=256 and el<=1024 and cl<=1024 and end<=len(raw)
          and entrydisk==0 and not flags&1 and method in (0,8)
          and decoded!=0xffffffff and compressed!=0xffffffff and local!=0xffffffff and local<offset)
        name=raw[pos+46:pos+46+nl].decode('ascii'); safe(name,directory=True)
        need(name not in result)
        mode=external>>16; need(not stat.S_ISLNK(mode) and (stat.S_IFMT(mode) in (0,stat.S_IFREG,stat.S_IFDIR)))
        extra=raw[pos+46+nl:pos+46+nl+el]; i=0
        while i<len(extra):
            need(i+4<=len(extra)); kind,length=struct.unpack_from('<HH',extra,i); i+=4
            need(kind!=1 and i+length<=len(extra)); i+=length
        expanded+=decoded; need(expanded<=MAX_EXPANDED)
        need(decoded==0 or (compressed>0 and decoded<=compressed*512))
        result[name]=(decoded,compressed,crc,flags,method,external,local); pos=end
    need(pos==cdsize and len(result)==count); return result


@boundary
def check_ipa(path,root=ROOT):
    b=Budget(); notices,license_raw,runtime=_project(root,b); wanted=_wanted(notices,license_raw,runtime)
    with evidence.Capture() as c:
        b.operation(); fd,info=_open(c,Path(path).absolute(),b,MAX_IPA)
        observed=_hash(fd,info.st_size,b,archive=True); central=_central(fd,info.st_size,b)
        # Some producers omit directory entries; derive roots from member paths.
        roots={n.split('/')[1] for n in central if n.startswith('Payload/') and len(n.split('/'))>2 and n.split('/')[1].endswith('.app')}
        need(len(roots)==1); app='Payload/'+next(iter(roots))+'/'
        shares={n[len(app):].split('/')[1] for n in central if n.startswith(app+'PlugIns/') and len(n[len(app):].split('/'))>2 and n[len(app):].split('/')[1].endswith('.appex')}
        need(len(shares)==1); share=app+'PlugIns/'+next(iter(shares))+'/'
        selected={prefix+name:expected for prefix in (app,share) for name,expected in wanted.items()}
        for name in central:
            for prefix in (app,share):
                relative=name.removeprefix(prefix) if name.startswith(prefix) else ''
                if relative.startswith(('Notices/','Assets/runtime/')) and not name.endswith('/'):
                    need(name in selected)
        missing = set(selected)-set(central)
        # Always require the ten exact runtime files; absence of new notices is
        # a carrying refusal, not an alteration or a promoted partial success.
        need(not any('/Assets/runtime/' in n for n in missing))
        need(len(c.fds)+1<=MAX_FDS); b.peak_fds=max(b.peak_fds,len(c.fds)+1)
        duplicate=os.dup(fd)
        try:
            stream=os.fdopen(duplicate,'rb'); duplicate=None
            with stream,zipfile.ZipFile(stream,'r',allowZip64=False) as z:
                need(len(z.infolist())==len(central))
                for entry in z.infolist():
                    need((entry.file_size,entry.compress_size,entry.CRC,entry.flag_bits,entry.compress_type,entry.external_attr,entry.header_offset)==central[entry.filename])
                for name,expected in sorted(selected.items()):
                    if name in missing: continue
                    b.operation(); entry=z.getinfo(name)
                    need(0<entry.file_size<=MAX_MEMBER and entry.file_size==expected['bytes'])
                    b.selected_compressed_bytes+=entry.compress_size; need(b.selected_compressed_bytes<=MAX_IPA)
                    h=hashlib.sha256(); length=0
                    with z.open(entry,'r') as member:
                        while True:
                            b.tick(); chunk=member.read(min(65536,expected['bytes']+1-length))
                            if not chunk: break
                            length+=len(chunk); b.charge(len(chunk)); need(length<=expected['bytes']); h.update(chunk)
                    need(length==expected['bytes'] and h.hexdigest()==expected['sha256'])
        finally:
            if duplicate is not None: os.close(duplicate)
        need(_hash(fd,info.st_size,b,archive=True)==observed); c.check(); b.tick()
    b.recheck()
    if missing: raise IncompleteCarrying(len(missing))
    return _report(b,notices,46,observed)


@boundary
def prepare(destination,root=ROOT):
    b=Budget(); notices,_,_=_project(root,b); attempted=False; c=evidence.Capture()
    try:
        target=Path(destination).absolute(); b.capacity(c,target/'_private',file=False)
        parent,leaf=c.parent(target)
        need(shutil.disk_usage(target.parent).free>=DISK_FLOOR); b.tick()
        try: os.stat(leaf,dir_fd=parent,follow_symlinks=False)
        except FileNotFoundError: pass
        else: raise Unavailable()
        b.recheck(); attempted=True; os.mkdir(leaf,0o700,dir_fd=parent); c.directory(target)
        for group in sorted({str(Path(n).parent) for n in notices}):
            current=target
            for part in Path(group).parts:
                next_path=current/part; held,name=c.parent(next_path)
                try: os.mkdir(name,0o700,dir_fd=held)
                except FileExistsError: pass
                c.directory(next_path); current=next_path
        for name,raw in sorted(notices.items()):
            b.tick(); b.capacity(c,target/name); held,leaf=c.parent(target/name)
            out=os.open(leaf,os.O_RDWR|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=held)
            c.fds.append(out)  # Capture owns it immediately, including write faults.
            offset=0
            while offset<len(raw):
                count=os.write(out,raw[offset:offset+65536]); need(count>0); offset+=count; b.tick()
            b.operation(); b.charge(len(raw))
            evidence.verify_written(out,raw); os.fsync(out)
            final=os.fstat(out)
            need(final.st_nlink==1 and stat.S_IMODE(final.st_mode)==0o600 and final.st_uid==os.getuid())
            c.files.append((held,leaf,out,evidence.snapshot(final)))
        for parts,(fd,_) in c.directory_cache.items():
            if Path(*parts).is_relative_to(target): os.fsync(fd)
        c.check(); b.recheck(); b.tick(); result=_report(b,notices)
        c.close(); b.tick(); return result
    except BaseException:
        if attempted: raise OutputUncertain() from None
        raise
    finally:
        try: c.close()
        except BaseException:
            if attempted: raise OutputUncertain() from None
            raise
