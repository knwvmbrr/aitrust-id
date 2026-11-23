"""Closed static-web artifact facts and authenticated private materialization.

No distribution permission is issued here. Shared registry and genuine protected
producer/attestation remain independent. Publisher JS/source is never executed.
"""
import contextlib
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import stat
import struct
import threading
import time
import zlib

ROOT = Path(__file__).resolve().parents[1]
PROFILE = 'web-checker-artifact/v1'
BUILD_PROFILE = 'web-checker-build-observations/v1'
META = 'WEB-CHECKER-MANIFEST.json'
MAX_ARTIFACT = 64_000_000
MAX_FILES = MAX_MODULES = 2048
MAX_MEMBER = 12_000_000
MAX_RECORD = 2_000_000
MAX_PACKET = 16_000_000
MAX_ROOTS = 5_000_000
MAX_READ_CALLS = 8192
MAX_OWN_READ = 448_000_000
MAX_APPLICATION_READ = 1_200_000_000
MAX_FDS = 128
FALSE_CLAIMS = {'release_authorized': False, 'attestation_verified': False,
                'all_project_obligations_complete': False, 'compiler_reproduced': False,
                'legal_clearance': False, 'independent_accuracy_evidence': False}
RUNTIME_METHOD_SHA256 = '597ac7cc8f53750e723e1119076d63c3363e400e5a7c0ee65bb9cf2ccc52ba7b'
RUNTIME_MANIFEST_SHA256 = '5d662e2a8c1feeb35465370a01eab9a192c21b0d1eb5c60cbc7021c92e592184'
VIRTUAL_PROVIDERS = {'virtual:rolldown-runtime': 'rolldown',
 'virtual:vite-preload-helper': 'vite', 'virtual:vite-modulepreload': 'vite'}
GENERATOR_PACKAGES = {'node_modules/vite': '8.3.4',
 'node_modules/tailwindcss': '4.3.3', 'node_modules/rolldown': '1.2.13'}


class WebUnavailable(ValueError):
    def __init__(self): super().__init__('Selected web artifact unavailable.')


class WebOutputUncertain(WebUnavailable):
    output_may_exist = True
    def __init__(self): ValueError.__init__(self, 'Private web output may exist; inspect before retrying.')


def need(value):
    if not value: raise WebUnavailable()


def sha(raw): return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True,
                      allow_nan=False, separators=(',', ':')).encode('ascii')


def path_name(value):
    need(type(value) is str and 0 < len(value) <= 240 and value.isascii()
         and re.fullmatch(r'[A-Za-z0-9_.@+~/-]+', value)
         and not value.startswith('/')
         and all(p not in ('', '.', '..', '.git', 'node_modules') and not p.startswith('.env')
                 for p in value.split('/')))
    return value


def source_name(value):
    need(type(value) is str and 0 < len(value) <= 240 and value.isascii()
         and re.fullmatch(r'[A-Za-z0-9_.@+~/-]+', value)
         and not value.startswith('/') and all(p not in ('', '.', '..', '.git') and not p.startswith('.env') for p in value.split('/')))
    return value


def identity(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink, info.st_size,
            info.st_mtime_ns, info.st_ctime_ns)


class Ledger:
    def __init__(self, *, managed=False):
        self.started = time.monotonic(); self.deadline = self.started + (115 if managed else 60)
        self.calls = self.own_bytes = self.legacy_bytes = self.fds = self.peak_fds = self.nodes = 0
        self.output_attempted = False
        self.managed=managed;self.crypto_seconds=0.0;self.verifier_invoked=False
    def tick(self):
        now=time.monotonic()
        need(type(now)in(int,float)and self.started<=now<self.deadline
          and type(self.crypto_seconds)in(int,float)and 0<=self.crypto_seconds<=65
          and (not self.managed or now-self.started-self.crypto_seconds<60))
    def charge(self, size):
        self.tick(); need(type(size) is int and size >= 0 and self.calls < MAX_READ_CALLS
                          and self.own_bytes + size <= MAX_OWN_READ
                          and self.own_bytes + size + self.legacy_bytes <= MAX_APPLICATION_READ)
        self.calls += 1; self.own_bytes += size
    def reserve_auth(self, artifact_bytes):
        need(type(artifact_bytes) is int and 0 < artifact_bytes <= MAX_ARTIFACT)
        amount = 6*artifact_bytes + 338_000_000
        need(self.own_bytes + self.legacy_bytes + amount <= MAX_APPLICATION_READ)
        self.legacy_bytes += amount; self.tick()
    def adopt(self, fd):
        need(self.fds < MAX_FDS); self.fds += 1; self.peak_fds = max(self.peak_fds, self.fds)
        return fd
    def close(self, fd):
        old=signal.pthread_sigmask(signal.SIG_BLOCK,{signal.SIGALRM})
        try:
            self.fds -= 1; os.close(fd)
        finally: signal.pthread_sigmask(signal.SIG_SETMASK,old)


@contextlib.contextmanager
def original_deadline(ledger):
    """One main-thread work deadline; owned-child cleanup gets the final five seconds."""
    need(os.name == 'posix' and threading.current_thread() is threading.main_thread()
         and threading.active_count() == 1 and signal.getitimer(signal.ITIMER_REAL) == (0.0, 0.0))
    old = signal.getsignal(signal.SIGALRM)
    def expired(_signum, _frame): raise WebUnavailable()
    try:
        signal.signal(signal.SIGALRM, expired)
        signal.setitimer(signal.ITIMER_REAL, max(0.001, ledger.deadline-time.monotonic()))
        yield
    finally:
        try: signal.setitimer(signal.ITIMER_REAL, 0)
        finally: signal.signal(signal.SIGALRM, old)


def preflight_json(raw, ledger, limit=MAX_RECORD):
    """Bound structures/tokens before json.loads allocates an object graph."""
    need(type(raw) is bytes and 0 < len(raw) <= limit)
    at = depth = 0
    while at < len(raw):
        if at % 65536 == 0: ledger.tick()
        c = raw[at]
        if c in b' \r\n\t,:': at += 1; continue
        if c in b'{[':
            depth += 1; ledger.nodes += 1; need(depth <= 32 and ledger.nodes <= 100_000); at += 1; continue
        if c in b'}]': depth -= 1; need(depth >= 0); at += 1; continue
        ledger.nodes += 1; need(ledger.nodes <= 100_000)
        if c == 34:
            at += 1; start = at
            while at < len(raw):
                need(at-start <= 1_000_000)
                if raw[at] == 34: at += 1; break
                if raw[at] == 92:
                    at += 2
                else: need(raw[at] >= 32); at += 1
            else: raise WebUnavailable()
        else:
            start = at
            while at < len(raw) and raw[at] not in b' \r\n\t,:{}[]': at += 1
            need(0 < at-start <= 32)
    need(depth == 0); ledger.tick()


def parse(raw, ledger, limit=MAX_RECORD):
    preflight_json(raw, ledger, limit)
    def unique(rows):
        result = {}
        for key, value in rows:
            need(key not in result); result[key] = value
        return result
    value = json.loads(raw.decode('utf8'), object_pairs_hook=unique,
                       parse_constant=lambda _: need(False))
    ledger.tick(); return value


class FileTree:
    """Held root, sequential no-follow files, bounded scans and snapshot rechecks."""
    def __init__(self, root, ledger, *, private=False):
        self.root = Path(root).absolute(); self.ledger = ledger; self.private = private
        self.held = []; self.directories=[]; self.snapshots = {}; self.closed = False
        need('..' not in self.root.parts)
        try:
            fd = self._open(self.root.anchor, os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,owned=self.held)
            for part in self.root.parts[1:]:
                self._private(fd, owner=False)
                child = self._open(part, os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW, dir_fd=fd,owned=self.held)
                self.directories.append((fd,part,child));fd = child
            self.fd = fd; self._private(fd, owner=private)
        except BaseException:
            self.close(); raise
    def _open(self, *args, owned, **kwargs):
        need(self.ledger.fds < MAX_FDS); self.ledger.tick()
        previous=signal.pthread_sigmask(signal.SIG_BLOCK,{signal.SIGALRM})
        fd=None;registered=False;before=self.ledger.fds
        try:
            fd=os.open(*args,**kwargs)
            owned.append(fd);registered=True
            self.ledger.adopt(fd)
            return fd
        except BaseException:
            if registered:owned.pop()
            self.ledger.fds=before
            if fd is not None:os.close(fd)
            raise
        finally:signal.pthread_sigmask(signal.SIG_SETMASK,previous)
    def _private(self, fd, owner=False):
        if not self.private: return
        try: os.stat('.git', dir_fd=fd, follow_symlinks=False)
        except FileNotFoundError: pass
        else: raise WebUnavailable()
        if owner:
            s=os.fstat(fd);need(s.st_uid==os.getuid() and stat.S_IMODE(s.st_mode)==0o700)
    @contextlib.contextmanager
    def file(self, name, limit, *, expected_size=None, charge=True):
        source_name(name); parts=name.split('/');need(len(parts)<=16)
        need(self.ledger.fds+len(parts)<=MAX_FDS)
        owned=[];failure=None
        try:
            parent=self.fd
            for part in parts[:-1]:
                child=self._open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=parent,owned=owned)
                parent=child;self._private(parent,owner=self.private)
            fd=self._open(parts[-1],os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=parent,owned=owned)
            before=os.fstat(fd)
            need(stat.S_ISREG(before.st_mode) and before.st_nlink==1 and 0<=before.st_size<=limit
                 and (expected_size is None or before.st_size==expected_size))
            if charge:self.ledger.charge(before.st_size)
            yield fd,before
            need(identity(before)==identity(os.fstat(fd))==identity(os.stat(parts[-1],dir_fd=parent,follow_symlinks=False)))
            if name in self.snapshots:need(self.snapshots[name]==identity(before))
            self.snapshots[name]=identity(before)
        except BaseException as error:failure=error
        finally:
            while owned:
                fd=owned.pop()
                try:self.ledger.close(fd)
                except BaseException as error:
                    if failure is None:failure=error
            if failure is not None:raise WebUnavailable() from None
    def read(self,name,limit=2_000_000,*,expected=None):
        need(type(limit)is int and 0<limit<=MAX_MEMBER)
        with self.file(name,limit,expected_size=expected['bytes']if expected else None)as(fd,info):
            chunks=[];at=0
            while at<info.st_size:
                self.ledger.tick();block=os.read(fd,min(65536,info.st_size-at));need(block);chunks.append(block);at+=len(block)
            raw=b''.join(chunks)
            if expected:need(sha(raw)==expected['sha256'])
            return raw
    def describe(self,name,limit=MAX_MEMBER):
        h=hashlib.sha256();crc=0
        with self.file(name,limit)as(fd,info):
            at=0
            while at<info.st_size:
                self.ledger.tick();block=os.read(fd,min(65536,info.st_size-at));need(block);at+=len(block);h.update(block);crc=zlib.crc32(block,crc)
            return {'bytes':at,'sha256':h.hexdigest(),'crc32':crc,'mode':0o644}
    def inventory(self,max_files=MAX_FILES):
        result={};directories=0
        def walk(fd,prefix,depth):
            nonlocal directories
            need(depth<=16 and self.ledger.fds+1<=MAX_FDS)
            # scandir's temporary duplicated FD is explicitly owned for capacity.
            self.ledger.fds+=1;self.ledger.peak_fds=max(self.ledger.peak_fds,self.ledger.fds)
            try:
                with os.scandir(fd)as entries:
                    for entry in entries:
                        self.ledger.tick();name=prefix+entry.name;path_name(name)
                        info=entry.stat(follow_symlinks=False)
                        if stat.S_ISDIR(info.st_mode):
                            directories+=1;need(directories<=MAX_FILES)
                            owned=[]
                            try:
                                child=self._open(entry.name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd,owned=owned)
                                self._private(child,owner=self.private);walk(child,name+'/',depth+1)
                            finally:
                                while owned:self.ledger.close(owned.pop())
                        else:
                            need(stat.S_ISREG(info.st_mode) and info.st_nlink==1 and len(result)<max_files)
                            result[name]={'bytes':info.st_size,'mode':0o644}
            finally:self.ledger.fds-=1
        walk(self.fd,'',0);return result
    def check(self):
        self.ledger.tick()
        for name,expected in list(self.snapshots.items()):
            # Opening and checking identity is not an additional body read.
            with self.file(name,expected[4],expected_size=expected[4],charge=False)as(fd,info):
                need(identity(info)==expected)
        for parent,name,child in self.directories:
            a=os.fstat(child);b=os.stat(name,dir_fd=parent,follow_symlinks=False)
            need((a.st_dev,a.st_ino,a.st_mode)==(b.st_dev,b.st_ino,b.st_mode))
        for fd in self.held:self._private(fd,owner=fd==self.fd and self.private)
    def close(self):
        if self.closed:return
        self.closed=True;failure=None
        while self.held:
            fd=self.held.pop()
            try:self.ledger.close(fd)
            except BaseException as error:
                if failure is None:failure=error
        if failure is not None:raise WebUnavailable()from None
    def __enter__(self):return self
    def __exit__(self,*args):self.close()


def _write_all(fd, raw, ledger):
    at=0
    while at<len(raw):
        ledger.tick();count=os.write(fd,raw[at:at+65536]);need(count>0);at+=count


def _pread(fd, at, size, ledger):
    need(type(at)is int and at>=0 and type(size)is int and size>=0)
    ledger.charge(size);chunks=[];total=0
    while total<size:
        ledger.tick();raw=os.pread(fd,min(65536,size-total),at+total);need(raw)
        chunks.append(raw);total+=len(raw)
    return b''.join(chunks)


def _zip_local(name, row):
    raw=name.encode('ascii')
    return struct.pack('<4s5H3I2H',b'PK\x03\x04',20,0,0,0,33,row['crc32'],row['bytes'],row['bytes'],len(raw),0)+raw


def _zip_central(name,row,offset):
    raw=name.encode('ascii')
    return struct.pack('<4s6H3I5H2I',b'PK\x01\x02',788,20,0,0,0,33,row['crc32'],row['bytes'],row['bytes'],len(raw),0,0,0,0,0o100644<<16,offset)+raw


def canonical_archive(fd, rows, get_chunks, ledger):
    """Write canonical stored ZIP from already bound byte sources, no extraction."""
    need(type(rows)is dict and 0<len(rows)<=MAX_FILES+1)
    offset=payload=0;central=[]
    for name,row in sorted(rows.items()):
        path_name(name)
        need(set(row)=={'bytes','sha256','crc32','mode'}and type(row['bytes'])is int
             and 0<=row['bytes']<=MAX_MEMBER and row['mode']==0o644
             and type(row['mode'])is int and type(row['crc32'])is int and 0<=row['crc32']<=0xffffffff
             and type(row['sha256'])is str and re.fullmatch('[0-9a-f]{64}',row['sha256']))
        payload+=row['bytes'];need(payload<=MAX_ARTIFACT)
        head=_zip_local(name,row);end=offset+len(head)+row['bytes'];need(end<=MAX_ARTIFACT)
        central.append(_zip_central(name,row,offset));_write_all(fd,head,ledger)
        h=hashlib.sha256();crc=length=0
        for raw in get_chunks(name):
            need(type(raw)is bytes and 0<len(raw)<=65536 and length+len(raw)<=row['bytes'])
            length+=len(raw);h.update(raw);crc=zlib.crc32(raw,crc);_write_all(fd,raw,ledger)
        need(length==row['bytes']and h.hexdigest()==row['sha256']and crc==row['crc32'])
        offset=end
    central_bytes=sum(map(len,central));need(offset+central_bytes+22<=MAX_ARTIFACT)
    for raw in central:_write_all(fd,raw,ledger)
    _write_all(fd,struct.pack('<4s4H2IH',b'PK\x05\x06',0,0,len(rows),len(rows),central_bytes,offset,0),ledger)
    os.fsync(fd);need(os.fstat(fd).st_size==offset+central_bytes+22)
    return offset+central_bytes+22


def inspect_archive(fd, ledger, *, expected_manifest=None, hash_payload=True):
    """Bound central metadata before reading or allocating any member payload."""
    before=os.fstat(fd);need(stat.S_ISREG(before.st_mode)and before.st_nlink==1 and 22<=before.st_size<=MAX_ARTIFACT)
    end=_pread(fd,before.st_size-22,22,ledger)
    e=struct.unpack('<4s4H2IH',end)
    need(e[0]==b'PK\x05\x06'and e[1:3]==(0,0)and e[3]==e[4]and 1<=e[3]<=MAX_FILES+1
         and e[7]==0 and e[6]+e[5]+22==before.st_size and 0<e[5]<=2_000_000)
    raw=_pread(fd,e[6],e[5],ledger);at=previous_end=total=0;rows={};names=[]
    for _ in range(e[3]):
        need(at+46<=len(raw));v=struct.unpack('<4s6H3I5H2I',raw[at:at+46]);length=v[10]
        need(v[0]==b'PK\x01\x02'and v[1:7]==(788,20,0,0,0,33)and v[8]==v[9]
             and v[11:15]==(0,0,0,0)and v[15]==0o100644<<16 and 0<length<=240
             and at+46+length<=len(raw)and v[16]==previous_end)
        name=raw[at+46:at+46+length].decode('ascii');path_name(name)
        need(name not in rows and (not names or names[-1]<name));names.append(name)
        size=v[9];need(0<=size<=MAX_MEMBER);total+=size;need(total<=MAX_ARTIFACT)
        local=_pread(fd,v[16],30+length,ledger)
        expected={'bytes':size,'sha256':'','crc32':v[7],'mode':0o644}
        need(local==_zip_local(name,expected));offset=v[16]+len(local)
        need(offset+size<=e[6]);previous_end=offset+size
        rows[name]={'bytes':size,'crc32':v[7],'mode':0o644,'offset':offset};at+=46+length
    need(at==len(raw)and previous_end==e[6]and META in rows)
    need(rows[META]['bytes']<=MAX_RECORD)
    meta_raw=_pread(fd,rows[META]['offset'],rows[META]['bytes'],ledger)
    need(zlib.crc32(meta_raw)==rows[META]['crc32'])
    if expected_manifest is not None:need(meta_raw==expected_manifest)
    manifest=parse(meta_raw,ledger)
    need(encoded(manifest)+b'\n'==meta_raw)
    need(type(manifest)is dict and set(manifest)=={'profile','build','files','claims'}and manifest['profile']==PROFILE
         and manifest['claims']==FALSE_CLAIMS and all(type(v)is bool and v is False for v in manifest['claims'].values())
         and type(manifest['files'])is dict and 0<len(manifest['files'])<=MAX_FILES)
    collision_free(manifest['files'])
    wanted={'payload/'+path_name(name) for name in manifest['files']}|{META};need(set(rows)==wanted)
    for name,row in manifest['files'].items():
        need(type(row)is dict and set(row)=={'bytes','sha256','mode'}and type(row['bytes'])is int
             and 0<=row['bytes']<=MAX_MEMBER and type(row['mode'])is int and row['mode']==0o644
             and type(row['sha256'])is str and re.fullmatch('[0-9a-f]{64}',row['sha256']))
        actual=rows['payload/'+name];need(actual['bytes']==row['bytes'])
        if hash_payload:
            digest=hashlib.sha256();crc=length=0;ledger.charge(actual['bytes'])
            while length<actual['bytes']:
                ledger.tick();block=os.pread(fd,min(65536,actual['bytes']-length),actual['offset']+length)
                need(block);length+=len(block);digest.update(block);crc=zlib.crc32(block,crc)
            need(digest.hexdigest()==row['sha256']and crc==actual['crc32'])
    need(identity(before)==identity(os.fstat(fd)));ledger.tick()
    return manifest,rows


# Closed authorship/source facts; paired with actual primary grants below.
# These names are not an inference that source-copy permission grants runtime rights.
PROJECT_SOURCE_NAMES = frozenset((
    'docs/PS-reviewer-start.md',
    'docs/a11y-dialog-failure-context.md',
    'docs/accessibility-conformance-report.md',
    'docs/accessibility-deferred-details-measurement.md',
    'docs/accessibility-evidence-selection-plan.md',
    'docs/accessibility-failure-diagnostics.md',
    'docs/accessibility-release-gate.md',
    'docs/adjudication-spec.md',
    'docs/agent-delivery-status.md',
    'docs/agent-handoffs.md',
    'docs/agent-output-plan.md',
    'docs/agent-output.md',
    'docs/ai-tool-plugin-plan.md',
    'docs/ai-tools.md',
    'docs/android-configuration-handoff-plan.md',
    'docs/android-configuration-home-setup-plan.md',
    'docs/android-configuration-verifier-visibility-plan.md',
    'docs/android-content-margin-gesture-plan.md',
    'docs/android-intake-provenance-plan.md',
    'docs/android-malformed-intent-plan.md',
    'docs/android-os-chooser-plan.md',
    'docs/android-share-developer.md',
    'docs/android-share-plan.md',
    'docs/api-rollback-ownership-plan.md',
    'docs/app-store-readiness.md',
    'docs/approachable-tag-modals.md',
    'docs/artifact-io-ownership-plan.md',
    'docs/assertion-conformance-plan.md',
    'docs/assertion-migration.md',
    'docs/assertion-replay-plan.md',
    'docs/assertion-replay-result.md',
    'docs/assertion-replay.md',
    'docs/asset-notices-plan.md',
    'docs/asset-notices-result.md',
    'docs/asset-notices.md',
    'docs/audit-guide-entry-plan.md',
    'docs/authenticated-results-plan.md',
    'docs/authenticated-results-result.md',
    'docs/author-choice.md',
    'docs/authority-quotation-plan.md',
    'docs/authority-quotation-result.md',
    'docs/authority-quotation.md',
    'docs/backup-implementation.md',
    'docs/backup-option-review.md',
    'docs/backup-retention-plan.md',
    'docs/backup-retention-result.md',
    'docs/backup-retention.md',
    'docs/blind-review-privacy-plan.md',
    'docs/blind-review-privacy-result.md',
    'docs/c2pa-cohort-plan.md',
    'docs/c2pa-cohort-result.md',
    'docs/c2pa-cohort-review.md',
    'docs/c2pa-native-obligations-plan.md',
    'docs/c2pa-native-obligations-result.md',
    'docs/c2pa-native-obligations.md',
    'docs/calmer-tag-panels.md',
    'docs/capture-mechanism-result.md',
    'docs/certification-programme-guide.md',
    'docs/certification-programme-main-integration-plan.md',
    'docs/certification-programme-main-integration-result.md',
    'docs/certification-programme-plan.md',
    'docs/certification-programme-result.md',
    'docs/certification-programme.md',
    'docs/cffi-libffi-obligation-plan.md',
    'docs/cffi-libffi-obligations.md',
    'docs/change-accountability-plan.md',
    'docs/change-accountability-result.md',
    'docs/changelog-merge-parent-plan.md',
    'docs/changelog-policy.md',
    'docs/choice-between-plan.md',
    'docs/choice-framing-plan.md',
    'docs/choice-framing-result.md',
    'docs/choice-framing.md',
    'docs/choice-grammar-result.md',
    'docs/ci-branch-baseline-plan.md',
    'docs/ci-browser-install-plan.md',
    'docs/ci-efficiency-observation.md',
    'docs/ci-event-efficiency-plan.md',
    'docs/ci-portability-plan.md',
    'docs/ci-regression-plan.md',
    'docs/classifier-confidence-plan.md',
    'docs/command-matching-performance-plan.md',
    'docs/communications-plan.md',
    'docs/community-core-plan.md',
    'docs/community-core-result.md',
    'docs/community-core.md',
    'docs/compact-evidence-plan.md',
    'docs/compact-tags-plan.md',
    'docs/competitive-differentiation.md',
    'docs/competitive-landscape.json',
    'docs/competitive-landscape.md',
    'docs/composition-observation-plan.md',
    'docs/composition-observations.md',
    'docs/confidence-floor-audit.md',
    'docs/conformance-acceptance-plan.md',
    'docs/conformance-evidence-result.md',
    'docs/conformance-recusal.md',
    'docs/conformance-runner-plan.md',
    'docs/conformance-runner.md',
    'docs/consent-conformance-plan.md',
    'docs/consumer-boundary-result.md',
    'docs/corpus-support.md',
    'docs/credential-device-integration-plan.md',
    'docs/credential-disclosure-readiness.md',
    'docs/credential-flow-context-plan.md',
    'docs/credential-flow-context.md',
    'docs/credential-flow-device-plan.md',
    'docs/credential-flow-device.md',
    'docs/credential-flow-plan.md',
    'docs/credential-flow.md',
    'docs/credential-production-ui-review.md',
    'docs/current-route-boundaries.md',
    'docs/data-growth-plan.md',
    'docs/decision-history.md',
    'docs/decisions.json',
    'docs/delivery-wave-2026-11-21.md',
    'docs/dependency-automation-plan.md',
    'docs/dependency-automation-result.md',
    'docs/dependency-conflict-plan.md',
    'docs/dependency-contract.md',
    'docs/dependency-notices.md',
    'docs/development.md',
    'docs/device-accessibility-increment.md',
    'docs/device-accessibility-result.md',
    'docs/device-build-reference.json',
    'docs/directory-clock-fence-plan.md',
    'docs/dispute-correction-link-plan.md',
    'docs/dispute-correction-link.md',
    'docs/distribution-artifact-sbom-plan.md',
    'docs/distribution-artifact-sbom.md',
    'docs/draft-privacy-plan.md',
    'docs/draft-privacy-result.md',
    'docs/draft-privacy.md',
    'docs/editorial-workflow-plan.md',
    'docs/editorial-workflow-result.md',
    'docs/editorial-workflow.md',
    'docs/enterprise-worker-evidence-refresh-plan.md',
    'docs/esbuild-source-review.md',
    'docs/evidence-packet-plan.md',
    'docs/evidence-packet.md',
    'docs/evidence-resistance.md',
    'docs/execution-ownership.json',
    'docs/execution-report-contract.md',
    'docs/experiments/native-share-unreleased.json',
    'docs/extension-consent-plan.md',
    'docs/extension-consumer-plan.md',
    'docs/f030-dom-replacement-result.md',
    'docs/f030-live-stream-plan.md',
    'docs/fa-discovery-preview-plan.md',
    'docs/fa-image-main-integration-plan.md',
    'docs/fa-image-main-integration-result.md',
    'docs/feedback-analysis-plan.md',
    'docs/feedback-analysis-result.md',
    'docs/feedback-analysis.md',
    'docs/fi-citation-practice-main-integration-plan.md',
    'docs/fi-citation-practice-plan.md',
    'docs/fi-citation-practice.md',
    'docs/fi-citation-sidecar-plan.md',
    'docs/fi-citation-sidecar.md',
    'docs/firefox-adapter-plan.md',
    'docs/firefox-adapter-result.md',
    'docs/firefox-preview.md',
    'docs/fleet-deployment-plan.md',
    'docs/fleet-deployment.md',
    'docs/footer-workflows.md',
    'docs/full-host-recovery-plan.md',
    'docs/gateway-authentication.md',
    'docs/group-receipt-plan.md',
    'docs/group-receipts.md',
    'docs/handheld-delivery.md',
    'docs/hash-agent-worker-evidence-refresh-plan.md',
    'docs/hash-report-intake-plan.md',
    'docs/hash-report-intake.md',
    'docs/hf-model-card-reference-plan.md',
    'docs/host-capture-plan.md',
    'docs/host-capture-result.md',
    'docs/host-capture.md',
    'docs/hosted-delivery-revalidation-plan.md',
    'docs/hp-accessibility-readiness.md',
    'docs/hp-device-explorer-plan.md',
    'docs/hp-device-explorer.md',
    'docs/hp-site-integration.md',
    'docs/hp-uncertainty-device-handoff.md',
    'docs/hp-uncertainty-device-plan.md',
    'docs/hp-uncertainty-device.md',
    'docs/hp-uncertainty-integration-controls.md',
    'docs/http-privacy-plan.md',
    'docs/image-current-delivery-registration-plan.md',
    'docs/image-declaration-profile-plan.md',
    'docs/image-declaration-profile-result.md',
    'docs/image-device-guide.md',
    'docs/image-device-plan.md',
    'docs/image-device-result.md',
    'docs/image-evidence-readout-plan.md',
    'docs/image-evidence-readout-result.md',
    'docs/image-privacy-activation-plan.md',
    'docs/image-provenance-boundary.md',
    'docs/image-release-diagnostics-plan.md',
    'docs/image-score-cleanup-ownership-correction-plan.md',
    'docs/increment-A-result.md',
    'docs/independent-delivery-nov21-next.md',
    'docs/independent-review.md',
    'docs/independent-signals-result.md',
    'docs/independent-timestamp-plan.md',
    'docs/independent-timestamps.md',
    'docs/ios-distribution-plan.md',
    'docs/jpeg-credential-result.md',
    'docs/jpeg-provenance-guide.md',
    'docs/jpeg-provenance-plan.md',
    'docs/key-recovery-plan.md',
    'docs/key-recovery.md',
    'docs/language-observations-plan.md',
    'docs/language-observations.md',
    'docs/legal-operations-review.md',
    'docs/legal/README.md',
    'docs/legal/entity-structure-comparison.md',
    'docs/legal/execution-packet.md',
    'docs/legal/michigan-llc-packet.md',
    'docs/legal/reviewed-corrections.md',
    'docs/legal/source-inventory.json',
    'docs/license-evidence-plan.md',
    'docs/live-launch-status.md',
    'docs/local-reference-corpus.md',
    'docs/local-setup-plan.md',
    'docs/local-setup-result.md',
    'docs/maintainers.json',
    'docs/maintenance-delivery-nov21.md',
    'docs/manifest-inspection-plan.md',
    'docs/manifest-inspection.md',
    'docs/manifest-loader-plan.md',
    'docs/mark-usage.md',
    'docs/master-scope.json',
    'docs/master-scope.md',
    'docs/mcp-current-registry-zlib-repair-plan.md',
    'docs/mcp-linux-release.md',
    'docs/mcp-managed-release-plan.md',
    'docs/mcp-managed-release-result.md',
    'docs/mcp-managed-release.md',
    'docs/mcp-publication-result.md',
    'docs/mcp-stdio-distribution-plan.md',
    'docs/mcp-stdio-distribution.md',
    'docs/mcp-zlib-producer-refresh-plan.md',
    'docs/measurement-provenance-plan.md',
    'docs/metadata-pilot-contract.md',
    'docs/metadata-storage-plan.md',
    'docs/metadata-storage.md',
    'docs/mobile-payload-plan.md',
    'docs/modal-enlarged-text-fix.md',
    'docs/model-asset-integrity.md',
    'docs/mt-annotation-guide.md',
    'docs/mt-choice-device.md',
    'docs/mt-choice-modal-integration-plan.md',
    'docs/mt-choice-modal-integration-result.md',
    'docs/mt-cohort-integration-plan.md',
    'docs/mt-device-explorer-plan.md',
    'docs/mt-device-explorer-result.md',
    'docs/mt-device-explorer.md',
    'docs/mt-device-integrity-correction.md',
    'docs/mt-evidence-workflow.md',
    'docs/mt-input-retention-plan.md',
    'docs/mt-input-retention-result.md',
    'docs/mt-label-preparation-plan.md',
    'docs/mt-label-preparation-result.md',
    'docs/mt-label-preparation.md',
    'docs/mt-mobile-quotation-plan.md',
    'docs/mt-mobile-quotation-result.md',
    'docs/mt-mobile-quotation.md',
    'docs/mt-quotation-workflow-result.md',
    'docs/mt-quotation-workflow.md',
    'docs/mt-urgency-locality-plan.md',
    'docs/mt-urgency-locality-result.md',
    'docs/mt-workflow-plan.md',
    'docs/name-evidence-review.md',
    'docs/native-dependency-evidence.md',
    'docs/native-dependency-plan.md',
    'docs/native-engine-checks.md',
    'docs/native-share-developer.md',
    'docs/native-share-plan.md',
    'docs/native-share-repair-plan.md',
    'docs/nested-runtime-evidence.md',
    'docs/nested-runtime-plan.md',
    'docs/nf-browser-diagnostic-plan.md',
    'docs/nf-device-reference-plan.md',
    'docs/nf-device-reference-result.md',
    'docs/nf-device-reference.md',
    'docs/nf-pr149-diagnostic-plan.md',
    'docs/nf-source-evidence-plan.md',
    'docs/nf-source-evidence.md',
    'docs/nli-license-cohort-plan.md',
    'docs/nli-license-cohort.md',
    'docs/nli-native-obligations-plan.md',
    'docs/nli-native-obligations-result.md',
    'docs/nli-native-obligations.md',
    'docs/nli-pairs-plan.md',
    'docs/nli-pairs-result.md',
    'docs/nli-pairs.md',
    'docs/nli-reference-plan.md',
    'docs/nli-reference-result.md',
    'docs/nli-references.md',
    'docs/normalization-contract.md',
    'docs/nov21-autonomous-closure-audit.json',
    'docs/nov22-managed-distribution-integration-plan.md',
    'docs/offline-component-result.md',
    'docs/offline-image-score-guide.md',
    'docs/offline-image-score-hosted-source-plan.md',
    'docs/offline-image-score-integration-plan.md',
    'docs/offline-image-score-plan.md',
    'docs/offline-image-score-qualification-plan.md',
    'docs/offline-image-score-registration-amendment.md',
    'docs/offline-image-score-result.md',
    'docs/offline-receipt-plan.md',
    'docs/offline-receipts.md',
    'docs/offline-revocation-plan.md',
    'docs/offline-revocation.md',
    'docs/open-dependency-audit-plan.md',
    'docs/open-requirement-gates-2026-11-16.json',
    'docs/open-source-hosting-plan.md',
    'docs/open-validation-path.md',
    'docs/operational-alerts.md',
    'docs/optional-notifications-plan.md',
    'docs/organization-audit-plan.md',
    'docs/organization-audit-result.md',
    'docs/organization-audit.md',
    'docs/organization-directory-plan.md',
    'docs/organization-directory.md',
    'docs/organization-policy-acceptance.md',
    'docs/organization-policy-registry-plan.md',
    'docs/organization-policy-registry-result.md',
    'docs/organization-policy-registry.md',
    'docs/original-closure-wave-nov21.md',
    'docs/owner-actions.md',
    'docs/owner-operation.md',
    'docs/owner-pilot-result.md',
    'docs/package-proximity-plan.md',
    'docs/package-proximity.md',
    'docs/pii-hidden-separators-plan.md',
    'docs/pii-pan-token-plan.md',
    'docs/pii-protocol-import-plan.md',
    'docs/pii-separator-correction-plan.md',
    'docs/pii-startup-diagnostics-plan.md',
    'docs/pipeline-performance-plan.md',
    'docs/pipeline-performance.md',
    'docs/privacy-boundaries.md',
    'docs/private-host-operations.md',
    'docs/private-policy-plan.md',
    'docs/private-policy-result.md',
    'docs/private-policy.md',
    'docs/private-tools-publication-plan.md',
    'docs/product-differentiation.md',
    'docs/progress-audit-plan.md',
    'docs/protocol-migration-contract.json',
    'docs/protocol-migration-plan.md',
    'docs/provenance-boundary-increment.md',
    'docs/provenance-boundary-result.md',
    'docs/ps-lazy-context-performance-plan.md',
    'docs/ps-lazy-context-performance-result.md',
    'docs/ps-result-clarity.md',
    'docs/ps-source-distribution-plan.md',
    'docs/ps-source-distribution.md',
    'docs/ps-source-provenance-downloads-plan.md',
    'docs/ps-source-provenance-downloads.md',
    'docs/public-community-and-private-data.md',
    'docs/public-policies.md',
    'docs/pyodide-js-source-delivery.md',
    'docs/pyodide-js-source-plan.md',
    'docs/quantitative-observation-plan.md',
    'docs/quantitative-observations.md',
    'docs/quarterly-brand-and-agent-plan.md',
    'docs/quiet-layer-architecture.md',
    'docs/quiet-paused-checks-plan.md',
    'docs/quiet-paused-checks.md',
    'docs/recusal-enforcement-plan.md',
    'docs/redaction-recognition-plan.md',
    'docs/redaction-recognition-result.md',
    'docs/redaction-recognition.md',
    'docs/reference-claim-coverage-plan.md',
    'docs/reference-claim-coverage-result.md',
    'docs/reference-review-window-plan.md',
    'docs/reference-revision-plan.md',
    'docs/reference-revision-result.md',
    'docs/reference-revisions.md',
    'docs/registry-contract-plan.md',
    'docs/registry-contract-result.md',
    'docs/registry-deferral-plan.md',
    'docs/registry-deferral-result.md',
    'docs/remaining-worker-evidence-refresh-plan.md',
    'docs/remaining-worker-evidence-refresh-result.md',
    'docs/remote-ai-connections.md',
    'docs/remote-openapi-plan.md',
    'docs/remote-tag-connectors-plan.md',
    'docs/remote-tag-connectors-result.md',
    'docs/remote-tag-connectors.md',
    'docs/reproducibility-controls-plan.md',
    'docs/reproducibility-controls-result.md',
    'docs/required-ci-plan.md',
    'docs/required-ci-result.md',
    'docs/research-admission-plan.md',
    'docs/research-admission-result.md',
    'docs/research-admission.md',
    'docs/research-http-plan.md',
    'docs/research-http-result.md',
    'docs/research-http.md',
    'docs/research-invitation-plan.md',
    'docs/research-invitation-result.md',
    'docs/research-invitations.md',
    'docs/reserved-subject-contract.md',
    'docs/reserved-subject-plan.md',
    'docs/restore-isolation-plan.md',
    'docs/restore-isolation-result.md',
    'docs/review-execution-binding-plan.md',
    'docs/review-execution-binding-result.md',
    'docs/reviewed-programme-mt-delivery-plan.md',
    'docs/reviewer-agreement-plan.md',
    'docs/reviewer-agreement.md',
    'docs/rolldown-source-review.md',
    'docs/route-boundary-result.md',
    'docs/runtime-gap-plan.md',
    'docs/runtime-gap-result.md',
    'docs/runtime-sbom.md',
    'docs/rust-stdlib-obligation-plan.md',
    'docs/rust-stdlib-obligations.md',
    'docs/scope-100-execution.md',
    'docs/scope-25-execution.md',
    'docs/scope-50-execution.md',
    'docs/scope-60-execution.md',
    'docs/scope-boundary-guard-plan.md',
    'docs/scope-delivery.json',
    'docs/scope-delivery.md',
    'docs/scope-grouping-plan.md',
    'docs/scope-grouping-result.md',
    'docs/scope-groups.json',
    'docs/scope-priorities-2026-11-16.json',
    'docs/scope-priorities-2026-11-16.md',
    'docs/scope-progress.json',
    'docs/scope-progress.md',
    'docs/scope-render-plan.md',
    'docs/scope-task-index.md',
    'docs/search-discovery-status.md',
    'docs/security-operations.md',
    'docs/selected-reference-comparison.md',
    'docs/selected-reference-pair-plan.md',
    'docs/selected-reference-pair-result.md',
    'docs/seo-audit-2026-11-16.md',
    'docs/session-accountability-plan.md',
    'docs/session-delivery-plan.md',
    'docs/session-delivery.json',
    'docs/session-revision-plan.md',
    'docs/session-revision-result.md',
    'docs/session-revisions.md',
    'docs/site-fixture-server.md',
    'docs/social-launch-kit.md',
    'docs/source-image-integration-result.md',
    'docs/source-input-binding-plan.md',
    'docs/source-input-binding-result.md',
    'docs/source-provenance-plan.md',
    'docs/source-provenance.md',
    'docs/source-snapshot-binding-plan.md',
    'docs/source-snapshot-managed-consumer.md',
    'docs/source-snapshot-managed-integration-plan.md',
    'docs/source-snapshot-rights-current-main-plan.md',
    'docs/source-snapshot-rights-current-main.md',
    'docs/source-snapshot-rights-plan.md',
    'docs/source-snapshot-rights-v2-plan.md',
    'docs/source-snapshot-rights-v2.md',
    'docs/source-snapshot-rights-v3-additions-plan.md',
    'docs/source-snapshot-rights-v3-metadata-transitions-plan.md',
    'docs/source-snapshot-rights-v3.md',
    'docs/source-snapshot-v2-plan.md',
    'docs/source-snapshot-v3-plan.md',
    'docs/source-snapshot-v3-result.md',
    'docs/spdx-inventory-validation.md',
    'docs/spdx-validation-plan.md',
    'docs/state-chronology-plan.md',
    'docs/stream-observer-plan.md',
    'docs/subject-contract.md',
    'docs/synthid-vendor-input-plan.md',
    'docs/synthid-vendor-input-result.md',
    'docs/synthid-vendor-input-status.md',
    'docs/synthid-vendor-input.md',
    'docs/tag-failure-isolation-plan.md',
    'docs/tag-failure-isolation-result.md',
    'docs/tag-integration-2026-11-16.md',
    'docs/tag-performance-plan.md',
    'docs/tag-safety-use-cases.json',
    'docs/tag-safety-use-cases.md',
    'docs/tag-status-2026-11-16.json',
    'docs/tag-status-2026-11-16.md',
    'docs/tag-status-2026-11-18.md',
    'docs/tag-system-upgrade.md',
    'docs/tag-wave-nov19-integration.md',
    'docs/tags/BT-01.md',
    'docs/tags/FA-01.md',
    'docs/tags/FI-01.md',
    'docs/tags/HP-01.md',
    'docs/tags/IV-01.md',
    'docs/tags/MT-01.md',
    'docs/tags/NF-01.md',
    'docs/tags/PA-01.md',
    'docs/tags/PII-01.md',
    'docs/tags/PII_OUTBOUND-01.md',
    'docs/tags/PS-01-acceptance.md',
    'docs/tags/PS-01.md',
    'docs/tags/SC-01.md',
    'docs/tags/UC-01.md',
    'docs/tags/UNK-01.md',
    'docs/threat-controls.json',
    'docs/virtual-tag-lab.md',
    'docs/visual-camera-detector-candidates.md',
    'docs/visual-model-data-screening.md',
    'docs/visual-score-source-copy-grants.md',
    'docs/visual-tag-execution-plan.md',
    'docs/web-distribution-plan.md',
    'docs/web-distribution-result.md',
    'docs/web-distribution.md',
    'docs/website-build-diagnostics-plan.md',
    'docs/website.md',
    'docs/worker-supervision-recovery-plan.md',
    'docs/zlib-source-delivery-plan.md',
    'docs/zlib-source-delivery.md',
    'integrations/ai-tools/check-text.input.schema.json',
    'integrations/ai-tools/check-text.output.schema.json',
    'integrations/ai-tools/function-tools.json',
    'integrations/ai-tools/remote-openapi.json',
    'integrations/mcp/requirements.in',
    'integrations/mcp/requirements.lock',
    'integrations/visual-score-reference/1.0.0/hf-model-card-reference.json',
    'integrations/visual-score-reference/1.0.0/preprocess-reference.json',
    'integrations/visual-score-reference/1.0.0/projection.json',
    'integrations/visual-score-reference/1.0.0/runtime-candidates.json',
    'integrations/visual-score-reference/1.0.0/source.json',
    'integrations/visual-score-reference/qualification-linux-cp313.json',
    'integrations/visual-score-reference/qualification-linux-cp313.lock',
    'integrations/visual-score-reference/qualification-notice-inventory.json',
    'protocol/accessibility_release.py',
    'protocol/assertions.py',
    'protocol/author-choice.cjs',
    'protocol/categories.py',
    'protocol/conformance-statement.cjs',
    'protocol/corpus.py',
    'protocol/corpus_support.py',
    'protocol/decisions.py',
    'protocol/evidence.py',
    'protocol/group-receipts.cjs',
    'protocol/http_privacy.py',
    'protocol/key-backup.cjs',
    'protocol/measurements.py',
    'protocol/migration.py',
    'protocol/migration_io.py',
    'protocol/normalization-core.js',
    'protocol/normalization.cjs',
    'protocol/normalization.mjs',
    'protocol/normalization.py',
    'protocol/receipts.cjs',
    'protocol/repetition.py',
    'protocol/replay.py',
    'protocol/replay_identity.py',
    'protocol/reports.py',
    'protocol/reserved-subjects.cjs',
    'protocol/reserved_subjects.py',
    'protocol/revalidation.py',
    'protocol/revocation-witnesses.cjs',
    'protocol/revocation.cjs',
    'protocol/scope_groups.py',
    'protocol/signals.py',
    'protocol/subjects.cjs',
    'protocol/subjects.py',
    'protocol/transport_signing.py',
    'scripts/web-checker-build-observer.mjs',
    'services/evaluator/app.py',
    'site/image-metadata-fixture.html',
    'site/index.html',
    'site/package-lock.json',
    'site/package.json',
    'site/public/404.html',
    'site/public/_headers',
    'site/public/camo-q4.svg',
    'site/public/downloads/aitrust-id-ps-source.zip.sha256',
    'site/public/downloads/provenance/cd3beab02774fa939e3a2bd8a0d87913d9e8fd81/VERIFY.md',
    'site/public/downloads/provenance/cd3beab02774fa939e3a2bd8a0d87913d9e8fd81/artifact.spdx.json',
    'site/public/downloads/provenance/cd3beab02774fa939e3a2bd8a0d87913d9e8fd81/evidence.json',
    'site/public/downloads/provenance/cd3beab02774fa939e3a2bd8a0d87913d9e8fd81/manifest.json',
    'site/public/downloads/provenance/cd3beab02774fa939e3a2bd8a0d87913d9e8fd81/sbom.sigstore.json',
    'site/public/downloads/provenance/cd3beab02774fa939e3a2bd8a0d87913d9e8fd81/verified-observation.json',
    'site/public/favicon.svg',
    'site/public/googlefd96956266acb393.html',
    'site/public/hp-device/.gitattributes',
    'site/public/hp-uncertainty-device/hedge-1e05ab4af768a5db89229dcfdb8eb18faf1f8adbf58518b4efe9c56f9bdd01ec.json',
    'site/public/mt-device/.gitattributes',
    'site/public/nf-device/cosine-41334bcd5ff9a9fe1842fb1d35f8ebe076ab7f35c8b9d667d2d9523e35574332.json',
    'site/public/nf-device/literal-c26434149b752d6eba0ba0aefb8cf0a3d9a334035426911f6d5e17896bccb5c7.json',
    'site/public/reference/0004-tag-claim-boundaries.md',
    'site/public/reference/PS-01-acceptance.md',
    'site/public/reference/PS-01.md',
    'site/public/reference/accessibility-policy.md',
    'site/public/reference/accessibility-release-gate.md',
    'site/public/reference/assertion-migration.md',
    'site/public/reference/asset-notices.md',
    'site/public/reference/backup-retention.md',
    'site/public/reference/bounded-service-conformance.json',
    'site/public/reference/browser-checks.json',
    'site/public/reference/certification-programme-guide.md',
    'site/public/reference/certification-programme.json',
    'site/public/reference/certification-programme.md',
    'site/public/reference/command-stress.json',
    'site/public/reference/conduct-policy.md',
    'site/public/reference/conformance-runner.md',
    'site/public/reference/container-checks.json',
    'site/public/reference/context-v6-service.json',
    'site/public/reference/contributing-policy.md',
    'site/public/reference/counterexamples_v2.jsonl',
    'site/public/reference/credential-flow-device.md',
    'site/public/reference/decisions.json',
    'site/public/reference/decisions.md',
    'site/public/reference/development-dataset-manifest.json',
    'site/public/reference/directory-software-linux.json',
    'site/public/reference/draft-privacy.md',
    'site/public/reference/evidence-packet.md',
    'site/public/reference/evidence-resistance.json',
    'site/public/reference/evidence-resistance.md',
    'site/public/reference/example-provenance.json',
    'site/public/reference/extension-integration.json',
    'site/public/reference/feedback-analysis.md',
    'site/public/reference/fetch_execute_v1.jsonl',
    'site/public/reference/fi-citation-practice.md',
    'site/public/reference/fi-citation-sidecar-plan.md',
    'site/public/reference/fi-citation-sidecar.md',
    'site/public/reference/fleet-deployment.md',
    'site/public/reference/fleet-linux.json',
    'site/public/reference/fleet-macos.json',
    'site/public/reference/frozen-normalization.json',
    'site/public/reference/frozen-service-conformance.json',
    'site/public/reference/governance-policy.md',
    'site/public/reference/hash-inbox-linux.json',
    'site/public/reference/hash-inbox-macos.json',
    'site/public/reference/hash-report-intake.md',
    'site/public/reference/host-capture-linux.json',
    'site/public/reference/host-capture-macos.json',
    'site/public/reference/host-capture.md',
    'site/public/reference/host-recovery.json',
    'site/public/reference/hp-device-explorer.md',
    'site/public/reference/hp-uncertainty-device.md',
    'site/public/reference/image-device-guide.md',
    'site/public/reference/independent-review.md',
    'site/public/reference/language-observations.md',
    'site/public/reference/live-gap-implementation.json',
    'site/public/reference/live_gap_v1.jsonl',
    'site/public/reference/local-reference-corpus.md',
    'site/public/reference/measurement-provenance-plan.md',
    'site/public/reference/model-asset-integrity.md',
    'site/public/reference/mt-choice-device.md',
    'site/public/reference/mt-device-explorer.md',
    'site/public/reference/mt-evidence-workflow.md',
    'site/public/reference/mt-mobile-quotation.md',
    'site/public/reference/native-dependency-evidence.md',
    'site/public/reference/native-engine-checks.md',
    'site/public/reference/native-share-developer.md',
    'site/public/reference/native-share-engine.json',
    'site/public/reference/native-share-workflow.json',
    'site/public/reference/nf-device-reference.md',
    'site/public/reference/nf-source-evidence.md',
    'site/public/reference/open-validation-path.md',
    'site/public/reference/organization-audit-linux.json',
    'site/public/reference/organization-audit.md',
    'site/public/reference/organization-directory.md',
    'site/public/reference/organization-policy-acceptance.md',
    'site/public/reference/organization-policy-registry.md',
    'site/public/reference/performance-device.json',
    'site/public/reference/performance-regressions.json',
    'site/public/reference/pii-compact-addresses.json',
    'site/public/reference/pii-recognition-development.json',
    'site/public/reference/pipeline-performance.json',
    'site/public/reference/policies/access/v1.0.txt',
    'site/public/reference/policies/access/v1.1.txt',
    'site/public/reference/policies/access/v1.10.txt',
    'site/public/reference/policies/access/v1.11.txt',
    'site/public/reference/policies/access/v1.12.txt',
    'site/public/reference/policies/access/v1.13.txt',
    'site/public/reference/policies/access/v1.14.txt',
    'site/public/reference/policies/access/v1.15.txt',
    'site/public/reference/policies/access/v1.2.txt',
    'site/public/reference/policies/access/v1.3.txt',
    'site/public/reference/policies/access/v1.4.txt',
    'site/public/reference/policies/access/v1.5.txt',
    'site/public/reference/policies/access/v1.6.txt',
    'site/public/reference/policies/access/v1.7.txt',
    'site/public/reference/policies/access/v1.8.txt',
    'site/public/reference/policies/access/v1.9.txt',
    'site/public/reference/policies/community/v1.0.txt',
    'site/public/reference/policies/community/v1.1.txt',
    'site/public/reference/policies/community/v1.10.txt',
    'site/public/reference/policies/community/v1.11.txt',
    'site/public/reference/policies/community/v1.12.txt',
    'site/public/reference/policies/community/v1.13.txt',
    'site/public/reference/policies/community/v1.14.txt',
    'site/public/reference/policies/community/v1.15.txt',
    'site/public/reference/policies/community/v1.2.txt',
    'site/public/reference/policies/community/v1.3.txt',
    'site/public/reference/policies/community/v1.4.txt',
    'site/public/reference/policies/community/v1.5.txt',
    'site/public/reference/policies/community/v1.6.txt',
    'site/public/reference/policies/community/v1.7.txt',
    'site/public/reference/policies/community/v1.8.txt',
    'site/public/reference/policies/community/v1.9.txt',
    'site/public/reference/policies/contributing/v1.0.txt',
    'site/public/reference/policies/contributing/v1.1.txt',
    'site/public/reference/policies/contributing/v1.10.txt',
    'site/public/reference/policies/contributing/v1.11.txt',
    'site/public/reference/policies/contributing/v1.12.txt',
    'site/public/reference/policies/contributing/v1.13.txt',
    'site/public/reference/policies/contributing/v1.14.txt',
    'site/public/reference/policies/contributing/v1.15.txt',
    'site/public/reference/policies/contributing/v1.2.txt',
    'site/public/reference/policies/contributing/v1.3.txt',
    'site/public/reference/policies/contributing/v1.4.txt',
    'site/public/reference/policies/contributing/v1.5.txt',
    'site/public/reference/policies/contributing/v1.6.txt',
    'site/public/reference/policies/contributing/v1.7.txt',
    'site/public/reference/policies/contributing/v1.8.txt',
    'site/public/reference/policies/contributing/v1.9.txt',
    'site/public/reference/policies/governance/v1.0.txt',
    'site/public/reference/policies/governance/v1.1.txt',
    'site/public/reference/policies/governance/v1.10.txt',
    'site/public/reference/policies/governance/v1.11.txt',
    'site/public/reference/policies/governance/v1.12.txt',
    'site/public/reference/policies/governance/v1.13.txt',
    'site/public/reference/policies/governance/v1.14.txt',
    'site/public/reference/policies/governance/v1.15.txt',
    'site/public/reference/policies/governance/v1.2.txt',
    'site/public/reference/policies/governance/v1.3.txt',
    'site/public/reference/policies/governance/v1.4.txt',
    'site/public/reference/policies/governance/v1.5.txt',
    'site/public/reference/policies/governance/v1.6.txt',
    'site/public/reference/policies/governance/v1.7.txt',
    'site/public/reference/policies/governance/v1.8.txt',
    'site/public/reference/policies/governance/v1.9.txt',
    'site/public/reference/policies/licenses/v1.0.txt',
    'site/public/reference/policies/licenses/v1.1.txt',
    'site/public/reference/policies/licenses/v1.10.txt',
    'site/public/reference/policies/licenses/v1.11.txt',
    'site/public/reference/policies/licenses/v1.12.txt',
    'site/public/reference/policies/licenses/v1.13.txt',
    'site/public/reference/policies/licenses/v1.14.txt',
    'site/public/reference/policies/licenses/v1.15.txt',
    'site/public/reference/policies/licenses/v1.2.txt',
    'site/public/reference/policies/licenses/v1.3.txt',
    'site/public/reference/policies/licenses/v1.4.txt',
    'site/public/reference/policies/licenses/v1.5.txt',
    'site/public/reference/policies/licenses/v1.6.txt',
    'site/public/reference/policies/licenses/v1.7.txt',
    'site/public/reference/policies/licenses/v1.8.txt',
    'site/public/reference/policies/licenses/v1.9.txt',
    'site/public/reference/policies/privacy/v1.0.txt',
    'site/public/reference/policies/privacy/v1.1.txt',
    'site/public/reference/policies/privacy/v1.10.txt',
    'site/public/reference/policies/privacy/v1.11.txt',
    'site/public/reference/policies/privacy/v1.12.txt',
    'site/public/reference/policies/privacy/v1.13.txt',
    'site/public/reference/policies/privacy/v1.14.txt',
    'site/public/reference/policies/privacy/v1.15.txt',
    'site/public/reference/policies/privacy/v1.2.txt',
    'site/public/reference/policies/privacy/v1.3.txt',
    'site/public/reference/policies/privacy/v1.4.txt',
    'site/public/reference/policies/privacy/v1.5.txt',
    'site/public/reference/policies/privacy/v1.6.txt',
    'site/public/reference/policies/privacy/v1.7.txt',
    'site/public/reference/policies/privacy/v1.8.txt',
    'site/public/reference/policies/privacy/v1.9.txt',
    'site/public/reference/policies/security/v1.0.txt',
    'site/public/reference/policies/security/v1.1.txt',
    'site/public/reference/policies/security/v1.10.txt',
    'site/public/reference/policies/security/v1.11.txt',
    'site/public/reference/policies/security/v1.12.txt',
    'site/public/reference/policies/security/v1.13.txt',
    'site/public/reference/policies/security/v1.14.txt',
    'site/public/reference/policies/security/v1.15.txt',
    'site/public/reference/policies/security/v1.2.txt',
    'site/public/reference/policies/security/v1.3.txt',
    'site/public/reference/policies/security/v1.4.txt',
    'site/public/reference/policies/security/v1.5.txt',
    'site/public/reference/policies/security/v1.6.txt',
    'site/public/reference/policies/security/v1.7.txt',
    'site/public/reference/policies/security/v1.8.txt',
    'site/public/reference/policies/security/v1.9.txt',
    'site/public/reference/policies/terms/v1.0.txt',
    'site/public/reference/policies/terms/v1.1.txt',
    'site/public/reference/policies/terms/v1.10.txt',
    'site/public/reference/policies/terms/v1.11.txt',
    'site/public/reference/policies/terms/v1.12.txt',
    'site/public/reference/policies/terms/v1.13.txt',
    'site/public/reference/policies/terms/v1.14.txt',
    'site/public/reference/policies/terms/v1.15.txt',
    'site/public/reference/policies/terms/v1.2.txt',
    'site/public/reference/policies/terms/v1.3.txt',
    'site/public/reference/policies/terms/v1.4.txt',
    'site/public/reference/policies/terms/v1.5.txt',
    'site/public/reference/policies/terms/v1.6.txt',
    'site/public/reference/policies/terms/v1.7.txt',
    'site/public/reference/policies/terms/v1.8.txt',
    'site/public/reference/policies/terms/v1.9.txt',
    'site/public/reference/policies/validation/v1.0.txt',
    'site/public/reference/policies/validation/v1.1.txt',
    'site/public/reference/policies/validation/v1.10.txt',
    'site/public/reference/policies/validation/v1.11.txt',
    'site/public/reference/policies/validation/v1.12.txt',
    'site/public/reference/policies/validation/v1.13.txt',
    'site/public/reference/policies/validation/v1.14.txt',
    'site/public/reference/policies/validation/v1.15.txt',
    'site/public/reference/policies/validation/v1.2.txt',
    'site/public/reference/policies/validation/v1.3.txt',
    'site/public/reference/policies/validation/v1.4.txt',
    'site/public/reference/policies/validation/v1.5.txt',
    'site/public/reference/policies/validation/v1.6.txt',
    'site/public/reference/policies/validation/v1.7.txt',
    'site/public/reference/policies/validation/v1.8.txt',
    'site/public/reference/policies/validation/v1.9.txt',
    'site/public/reference/policy-access.txt',
    'site/public/reference/policy-community.txt',
    'site/public/reference/policy-contributing.txt',
    'site/public/reference/policy-governance.txt',
    'site/public/reference/policy-licenses.txt',
    'site/public/reference/policy-privacy.txt',
    'site/public/reference/policy-security.txt',
    'site/public/reference/policy-terms.txt',
    'site/public/reference/policy-validation.txt',
    'site/public/reference/private-policy.md',
    'site/public/reference/ps-efficiency.json',
    'site/public/reference/ps-routing-gates.json',
    'site/public/reference/ps-routing-regressions.json',
    'site/public/reference/ps-source-distribution.md',
    'site/public/reference/ps_v1.jsonl',
    'site/public/reference/public-scope.json',
    'site/public/reference/redaction-compact-addresses.json',
    'site/public/reference/redaction-recognition.json',
    'site/public/reference/redaction-recognition.md',
    'site/public/reference/reference-revisions.md',
    'site/public/reference/regression-gates.json',
    'site/public/reference/reproducibility-controls-plan.md',
    'site/public/reference/routing_boundaries_v1.jsonl',
    'site/public/reference/security-operations.md',
    'site/public/reference/security-policy.md',
    'site/public/reference/selected-reference-comparison.md',
    'site/public/reference/selected-reference-pair-plan.md',
    'site/public/reference/service-resource-faults.json',
    'site/public/reference/session-revision-plan.md',
    'site/public/reference/session-revision-result.md',
    'site/public/reference/session-revisions.md',
    'site/public/reference/subject-contract.md',
    'site/public/reference/subjects-v2.json',
    'site/public/reference/synthid-vendor-input.md',
    'site/public/reference/tag-performance-evidence.json',
    'site/public/reference/tag-performance-plan.md',
    'site/public/reference/tag-performance.json',
    'site/public/robots.txt',
    'site/public/sitemap.xml',
    'site/public/tag-logo.svg',
    'site/public/theme.js',
    'site/scripts/owner-guide.mjs',
    'site/scripts/prepare-device.mjs',
    'site/scripts/prepare-offline.mjs',
    'site/scripts/prepare-performance.mjs',
    'site/scripts/prepare.mjs',
    'site/scripts/render-reference.mjs',
    'site/scripts/seo.mjs',
    'site/src/CredentialFlowExplorer.jsx',
    'site/src/CredentialFlowExplorerSlot.jsx',
    'site/src/HPExplorer.jsx',
    'site/src/HPExplorerSlot.jsx',
    'site/src/HPUncertaintyExplorer.jsx',
    'site/src/HPUncertaintyExplorerSlot.jsx',
    'site/src/ImageMetadataExplorer.jsx',
    'site/src/ImageMetadataExplorerSlot.jsx',
    'site/src/MTChoiceExplorer.jsx',
    'site/src/MTChoiceExplorerSlot.jsx',
    'site/src/MTExplorer.jsx',
    'site/src/MTExplorerSlot.jsx',
    'site/src/NFExplorer.jsx',
    'site/src/NFExplorerSlot.jsx',
    'site/src/ScopeData.jsx',
    'site/src/catalog.js',
    'site/src/catalogue-export.js',
    'site/src/credential-device-client.js',
    'site/src/credential-device-manifest.json',
    'site/src/credential-device-result.js',
    'site/src/credential-device-worker.js',
    'site/src/device-client.js',
    'site/src/device-worker.js',
    'site/src/handheld.jsx',
    'site/src/hp-device-client.js',
    'site/src/hp-device-manifest.json',
    'site/src/hp-device-result.js',
    'site/src/hp-device-worker.js',
    'site/src/hp-uncertainty-client.js',
    'site/src/hp-uncertainty-manifest.json',
    'site/src/hp-uncertainty-result.js',
    'site/src/hp-uncertainty-worker.js',
    'site/src/image-metadata-client.mjs',
    'site/src/image-metadata-fixture.jsx',
    'site/src/image-metadata-result.mjs',
    'site/src/image-metadata-worker.mjs',
    'site/src/main.jsx',
    'site/src/model-tools.js',
    'site/src/mt-choice-client.mjs',
    'site/src/mt-choice-result.mjs',
    'site/src/mt-choice-worker.mjs',
    'site/src/mt-device-client.js',
    'site/src/mt-device-manifest.json',
    'site/src/mt-device-result.js',
    'site/src/mt-device-worker.js',
    'site/src/mt-mobile-device-manifest.json',
    'site/src/mt-mobile-device-result.js',
    'site/src/nf-cosine-result.js',
    'site/src/nf-device-client.js',
    'site/src/nf-device-manifest.json',
    'site/src/nf-device-result.js',
    'site/src/nf-device-worker.js',
    'site/src/performance-model.js',
    'site/src/performance.jsx',
    'site/src/pipeline-timing-model.js',
    'site/src/policies.js',
    'site/src/presentation.js',
    'site/src/ps-result.js',
    'site/src/public-scope.json',
    'site/src/redaction-performance-model.js',
    'site/src/research-feedback.js',
    'site/src/review-file.js',
    'site/src/scope-data.js',
    'site/src/scope-manifest.json',
    'site/src/share-record.js',
    'site/src/styles.css',
    'site/src/tag-performance.json',
    'site/src/usage.js',
    'site/src/workflows/About.jsx',
    'site/src/workflows/Assist.jsx',
    'site/src/workflows/HowTagsWork.jsx',
    'site/src/workflows/Legal.jsx',
    'site/src/workflows/Report.jsx',
    'site/src/workflows/Scope.jsx',
    'site/src/workflows/Teamwork.jsx',
    'site/src/workflows/Townhall.jsx',
    'site/src/workflows/community.json',
    'site/src/workflows/index.jsx',
    'site/src/workflows/shared.jsx',
    'site/vite.config.js',
))
STATIC_SOURCE_FACTS = {'site/public/credential-device/method-eea415d989cb0ec4b19a1feccab4f8dc6fa4238e93332cf9d0524f3b3a60e451.json': {'mode': '100644', 'git_blob_oid': '2e03e68a0cf894981f7774d720978c151f327a9d', 'bytes': 178723, 'category': 'reference-copies'}, 'site/public/credential-device/notices.txt': {'mode': '100644', 'git_blob_oid': '4473913cce47dbc8a04fef78506cda42d0b69ec4', 'bytes': 14652, 'category': 'other-retained-terms'}, 'site/public/device-licenses/pyodide-MPL-2.0.txt': {'mode': '100644', 'git_blob_oid': 'a612ad9813b006ce81d1ee438dd784da99a54007', 'bytes': 16725, 'category': 'other-retained-terms'}, 'site/public/device-licenses/python-license.txt': {'mode': '100644', 'git_blob_oid': '20cf39097c68baa17cc566b64e76d34ebf034044', 'bytes': 13804, 'category': 'other-retained-terms'}, 'site/public/device-licenses/source.txt': {'mode': '100644', 'git_blob_oid': '5a9baa995650a82b1d610251e85ac043a842d543', 'bytes': 541, 'category': 'other-retained-terms'}, 'site/public/device-licenses/unicode-license.txt': {'mode': '100644', 'git_blob_oid': '56da58912807030b451a4700687d5bd02c72d6ed', 'bytes': 1995, 'category': 'other-retained-terms'}, 'site/public/downloads/aitrust-id-ps-source.zip': {'mode': '100644', 'git_blob_oid': '60389c300634e11ace07ba06d3dde3b088bb2787', 'bytes': 131039, 'category': 'selected-ps-container'}, 'site/public/downloads/provenance/cd3beab02774fa939e3a2bd8a0d87913d9e8fd81/checker.zip': {'mode': '100644', 'git_blob_oid': '60389c300634e11ace07ba06d3dde3b088bb2787', 'bytes': 131039, 'category': 'selected-ps-container'}, 'site/public/fonts/OFL.txt': {'mode': '100644', 'git_blob_oid': '2ae17359801c71b7b568854b98f73969ad822474', 'bytes': 4393, 'category': 'fonts'}, 'site/public/fonts/nunito-sans-cyrillic-ext.woff2': {'mode': '100644', 'git_blob_oid': '5028a4203c620ffa68f7d5a144656054e24f7a7b', 'bytes': 21752, 'category': 'fonts'}, 'site/public/fonts/nunito-sans-cyrillic.woff2': {'mode': '100644', 'git_blob_oid': '2217b5ca07f53d9dcde277b2ab8069479acacc6c', 'bytes': 16388, 'category': 'fonts'}, 'site/public/fonts/nunito-sans-latin-ext.woff2': {'mode': '100644', 'git_blob_oid': '6c9822760fe10fa8daa2ed6c3200e46e345f067d', 'bytes': 27908, 'category': 'fonts'}, 'site/public/fonts/nunito-sans-latin.woff2': {'mode': '100644', 'git_blob_oid': '4361be683dffd473fd55510ef329597b636fe844', 'bytes': 31076, 'category': 'fonts'}, 'site/public/fonts/nunito-sans-vietnamese.woff2': {'mode': '100644', 'git_blob_oid': '3bfb27c6bbaeb766539747327cc00a851e690a21', 'bytes': 10308, 'category': 'fonts'}, 'site/public/fonts/nunito-sans.css': {'mode': '100644', 'git_blob_oid': 'ec7ed9c2ed523559cee1ca5b4d5ee2b9655c82fc', 'bytes': 1808, 'category': 'fonts'}, 'site/public/fonts/provenance.json': {'mode': '100644', 'git_blob_oid': '6b872d4a3ee6e23f71bce9d5efcda0307e1fa2d1', 'bytes': 2120, 'category': 'fonts'}, 'site/public/hp-device/method-943b5b2352f86c44d80d79625cbdcfca8f25a1719d116640863ca7d730f370fb.json': {'mode': '100644', 'git_blob_oid': 'ef4ff7efbd2e971168a7bb1b156453c6d9e8adf6', 'bytes': 182395, 'category': 'reference-copies'}, 'site/public/hp-device/notices.txt': {'mode': '100644', 'git_blob_oid': '46c443105a337b0c0e3f5befb300b9d20c080809', 'bytes': 14640, 'category': 'other-retained-terms'}, 'site/public/hp-uncertainty-device/notices.txt': {'mode': '100644', 'git_blob_oid': '2df95180386174611ae20acc4903802e3ae2a3ca', 'bytes': 14632, 'category': 'other-retained-terms'}, 'site/public/mt-device/method-28f59d6a00fc2cae0dee86534656969879597fcb2d53fe050b9dcb3d58607750.json': {'mode': '100644', 'git_blob_oid': 'c21e29a8e6da29b0501579df8143b0fc78ec48e4', 'bytes': 190794, 'category': 'reference-copies'}, 'site/public/mt-device/notices.txt': {'mode': '100644', 'git_blob_oid': '2f051ffa478bd8ab40ba4353da058c94e5fe52ae', 'bytes': 14632, 'category': 'other-retained-terms'}, 'site/public/mt-mobile-device/method-cd6e6e257407e87b22947a29d8e836caebcd75e4658acaba6563d02ec858c292.json': {'mode': '100644', 'git_blob_oid': '282d1a2fa5c00ec4b73e898aa679ef55377a8da1', 'bytes': 194524, 'category': 'reference-copies'}, 'site/public/mt-mobile-device/notices.txt': {'mode': '100644', 'git_blob_oid': 'a5faa4e1ce9caa09ad305a42262c7c3d320ce0b6', 'bytes': 14650, 'category': 'other-retained-terms'}, 'site/public/nf-device/notices.txt': {'mode': '100644', 'git_blob_oid': '040ab9818c9c595c1b8096d5cc978fea9e3608f1', 'bytes': 14634, 'category': 'other-retained-terms'}, 'site/public/reference/code-license.txt': {'mode': '100644', 'git_blob_oid': 'd645695673349e3947e8e5ae42332d0ac3164cd7', 'bytes': 11358, 'category': 'project-grant'}, 'site/public/reference/normalization-contract.md': {'mode': '100644', 'git_blob_oid': '9fe5077862fa63436e979fc9cd2baf2ca5cefb47', 'bytes': 2772, 'category': 'reference-copies'}, 'site/public/reference/signal-registry.json': {'mode': '100644', 'git_blob_oid': 'b9231bc597f3358a792ca85ee25a5c8fe376d691', 'bytes': 20546, 'category': 'spec'}, 'site/public/reference/signals.md': {'mode': '100644', 'git_blob_oid': 'e1efe4ea416fc7535de46b08e2cc19b479a2ab7f', 'bytes': 15385, 'category': 'spec'}, 'site/public/reference/spec-license.txt': {'mode': '100644', 'git_blob_oid': 'cb4efa272d6418cc08a78d33fc148dbe36744678', 'bytes': 338, 'category': 'spec'}, 'site/public/reference/taxonomy.md': {'mode': '100644', 'git_blob_oid': '1a031dbe89667cb1210358899fc4643840fc53b0', 'bytes': 5483, 'category': 'spec'}, 'site/public/web-licenses/THIRD-PARTY-NOTICES.txt': {'mode': '100644', 'git_blob_oid': '71ec4db01ff37ca49feb119e4909dc1247ba803d', 'bytes': 47849, 'category': 'other-retained-terms'}, 'site/public/web-licenses/packages.json': {'mode': '100644', 'git_blob_oid': '4a4c9e0242d23ed1c55787089bd0ebf0c97109ea', 'bytes': 38531, 'category': 'other-retained-terms'}, 'site/public/web-licenses/web-runtime.spdx.json': {'mode': '100644', 'git_blob_oid': '998505c0c6207694d9c82bfd2fb5e25b8c105101', 'bytes': 28936, 'category': 'other-retained-terms'}, 'spec/LICENSE': {'mode': '100644', 'git_blob_oid': 'cb4efa272d6418cc08a78d33fc148dbe36744678', 'bytes': 338, 'category': 'spec'}, 'spec/assertion.schema.json': {'mode': '100644', 'git_blob_oid': '9f1a69b9f0b172068a1cc0a570823c347b27b7eb', 'bytes': 13233, 'category': 'spec'}, 'spec/image-provenance-boundary.json': {'mode': '100644', 'git_blob_oid': '464c5b521ec483465a2ac5b8dd50ebb2f4df791c', 'bytes': 390, 'category': 'spec'}, 'spec/organization-audit-metadata.schema.json': {'mode': '100644', 'git_blob_oid': 'dc46431abf5a0e5bc971e047f7271220b5306427', 'bytes': 6616, 'category': 'spec'}, 'spec/signal-registry.json': {'mode': '100644', 'git_blob_oid': 'b9231bc597f3358a792ca85ee25a5c8fe376d691', 'bytes': 20546, 'category': 'spec'}, 'spec/signals.md': {'mode': '100644', 'git_blob_oid': 'e1efe4ea416fc7535de46b08e2cc19b479a2ab7f', 'bytes': 15385, 'category': 'spec'}, 'spec/subject-profiles.json': {'mode': '100644', 'git_blob_oid': 'a8ee3dbebba36e85b695c5049b413629912af609', 'bytes': 1352, 'category': 'spec'}, 'spec/taxonomy.md': {'mode': '100644', 'git_blob_oid': '1a031dbe89667cb1210358899fc4643840fc53b0', 'bytes': 5483, 'category': 'spec'}, 'spec/vendor/spdx-2.3.1/LICENSE': {'mode': '100644', 'git_blob_oid': '44a22d370bba8d13c7dd7449d71b40ea8842788e', 'bytes': 18508, 'category': 'spdx-schema'}, 'spec/vendor/spdx-2.3.1/schema.json': {'mode': '100644', 'git_blob_oid': '2dc11d1a34268227b63113d788b89efd75b5d2a8', 'bytes': 47602, 'category': 'spdx-schema'}, 'spec/vendor/spdx-2.3.1/source.json': {'mode': '100644', 'git_blob_oid': '22126d612a4990dc054e19b27217cb3baa975641', 'bytes': 709, 'category': 'spdx-schema'}, 'spec/versions/0.2.0/assertion.schema.json': {'mode': '100644', 'git_blob_oid': '7303620ad8f47b020d562f8f1a4137c1ef760d0e', 'bytes': 13837, 'category': 'spec'}, 'spec/vocabulary.json': {'mode': '100644', 'git_blob_oid': 'a4a590ca1a739b3bb8f319dc779695ff1dc45c8a', 'bytes': 637, 'category': 'spec'}}
KNOWN_GENERATED_PATHS = frozenset(('404.html', '_headers', 'app-icon-192.png', 'app-icon-512.png', 'assets/CredentialFlowExplorer-mkASPF5q.js', 'assets/HPExplorer-CitS_3ah.js', 'assets/HPUncertaintyExplorer-CkhWqlwQ.js', 'assets/ImageMetadataExplorer-eL-hFPdg.js', 'assets/MTChoiceExplorer-BvBleeWJ.js', 'assets/MTExplorer-D4GR6o3j.js', 'assets/NFExplorer-CeZvaqrF.js', 'assets/credential-device-worker-IB4hBigb.js', 'assets/device-worker-CYlrzLLK.js', 'assets/hp-device-worker-Ckw2-Whn.js', 'assets/hp-uncertainty-worker-RW14Xkr0.js', 'assets/index-BIf5XAql.js', 'assets/index-BZxGydps.css', 'assets/mt-device-worker-BFy14zjg.js', 'assets/mt-mobile-device-result-D6PtgO3Y.js', 'assets/nf-cosine-result-BI_PnUK2.js', 'assets/nf-device-worker-C0Au7N2H.js', 'assets/public-scope-EqYnaeuQ.json', 'camo-q4.svg', 'credential-device/method-eea415d989cb0ec4b19a1feccab4f8dc6fa4238e93332cf9d0524f3b3a60e451.json', 'credential-device/notices.txt', 'device-licenses/pyodide-MPL-2.0.txt', 'device-licenses/python-license.txt', 'device-licenses/python-stdlib-notices.txt', 'device-licenses/source.txt', 'device-licenses/unicode-license.txt', 'device/image-metadata/image-metadata-worker.mjs', 'device/image-metadata/manifest.json', 'device/image-metadata/method-04fe19cbc1e4e712be393acc5ffc746e94f36ba78802ad18588a883c01d68a9f.json', 'device/image-metadata/project-notices.txt', 'device/method-ecc04fa17135175a841e3ef7ddbffb013098c5c6b877611f3ae7347001b9c0c0.py', 'device/mt-choice/manifest.json', 'device/mt-choice/method-a8c876a44dcae65ed92e3bc417fcdde46c6444d4e6f9bc6a9048df91d82841b7.json', 'device/mt-choice/mt-choice-worker.mjs', 'device/mt-choice/project-notices.txt', 'device/runtime-314.0.7/pyodide-lock.json', 'device/runtime-314.0.7/pyodide.asm.mjs', 'device/runtime-314.0.7/pyodide.mjs', 'downloads/aitrust-id-ps-source.zip.sha256', 'downloads/provenance/cd3beab02774fa939e3a2bd8a0d87913d9e8fd81/VERIFY.md', 'downloads/provenance/cd3beab02774fa939e3a2bd8a0d87913d9e8fd81/artifact.spdx.json', 'downloads/provenance/cd3beab02774fa939e3a2bd8a0d87913d9e8fd81/evidence.json', 'downloads/provenance/cd3beab02774fa939e3a2bd8a0d87913d9e8fd81/manifest.json', 'downloads/provenance/cd3beab02774fa939e3a2bd8a0d87913d9e8fd81/sbom.sigstore.json', 'downloads/provenance/cd3beab02774fa939e3a2bd8a0d87913d9e8fd81/verified-observation.json', 'favicon.svg', 'fonts/OFL.txt', 'fonts/nunito-sans-cyrillic-ext.woff2', 'fonts/nunito-sans-cyrillic.woff2', 'fonts/nunito-sans-latin-ext.woff2', 'fonts/nunito-sans-latin.woff2', 'fonts/nunito-sans-vietnamese.woff2', 'fonts/nunito-sans.css', 'fonts/provenance.json', 'googlefd96956266acb393.html', 'hp-device/.gitattributes', 'hp-device/method-943b5b2352f86c44d80d79625cbdcfca8f25a1719d116640863ca7d730f370fb.json', 'hp-device/notices.txt', 'hp-uncertainty-device/hedge-1e05ab4af768a5db89229dcfdb8eb18faf1f8adbf58518b4efe9c56f9bdd01ec.json', 'hp-uncertainty-device/notices.txt', 'index.html', 'manifest.webmanifest', 'mt-device/.gitattributes', 'mt-device/method-28f59d6a00fc2cae0dee86534656969879597fcb2d53fe050b9dcb3d58607750.json', 'mt-device/notices.txt', 'mt-mobile-device/method-cd6e6e257407e87b22947a29d8e836caebcd75e4658acaba6563d02ec858c292.json', 'mt-mobile-device/notices.txt', 'nf-device/cosine-41334bcd5ff9a9fe1842fb1d35f8ebe076ab7f35c8b9d667d2d9523e35574332.json', 'nf-device/literal-c26434149b752d6eba0ba0aefb8cf0a3d9a334035426911f6d5e17896bccb5c7.json', 'nf-device/notices.txt', 'offline-release.json', 'offline-worker.js', 'policies/access/index.html', 'policies/community/index.html', 'policies/contributing/index.html', 'policies/governance/index.html', 'policies/index.html', 'policies/licenses/index.html', 'policies/privacy/index.html', 'policies/security/index.html', 'policies/terms/index.html', 'policies/validation/index.html', 'reference/0004-tag-claim-boundaries.md', 'reference/PS-01-acceptance.md', 'reference/PS-01.md', 'reference/accessibility-evaluation.md', 'reference/accessibility-policy.md', 'reference/accessibility-release-gate.md', 'reference/agent-output.md', 'reference/ai-tools.md', 'reference/assertion-migration.md', 'reference/asset-notices.md', 'reference/author-choice.md', 'reference/backup-retention.md', 'reference/bounded-service-conformance.json', 'reference/browser-checks.json', 'reference/certification-programme-guide.md', 'reference/certification-programme.json', 'reference/certification-programme.md', 'reference/changelog-policy.md', 'reference/changelog.md', 'reference/choice-framing.md', 'reference/code-license.txt', 'reference/command-stress.json', 'reference/conduct-policy.md', 'reference/conformance-runner.md', 'reference/conformance-software-execution.json', 'reference/conformance/index.html', 'reference/container-checks.json', 'reference/context-v6-service.json', 'reference/contributing-policy.md', 'reference/corpus-support.md', 'reference/counterexamples_v2.jsonl', 'reference/credential-flow-device.md', 'reference/decisions.json', 'reference/decisions.md', 'reference/development-dataset-manifest.json', 'reference/directory-software-linux.json', 'reference/draft-privacy.md', 'reference/editorial-workflow.md', 'reference/entity-structure-comparison.md', 'reference/evidence-packet.md', 'reference/evidence-resistance.json', 'reference/evidence-resistance.md', 'reference/example-provenance.json', 'reference/extension-integration.json', 'reference/feedback-analysis.md', 'reference/fetch_execute_v1.jsonl', 'reference/fi-citation-practice.md', 'reference/fi-citation-sidecar-plan.md', 'reference/fi-citation-sidecar.md', 'reference/fleet-deployment.md', 'reference/fleet-linux.json', 'reference/fleet-macos.json', 'reference/frozen-normalization.json', 'reference/frozen-service-conformance.json', 'reference/governance-policy.md', 'reference/hash-inbox-linux.json', 'reference/hash-inbox-macos.json', 'reference/hash-report-intake.md', 'reference/host-capture-linux.json', 'reference/host-capture-macos.json', 'reference/host-capture.md', 'reference/host-recovery.json', 'reference/hp-device-explorer.md', 'reference/hp-uncertainty-device.md', 'reference/image-device-guide.md', 'reference/image-provenance-boundary.md', 'reference/independent-review.md', 'reference/language-observations.md', 'reference/legal-drafts/index.html', 'reference/legal-execution-packet.md', 'reference/live-gap-implementation.json', 'reference/live_gap_v1.jsonl', 'reference/local-reference-corpus.md', 'reference/mark-usage.md', 'reference/measurement-provenance-plan.md', 'reference/michigan-llc-packet.md', 'reference/model-asset-integrity.md', 'reference/mt-choice-device.md', 'reference/mt-device-explorer.md', 'reference/mt-evidence-workflow.md', 'reference/mt-mobile-quotation.md', 'reference/native-dependency-evidence.md', 'reference/native-engine-checks.md', 'reference/native-share-developer.md', 'reference/native-share-engine.json', 'reference/native-share-workflow.json', 'reference/nf-device-reference.md', 'reference/nf-source-evidence.md', 'reference/nli-pairs.md', 'reference/nli-references.md', 'reference/normalization-contract.md', 'reference/offline-editor.html', 'reference/offline-tools/index.html', 'reference/open-validation-path.md', 'reference/operate/index.html', 'reference/organization-audit-linux.json', 'reference/organization-audit.md', 'reference/organization-directory.md', 'reference/organization-policy-acceptance.md', 'reference/organization-policy-registry.md', 'reference/performance-device.json', 'reference/performance-regressions.json', 'reference/pii-compact-addresses.json', 'reference/pii-recognition-development.json', 'reference/pipeline-performance.json', 'reference/policies/access/v1.0.txt', 'reference/policies/access/v1.1.txt', 'reference/policies/access/v1.10.txt', 'reference/policies/access/v1.11.txt', 'reference/policies/access/v1.12.txt', 'reference/policies/access/v1.13.txt', 'reference/policies/access/v1.14.txt', 'reference/policies/access/v1.15.txt', 'reference/policies/access/v1.2.txt', 'reference/policies/access/v1.3.txt', 'reference/policies/access/v1.4.txt', 'reference/policies/access/v1.5.txt', 'reference/policies/access/v1.6.txt', 'reference/policies/access/v1.7.txt', 'reference/policies/access/v1.8.txt', 'reference/policies/access/v1.9.txt', 'reference/policies/community/v1.0.txt', 'reference/policies/community/v1.1.txt', 'reference/policies/community/v1.10.txt', 'reference/policies/community/v1.11.txt', 'reference/policies/community/v1.12.txt', 'reference/policies/community/v1.13.txt', 'reference/policies/community/v1.14.txt', 'reference/policies/community/v1.15.txt', 'reference/policies/community/v1.2.txt', 'reference/policies/community/v1.3.txt', 'reference/policies/community/v1.4.txt', 'reference/policies/community/v1.5.txt', 'reference/policies/community/v1.6.txt', 'reference/policies/community/v1.7.txt', 'reference/policies/community/v1.8.txt', 'reference/policies/community/v1.9.txt', 'reference/policies/contributing/v1.0.txt', 'reference/policies/contributing/v1.1.txt', 'reference/policies/contributing/v1.10.txt', 'reference/policies/contributing/v1.11.txt', 'reference/policies/contributing/v1.12.txt', 'reference/policies/contributing/v1.13.txt', 'reference/policies/contributing/v1.14.txt', 'reference/policies/contributing/v1.15.txt', 'reference/policies/contributing/v1.2.txt', 'reference/policies/contributing/v1.3.txt', 'reference/policies/contributing/v1.4.txt', 'reference/policies/contributing/v1.5.txt', 'reference/policies/contributing/v1.6.txt', 'reference/policies/contributing/v1.7.txt', 'reference/policies/contributing/v1.8.txt', 'reference/policies/contributing/v1.9.txt', 'reference/policies/governance/v1.0.txt', 'reference/policies/governance/v1.1.txt', 'reference/policies/governance/v1.10.txt', 'reference/policies/governance/v1.11.txt', 'reference/policies/governance/v1.12.txt', 'reference/policies/governance/v1.13.txt', 'reference/policies/governance/v1.14.txt', 'reference/policies/governance/v1.15.txt', 'reference/policies/governance/v1.2.txt', 'reference/policies/governance/v1.3.txt', 'reference/policies/governance/v1.4.txt', 'reference/policies/governance/v1.5.txt', 'reference/policies/governance/v1.6.txt', 'reference/policies/governance/v1.7.txt', 'reference/policies/governance/v1.8.txt', 'reference/policies/governance/v1.9.txt', 'reference/policies/licenses/v1.0.txt', 'reference/policies/licenses/v1.1.txt', 'reference/policies/licenses/v1.10.txt', 'reference/policies/licenses/v1.11.txt', 'reference/policies/licenses/v1.12.txt', 'reference/policies/licenses/v1.13.txt', 'reference/policies/licenses/v1.14.txt', 'reference/policies/licenses/v1.15.txt', 'reference/policies/licenses/v1.2.txt', 'reference/policies/licenses/v1.3.txt', 'reference/policies/licenses/v1.4.txt', 'reference/policies/licenses/v1.5.txt', 'reference/policies/licenses/v1.6.txt', 'reference/policies/licenses/v1.7.txt', 'reference/policies/licenses/v1.8.txt', 'reference/policies/licenses/v1.9.txt', 'reference/policies/privacy/v1.0.txt', 'reference/policies/privacy/v1.1.txt', 'reference/policies/privacy/v1.10.txt', 'reference/policies/privacy/v1.11.txt', 'reference/policies/privacy/v1.12.txt', 'reference/policies/privacy/v1.13.txt', 'reference/policies/privacy/v1.14.txt', 'reference/policies/privacy/v1.15.txt', 'reference/policies/privacy/v1.2.txt', 'reference/policies/privacy/v1.3.txt', 'reference/policies/privacy/v1.4.txt', 'reference/policies/privacy/v1.5.txt', 'reference/policies/privacy/v1.6.txt', 'reference/policies/privacy/v1.7.txt', 'reference/policies/privacy/v1.8.txt', 'reference/policies/privacy/v1.9.txt', 'reference/policies/security/v1.0.txt', 'reference/policies/security/v1.1.txt', 'reference/policies/security/v1.10.txt', 'reference/policies/security/v1.11.txt', 'reference/policies/security/v1.12.txt', 'reference/policies/security/v1.13.txt', 'reference/policies/security/v1.14.txt', 'reference/policies/security/v1.15.txt', 'reference/policies/security/v1.2.txt', 'reference/policies/security/v1.3.txt', 'reference/policies/security/v1.4.txt', 'reference/policies/security/v1.5.txt', 'reference/policies/security/v1.6.txt', 'reference/policies/security/v1.7.txt', 'reference/policies/security/v1.8.txt', 'reference/policies/security/v1.9.txt', 'reference/policies/terms/v1.0.txt', 'reference/policies/terms/v1.1.txt', 'reference/policies/terms/v1.10.txt', 'reference/policies/terms/v1.11.txt', 'reference/policies/terms/v1.12.txt', 'reference/policies/terms/v1.13.txt', 'reference/policies/terms/v1.14.txt', 'reference/policies/terms/v1.15.txt', 'reference/policies/terms/v1.2.txt', 'reference/policies/terms/v1.3.txt', 'reference/policies/terms/v1.4.txt', 'reference/policies/terms/v1.5.txt', 'reference/policies/terms/v1.6.txt', 'reference/policies/terms/v1.7.txt', 'reference/policies/terms/v1.8.txt', 'reference/policies/terms/v1.9.txt', 'reference/policies/validation/v1.0.txt', 'reference/policies/validation/v1.1.txt', 'reference/policies/validation/v1.10.txt', 'reference/policies/validation/v1.11.txt', 'reference/policies/validation/v1.12.txt', 'reference/policies/validation/v1.13.txt', 'reference/policies/validation/v1.14.txt', 'reference/policies/validation/v1.15.txt', 'reference/policies/validation/v1.2.txt', 'reference/policies/validation/v1.3.txt', 'reference/policies/validation/v1.4.txt', 'reference/policies/validation/v1.5.txt', 'reference/policies/validation/v1.6.txt', 'reference/policies/validation/v1.7.txt', 'reference/policies/validation/v1.8.txt', 'reference/policies/validation/v1.9.txt', 'reference/policy-access.txt', 'reference/policy-community.txt', 'reference/policy-contributing.txt', 'reference/policy-governance.txt', 'reference/policy-licenses.txt', 'reference/policy-privacy.txt', 'reference/policy-security.txt', 'reference/policy-terms.txt', 'reference/policy-validation.txt', 'reference/private-policy.md', 'reference/ps-efficiency.json', 'reference/ps-routing-gates.json', 'reference/ps-routing-regressions.json', 'reference/ps-source-distribution.md', 'reference/ps_v1.jsonl', 'reference/public-scope.json', 'reference/redaction-compact-addresses.json', 'reference/redaction-recognition.json', 'reference/redaction-recognition.md', 'reference/reference-revisions.md', 'reference/regression-gates.json', 'reference/remote-ai-connections.md', 'reference/remote-ai/index.html', 'reference/remote-openapi.json', 'reference/reproducibility-controls-plan.md', 'reference/routing_boundaries_v1.jsonl', 'reference/security-operations.md', 'reference/security-policy.md', 'reference/selected-reference-comparison.md', 'reference/selected-reference-pair-plan.md', 'reference/service-resource-faults.json', 'reference/session-revision-plan.md', 'reference/session-revision-result.md', 'reference/session-revisions.md', 'reference/signal-registry.json', 'reference/signals.md', 'reference/social-launch-kit.md', 'reference/spec-license.txt', 'reference/subject-contract.md', 'reference/subjects-v2.json', 'reference/synthid-vendor-input.md', 'reference/tag-performance-evidence.json', 'reference/tag-performance-plan.md', 'reference/tag-performance.json', 'reference/tag-safety-use-cases.md', 'reference/taxonomy.md', 'research-feedback.js', 'robots.txt', 'runtime-js-sources/NOTICES.txt', 'runtime-js-sources/index.json', 'runtime-zlib-sources/NOTICES.txt', 'runtime-zlib-sources/index.json', 'share-card.png', 'sitemap.xml', 'tag-logo.svg', 'tags/audit/index.html', 'tags/bt/index.html', 'tags/fa/index.html', 'tags/fi/index.html', 'tags/fleet/index.html', 'tags/host/index.html', 'tags/hp/index.html', 'tags/index.html', 'tags/iv/index.html', 'tags/mt/index.html', 'tags/nf/index.html', 'tags/pa/index.html', 'tags/pii-outbound/index.html', 'tags/pii-redacted/index.html', 'tags/proprietary/index.html', 'tags/ps/index.html', 'tags/sc/index.html', 'tags/sso/index.html', 'tags/support/index.html', 'tags/uc/index.html', 'tags/unk/index.html', 'theme.js', 'web-licenses/THIRD-PARTY-NOTICES.txt', 'web-licenses/packages.json', 'web-licenses/web-runtime.spdx.json'))
SOURCE_PINS = {'tools/artifact_evidence_io.py': {'bytes': 12720, 'sha256': '2d8089a460d0b70c7725ce8bfdecda88b798c70d3335cfbb22c8fe5b31ea0b4e'}, 'tools/artifact_process.py': {'bytes': 4311, 'sha256': 'aa178ad04bc8adbcdb1eb40c556b0bd9b2bfea76d07843ef0883511f55b4eb86'}, 'tools/distribution_artifacts.py': {'bytes': 39116, 'sha256': '548922881ab62b2c5b9af9dffd09496e4906ca252050bee0495a5f85b8a79e3c'}, 'tools/dependency_policy.py': {'bytes': 15682, 'sha256': 'e72e478a7508e6c3e6e000803ee4d583900f626cc219870fd1ad140131608408'}, 'eval/dependency-policy.json': {'bytes': 34311, 'sha256': '8db769dbd924e0b4c5ec4b5d92f4e953b0b4cf4cf78656f1dca3a544949ed2b6'}, 'tools/web_distribution.py': {'bytes': 25493, 'sha256': '56214c9e270c6c9ac05860a74931400fa7135fc43f2afb2c013add2bf6c66215'}, 'site/package-lock.json': {'bytes': 118066, 'sha256': '527f689fcb38beb9de7756c227084b41e9afcf547de92c687646edd90e01449e'}, 'site/vite.config.js': {'bytes': 136, 'sha256': 'bc433d16bf5cdafc2c6553b661e6ab4380c392e1d132c4cc253c1af8934d770d'}, 'sbom/notices/manifest.json': {'bytes': 336057, 'sha256': '8a19f0328c542c610fb5028e78313c80e7bf40c2d4e51f281a144883ee95bb58'}, 'sbom/assets/notices.json': {'bytes': 11659, 'sha256': '5c165aea3c716a183174a10ce8be0b5e0894554a8ad5492171e5141dc642facd'}, 'LICENSE': {'bytes': 11358, 'sha256': 'cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30'}, 'NOTICE': {'bytes': 1134, 'sha256': 'e185f305c76f821aa56011cd201ea03f49e97c57dfc786517f77bfc00c7fecd6'}, 'eval/vectors/unicode/LICENSE.txt': {'bytes': 1995, 'sha256': 'e7a93b009565cfce55919a381437ac4db883e9da2126fa28b91d12732bc53d96'}, 'spec/LICENSE': {'bytes': 338, 'sha256': 'dc5be08778ad83fc1be1c18c28788bee9e7848ac3bd68ef33129f402205f6e77'}, 'site/public/fonts/OFL.txt': {'bytes': 4393, 'sha256': 'efbb0c9e864cef973982d9a17567e6be5c3d1759695574586f3f18c7ecca064b'}}

STATIC_SOURCE_FACTS['site/public/mt-mobile-device/method-53b8a0016d40a7abae5f069f83a160787ca2264907c673c0ba0d09a5fa3f6191.json'] = {'mode': '100644', 'git_blob_oid': 'aa5d456611c1b6e72685f62a02ff0ebb2932bd42', 'bytes': 195760, 'category': 'reference-copies'}

STATIC_SOURCE_FACTS['LICENSE'] = {'mode': '100644', 'git_blob_oid': 'd645695673349e3947e8e5ae42332d0ac3164cd7', 'bytes': 11358, 'category': 'project-grant'}

BUILD_INPUTS = ('site/package.json','site/package-lock.json','site/vite.config.js',
 'site/scripts/prepare.mjs','site/scripts/prepare-device.mjs','site/scripts/prepare-performance.mjs',
 'site/scripts/prepare-offline.mjs','site/scripts/render-reference.mjs','scripts/web-checker-build-observer.mjs')
CARRY = ('LICENSE','NOTICE','spec/LICENSE','eval/vectors/unicode/LICENSE.txt','site/public/fonts/OFL.txt')
BUILD_NOTICES = 'web-obligations/BUILD-SOURCE-NOTICES.txt'
BUILD_GRANTS = 'web-obligations/source-grants.json'
OBSERVATION = 'web-build-observations.json'
FIXED_AUTH_ROUTE = 'web-checker'


def exact_keys(value, keys):
    need(type(value)is dict and set(value)==set(keys))


def file_row(value):
    exact_keys(value,('bytes','sha256','mode'))
    need(type(value['bytes'])is int and 0<=value['bytes']<=MAX_MEMBER
         and type(value['mode'])is int and value['mode']==0o644
         and type(value['sha256'])is str and re.fullmatch('[a-f0-9]{64}',value['sha256']))


def row(raw): return {'bytes':len(raw),'sha256':sha(raw),'mode':0o644}


def collision_free(names):
    seen=set()
    for name in names:
        path_name(name);folded=name.casefold();need(folded not in seen);seen.add(folded)
    for folded in seen:
        need(not any('/'.join(folded.split('/')[:i])in seen for i in range(1,len(folded.split('/')))))


def git_oid(raw):return hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()


def _private_module(raw,name,filename,imports=None):
    """Execute only independently pinned project code, never received code."""
    import builtins
    import types
    module=types.ModuleType(name);module.__file__=str(filename)
    importer=builtins.__import__
    def importing(target,globals=None,locals=None,fromlist=(),level=0):
        if imports and target in imports:return imports[target]
        return importer(target,globals,locals,fromlist,level)
    module.__dict__['__builtins__']={**vars(builtins),'__import__':importing}
    exec(compile(raw,str(filename),'exec'),module.__dict__)
    return module


def runtime_expected(root,ledger):
    """Precharge the immutable helper; release every nested capture before AUTH."""
    import types
    ledger.charge(64_000_000);need(ledger.calls+128<=MAX_READ_CALLS);ledger.calls+=128
    need(ledger.fds==0)
    with FileTree(root,ledger)as tree:
        io_raw=tree.read('tools/artifact_evidence_io.py',2_000_000,expected=SOURCE_PINS['tools/artifact_evidence_io.py'])
        method=tree.read('tools/web_runtime_obligations.py',2_000_000)
        need(sha(method)==RUNTIME_METHOD_SHA256)
        tree.check()
    io=_private_module(io_raw,'_web_fixed_io',Path(root)/'tools/artifact_evidence_io.py')
    helper=_private_module(method,'_web_fixed_runtime',Path(root)/'tools/web_runtime_obligations.py',
      {'tools':types.SimpleNamespace(artifact_evidence_io=io)})
    b=helper.Budget(Path(root))
    try:
        m=b.initialize();result=helper.expected(b,m);b.finish()
        need(len(result)==14 and helper.MANIFEST_SHA256==RUNTIME_MANIFEST_SHA256)
        ledger.peak_fds=max(ledger.peak_fds,len(b.capture.fds))
        runtime={'device/runtime-314.0.7/'+name:value for name,value in m['runtime'].items()}
        inputs={name:value.copy()for name,value in m['inputs'].items()}
    finally:b.close()
    ledger.tick();return result,runtime,inputs


def source_catalog(root,ledger):
    """Exact retained grants and unchanged format-producing code, no SDK import."""
    runtime,runtime_rows,runtime_inputs=runtime_expected(root,ledger)
    import types
    with FileTree(root,ledger)as tree:
        pins={name:tree.read(name,MAX_RECORD,expected=expected)for name,expected in SOURCE_PINS.items()}
        selected_inputs={name:{'bytes':len(raw),'sha256':sha(raw)}for name,raw in pins.items()}
        method=pins['tools/web_distribution.py']
        def read(selected_root,name,limit):
            need(Path(selected_root).absolute()==Path(root).absolute())
            source_name(name)
            if name in SOURCE_PINS:
                value=tree.read(name,min(limit,MAX_RECORD),expected=SOURCE_PINS[name]);selected_inputs[name]={'bytes':len(value),'sha256':sha(value)};return value
            raw=tree.read(name,min(limit,MAX_RECORD));selected_inputs[name]={'bytes':len(raw),'sha256':sha(raw)}
            if name.startswith('sbom/notices/')and name.endswith('.txt'):
                need(sha(raw)==Path(name).stem)
            return raw
        original=_private_module(method,'_web_fixed_notices',Path(root)/'tools/web_distribution.py',
          {'tools.dependency_policy':types.SimpleNamespace(read=read)})
        outputs,index=original.expected(Path(root))
        need(index['package_count']==35)
        npm={'node_modules/'+r['name']:r for r in index['packages']}
        lock=parse(pins['site/package-lock.json'],ledger)
        observed=parse(pins['sbom/notices/manifest.json'],ledger)
        providers={};grants={name:pins[name]for name in CARRY}
        for package,version in GENERATOR_PACKAGES.items():
            candidate=[r for r in observed['npm']if r.get('lock')=='site/package-lock.json'and r.get('package_path')==package]
            need(len(candidate)==1);r=candidate[0]
            need(r['version']==version and lock['packages'][package]['version']==version and r['license_declared']=='MIT')
            texts=[]
            for item in r['notices']:
                # Exact archived primary notice membership, never a license expression fallback.
                name=item['notice'];raw=read(root,name,MAX_RECORD)
                need(len(raw)==item['bytes']and sha(raw)==item['sha256'])
                grants[name]=raw;texts.append(name)
            need(texts);providers[package]={'version':version,'notice_paths':sorted(texts),'scope':'emitted source only; no native build binary rights'}
        # The immutable runtime helper already independently pins these primary facts.
        for name in ('sbom/web-runtime/react-exact-release-project-grant-facts.json',):
            need(name in runtime_inputs);grants[name]=tree.read(name,MAX_RECORD,expected=runtime_inputs[name])
        result={**runtime,**{'web-licenses/'+name:raw for name,raw in outputs.items()}}
        tree.check()
    need(sum(map(len,result.values()))<=10_000_000)
    return {'outputs':result,'runtime':runtime_rows,'runtime_inputs':runtime_inputs,
            'npm':npm,'providers':providers,'grants':grants,'lock':lock,'pins':SOURCE_PINS.copy(),
            'selected_inputs':selected_inputs}


def committed_source(root,commit,ledger):
    need(type(commit)is str and re.fullmatch('[a-f0-9]{40}',commit))
    import sys
    with FileTree(root,ledger)as tree:
        raw=tree.read('tools/artifact_process.py',MAX_RECORD,expected=SOURCE_PINS['tools/artifact_process.py']);tree.check()
    supervisor=_private_module(raw,'_web_fixed_process',Path(root)/'tools/artifact_process.py')
    # Git's internal reads are opaque. The fixed <=2MB output is precharged.
    ledger.charge(2_000_000)
    outcome=supervisor.run_worker(['git','-C',str(Path(root).absolute()),'ls-tree','-rlz','--full-tree',commit],
      input=b'',timeout=min(30,max(.001,ledger.deadline-time.monotonic())),output_limit=2_000_000)
    need(outcome.returncode==0 and outcome.stdout.endswith(b'\0'))
    result={}
    for rawrow in outcome.stdout[:-1].split(b'\0'):
        need(len(result)<16384)
        fields,name=rawrow.split(b'\t',1);mode,kind,oid,size=fields.split()
        name=name.decode('utf8');need(name not in result and kind==b'blob'and mode in(b'100644',b'100755'))
        need(re.fullmatch(b'[0-9a-f]{40}',oid)and re.fullmatch(b'[0-9]+',size))
        result[name]={'mode':mode.decode(),'git_blob_oid':oid.decode(),'bytes':int(size)}
    ledger.charge(256)
    outcome=supervisor.run_worker(['git','-C',str(Path(root).absolute()),'rev-parse',commit+'^{tree}'],
      input=b'',timeout=min(5,max(.001,ledger.deadline-time.monotonic())),output_limit=256)
    need(outcome.returncode==0 and re.fullmatch(b'[a-f0-9]{40}\n',outcome.stdout))
    return result,outcome.stdout.strip().decode()


def _notice_rows(rows,raw=None):
    need(type(rows)is list and len(rows)<=64);total=0
    for item in rows:
        exact_keys(item,('offset','bytes','sha256','text'))
        need(type(item['offset'])is int and item['offset']>=0 and type(item['bytes'])is int and item['bytes']>0
             and type(item['text'])is str)
        text=item['text'].encode('utf8');need(len(text)==item['bytes']and sha(text)==item['sha256'])
        total+=len(text);need(total<=16384)
        if raw is not None:need(raw[item['offset']:item['offset']+len(text)]==text)
    return total


def validate_observation(observation,commit,source,tree_oid,catalog,tree,ledger):
    exact_keys(observation,('profile','source_commit','source_tree_oid','sources','modules','outputs','toolchain','claims'))
    need(observation['profile']==BUILD_PROFILE and observation['source_commit']==commit and observation['source_tree_oid']==tree_oid
      and observation['toolchain']=={'vite':'8.3.4','rolldown':'1.2.13'})
    need(observation['claims']=={'permission_issued':False,'release_authorized':False,'compiled_equivalence_proved':False}
      and all(type(v)is bool and not v for v in observation['claims'].values()))
    sources=observation['sources'];modules=observation['modules'];outputs=observation['outputs']
    need(type(sources)is dict and 0<len(sources)<=MAX_MODULES and set(BUILD_INPUTS)<=set(sources)
      and type(modules)is dict and 0<len(modules)<=MAX_MODULES and type(outputs)is dict and 0<len(outputs)<=MAX_FILES)
    total=notices=associations=0;source_bodies={}
    for name,item in sources.items():
        source_name(name);exact_keys(item,('bytes','sha256','git_blob_oid','text_source','notices'))
        need(type(item['bytes'])is int and 0<=item['bytes']<=MAX_RECORD and type(item['text_source'])is bool
          and type(item['sha256'])is str and re.fullmatch('[a-f0-9]{64}',item['sha256'])
          and type(item['git_blob_oid'])is str and re.fullmatch('[a-f0-9]{40}',item['git_blob_oid']))
        total+=item['bytes'];need(total<=32_000_000);notices+=_notice_rows(item['notices']);need(notices<=256000)
        if name.startswith('site/node_modules/'):
            remainder=name[len('site/'):];parts=remainder.split('/')
            package='/'.join(parts[:3]if parts[1].startswith('@')else parts[:2])
            need(package in catalog['npm']or package in catalog['providers'])
            need('node_modules'not in remainder[len(package)+1:].split('/'))
            need(package in catalog['lock']['packages'])
            # Installed module bytes are observed in the protected builder, not assumed reproducible.
        else:
            need(name in source and (name in PROJECT_SOURCE_NAMES or name in STATIC_SOURCE_FACTS))
            expected=source[name];need(item['bytes']==expected['bytes']and item['git_blob_oid']==expected['git_blob_oid'])
            if name in STATIC_SOURCE_FACTS:need(all(expected[k]==STATIC_SOURCE_FACTS[name][k]for k in ('mode','git_blob_oid','bytes')))
            raw=tree.read(name,MAX_RECORD);need(sha(raw)==item['sha256']and git_oid(raw)==item['git_blob_oid'])
            if item['text_source']:raw.decode('utf8')
            notices2=_notice_rows(item['notices'],raw);need(notices2<=16384)
            source_bodies[name]=raw
    used=set()
    for key,item in modules.items():
        exact_keys(item,('id','kind','provider','source_path','source','source_notices','transformed'))
        need(key==item['id']and type(key)is str and len(key)<=1024)
        if item['kind']=='virtual':
            need(key in VIRTUAL_PROVIDERS and item['provider']==VIRTUAL_PROVIDERS[key]and item['source_path']is None and item['source']is None)
            notices+=_notice_rows(item['source_notices']);need(notices<=256000)
        else:
            need(item['kind']in('project','npm')and item['provider']is None and item['source_path']in sources)
            name=item['source_path'];source_name(name)
            need(key.startswith('file:'+name)and (key[len('file:'+name):]==''or key[len('file:'+name):].startswith('?'))and re.fullmatch(r'[A-Za-z0-9_.?=&%-]*',key[len('file:'+name):])
                 and len(key[len('file:'+name):])<=160)
            need((item['kind']=='npm')==name.startswith('site/node_modules/'))
            need(item['source']==sources[name]and item['source_notices']==sources[name]['notices'])
        transformed=item['transformed']
        if transformed is not None:
            exact_keys(transformed,('bytes','sha256'));need(type(transformed['bytes'])is int and 0<=transformed['bytes']<=MAX_RECORD
              and type(transformed['sha256'])is str and re.fullmatch('[a-f0-9]{64}',transformed['sha256']))
    for name,item in outputs.items():
        path_name(name);exact_keys(item,('kind','bytes','sha256','modules','imports','dynamic_imports'))
        file_row({k:item[k]for k in ('bytes','sha256')}|{'mode':0o644})
        need(item['kind']in('chunk','asset')and type(item['modules'])is list and len(item['modules'])<=MAX_MODULES)
        ids=[]
        for component in item['modules']:
            exact_keys(component,('id','rendered_length'));need(component['id']in modules and type(component['rendered_length'])is int and 0<=component['rendered_length']<=MAX_MEMBER)
            ids.append(component['id']);used.add(component['id']);associations+=1;need(associations<=8192)
        need(ids==sorted(set(ids)))
        for key in ('imports','dynamic_imports'):
            values=item[key];need(type(values)is list and len(values)<=MAX_MODULES and values==sorted(set(values)))
            for value in values:path_name(value);need(value in outputs);associations+=1;need(associations<=8192)
        if item['kind']=='asset':need(not item['modules']and not item['imports']and not item['dynamic_imports'])
    need(any(x['kind']=='chunk'for x in outputs.values()))
    # All observed modules remain in the record, including tree-shaken inputs.
    return used


def obligation_outputs(catalog,observation):
    bundle=bytearray(b'AI Trust ID: complete selected web source/build attribution.\n'
      b'Source/module notices supplement the unchanged npm and runtime notice files.\n'
      b'No native builder, binary equivalence, global rights or accuracy claim.\n'
      b'React scrollbar 2.3.8 project-grant correspondence is a documented inference; exact Git recovery remains absent.\n')
    anchors={}
    for name,raw in sorted(catalog['grants'].items()):
        need(len(bundle)+len(raw)+len(name)+32<=2_000_000)
        bundle.extend(('\n===== '+name+' =====\n').encode());start=len(bundle);bundle.extend(raw);bundle.extend(b'\n')
        anchors[name]=row(raw)|{'span':[start,start+len(raw)]}
    for key,item in sorted(observation['modules'].items()):
        for notice in item['source_notices']:
            raw=notice['text'].encode('utf8');need(len(bundle)+len(raw)+len(key)+32<=2_000_000)
            bundle.extend(('\nModule '+key+'\n').encode());bundle.extend(raw);bundle.extend(b'\n')
    info={'profile':'web-source-grant-projection/v1','anchors':anchors,'providers':catalog['providers'],
          'npm_packages':sorted(catalog['npm']),'react_relationship':'project-wide grant correspondence inference, not exact Git recovery',
          'optional_wasi_declaration_gaps':['@emnapi/core','@emnapi/wasi-threads','@napi-rs/wasm-runtime','@tybys/wasm-util'],
          'build_observation_sha256':sha(encoded(observation)+b'\n'),'claims':FALSE_CLAIMS.copy()}
    return {BUILD_NOTICES:bytes(bundle),BUILD_GRANTS:encoded(info)+b'\n'}


def _static_origin(name,actual,source,catalog):
    candidate='site/public/'+name
    if candidate in source:
        expected=source[candidate]
        if candidate in STATIC_SOURCE_FACTS:
            fact=STATIC_SOURCE_FACTS[candidate]
            need(all(expected[k]==fact[k]for k in ('mode','git_blob_oid','bytes')))
            return {'kind':'copied-source','source_path':candidate,'category':fact['category'],'git_blob_oid':expected['git_blob_oid']}
        need(candidate in PROJECT_SOURCE_NAMES)
        return {'kind':'project-public','source_path':candidate,'git_blob_oid':expected['git_blob_oid']}
    need(name in KNOWN_GENERATED_PATHS)
    return {'kind':'project-generated','generators':list(BUILD_INPUTS)}


def bound_build(observation,files,source,commit,tree_oid,catalog,tree,ledger):
    used=validate_observation(observation,commit,source,tree_oid,catalog,tree,ledger)
    need(type(files)is dict and 0<len(files)<=MAX_FILES);collision_free(files)
    origins={}
    for name,actual in files.items():
        file_row(actual)
        if name in catalog['outputs']:
            need(actual==row(catalog['outputs'][name]));origins[name]={'kind':'required-obligation'}
        elif name in catalog['runtime']:
            expected=catalog['runtime'][name];need(actual['bytes']==expected['bytes']and actual['sha256']==expected['sha256'])
            origins[name]={'kind':'exact-runtime'}
        elif name==OBSERVATION:
            need(actual==row(encoded(observation)+b'\n'));origins[name]={'kind':'build-observation'}
        elif name in (BUILD_NOTICES,BUILD_GRANTS):origins[name]={'kind':'additional-attribution'}
        elif name in observation['outputs']:
            expected=observation['outputs'][name];need(actual['bytes']==expected['bytes']and actual['sha256']==expected['sha256'])
            origins[name]={'kind':'bundler-output'}
        else:origins[name]=_static_origin(name,actual,source,catalog)
    mandatory=set(catalog['outputs'])|set(catalog['runtime'])|set(observation['outputs'])|{OBSERVATION,BUILD_NOTICES,BUILD_GRANTS}
    need(mandatory<=set(files))
    return {'profile':PROFILE,'source_commit':commit,'source_tree_oid':tree_oid,'observation':observation,
      'file_origins':origins,'files':files,'claims':FALSE_CLAIMS.copy()}

class PrivateStage:
    """New private output, conservative retention on every post-attempt failure."""
    def __init__(self,destination,ledger):
        self.path=Path(destination).absolute();self.ledger=ledger;self.parent=None;self.tree=None
        self.attempted=False;self.success=False
    def __enter__(self):
        import shutil
        need(self.path.name not in ('','.','..')and len(self.path.name)<=120)
        self.parent=FileTree(self.path.parent,self.ledger,private=True)
        try:
            try:os.stat(self.path.name,dir_fd=self.parent.fd,follow_symlinks=False)
            except FileNotFoundError:pass
            else:raise WebUnavailable()
            need(shutil.disk_usage(self.path.parent).free>=2*1024**3+213_000_000)
            self.parent.check();self.attempted=True;self.ledger.output_attempted=True
            os.mkdir(self.path.name,0o700,dir_fd=self.parent.fd)
            self.tree=FileTree(self.path,self.ledger,private=True)
            return self
        except BaseException:
            try:self.close()
            except BaseException:pass
            if self.attempted:raise WebOutputUncertain()from None
            raise WebUnavailable()from None
    @contextlib.contextmanager
    def new_file(self,name):
        path_name(name);need('/'not in name);owned=[];error=None
        try:
            self.tree.check();fd=self.tree._open(name,os.O_RDWR|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=self.tree.fd,owned=owned)
            yield fd
            os.fsync(fd)
        except BaseException as failure:error=failure
        finally:
            while owned:
                try:self.ledger.close(owned.pop())
                except BaseException as failure:
                    if error is None:error=failure
            if error is not None:raise WebOutputUncertain()from None
    def save(self,name,raw):
        with self.new_file(name)as fd:_write_all(fd,raw,self.ledger)
    def check(self):
        self.parent.check();self.tree.check()
        a=os.stat(self.path.name,dir_fd=self.parent.fd,follow_symlinks=False);b=os.fstat(self.tree.fd)
        need((a.st_dev,a.st_ino,a.st_mode)==(b.st_dev,b.st_ino,b.st_mode))
    def close(self):
        error=None
        for name in ('tree','parent'):
            value=getattr(self,name);setattr(self,name,None)
            if value is not None:
                try:value.close()
                except BaseException as failure:
                    if error is None:error=failure
        if error is not None:raise WebOutputUncertain()from None
    def __exit__(self,kind,value,tb):
        error=value
        try:
            if error is None:self.check()
        except BaseException as failure:error=failure
        try:self.close()
        except BaseException as failure:
            if error is None:error=failure
        if error is not None:raise WebOutputUncertain()from None


def _chunks(tree,name,size):
    with tree.file(name,size,expected_size=size)as(fd,info):
        at=0
        while at<size:
            tree.ledger.tick();raw=os.read(fd,min(65536,size-at));need(raw);at+=len(raw);yield raw


def _byte_chunks(raw):
    for at in range(0,len(raw),65536):yield raw[at:at+65536]


def _summary(ledger,**values):
    claims=FALSE_CLAIMS.copy()
    # Operational signature/authorization may become true only after the fixed AUTH path.
    for name in ('attestation_verified','release_authorized'):
        if name in values:need(type(values[name])is bool);claims[name]=values[name]
    return {'profile':PROFILE,'pass':True,**values,'resources':{
      'logical_read_bytes':ledger.own_bytes,'legacy_read_reservation':ledger.legacy_bytes,
      'read_calls':ledger.calls,'peak_owned_fds':ledger.peak_fds},'claims':claims}



def _boundary(function):
    def run(*args,**kwargs):
        try:return function(*args,**kwargs)
        except WebUnavailable:raise
        except Exception:raise WebUnavailable()from None
    return run


@_boundary
def verify_sources(root=ROOT):
    ledger=Ledger()
    with operation(ledger):
        catalog=source_catalog(root,ledger)
        return _summary(ledger,runtime_files=5,runtime_companions=14,npm_packages=35,
          source_generator_packages=3,complete_build_observed=False,
          required_companions={n:row(b)for n,b in catalog['outputs'].items()})


@_boundary
def prepare(directory,destination,source_commit,root=ROOT):
    """Package a complete genuinely observed local build; no received code executes."""
    ledger=Ledger()
    with operation(ledger):
        catalog=source_catalog(root,ledger)
        source,tree_oid=committed_source(root,source_commit,ledger)
        bind_catalog_source(root,source,catalog,ledger)
        with FileTree(root,ledger)as source_tree,FileTree(directory,ledger)as dist:
            inventory=dist.inventory();need(OBSERVATION in inventory)
            observation_raw=dist.read(OBSERVATION,MAX_RECORD)
            observation=parse(observation_raw,ledger);need(encoded(observation)+b'\n'==observation_raw)
            extras={**catalog['outputs'],**obligation_outputs(catalog,observation)}
            descriptions={name:dist.describe(name)for name in inventory}
            files={name:{k:v for k,v in item.items()if k!='crc32'}for name,item in descriptions.items()}
            # Supplemental notices may be synthesized by the trusted producer, never overwrite a received file.
            for name,raw in extras.items():
                if name in files:need(files[name]==row(raw))
                else:files[name]=row(raw)
            build=bound_build(observation,files,source,source_commit,tree_oid,catalog,source_tree,ledger)
            for name,raw in catalog['outputs'].items():need(files.get(name)==row(raw))
            for name,origin in build['file_origins'].items():
                if origin['kind']in('copied-source','project-public'):
                    expected=source[origin['source_path']]
                    need(files[name]['bytes']==expected['bytes'])
                    raw=source_tree.read(origin['source_path'],MAX_MEMBER)
                    need(git_oid(raw)==expected['git_blob_oid']and sha(raw)==files[name]['sha256'])
            manifest={'profile':PROFILE,'build':build,'files':files,'claims':FALSE_CLAIMS.copy()}
            manifest_raw=encoded(manifest)+b'\n';need(len(manifest_raw)<=MAX_RECORD)
            rows={META:row(manifest_raw)|{'crc32':zlib.crc32(manifest_raw)}}
            virtual={META:manifest_raw,**{'payload/'+n:b for n,b in extras.items()}}
            for name in files:
                if 'payload/'+name in virtual:actual=row(virtual['payload/'+name])|{'crc32':zlib.crc32(virtual['payload/'+name])}
                else:actual=descriptions[name]
                need({k:v for k,v in actual.items()if k!='crc32'}==files[name]);rows['payload/'+name]=actual
            source_tree.check();dist.check();need(dist.inventory()==inventory)
            with PrivateStage(destination,ledger)as stage:
                with stage.new_file('checker.zip')as fd:
                    def chunks(name):
                        if name in virtual:return _byte_chunks(virtual[name])
                        path=name[len('payload/'):];return _chunks(dist,path,files[path]['bytes'])
                    size=canonical_archive(fd,rows,chunks,ledger)
                    inspect_archive(fd,ledger,expected_manifest=manifest_raw)
                    ledger.charge(size);digest=hashlib.sha256();at=0
                    while at<size:
                        raw=os.pread(fd,min(65536,size-at),at);need(raw);digest.update(raw);at+=len(raw);ledger.tick()
                stage.save('build-binding.json',encoded(build)+b'\n')
                source_tree.check();dist.check();need(dist.inventory()==inventory);stage.check()
            return _summary(ledger,artifact={'bytes':size,'sha256':digest.hexdigest()},source_commit=source_commit,
              source_tree_oid=tree_oid,files=len(files),build_record_verified=True,genuine_protected_build_verified=False,private_output_created=True)


def validate_received(fd,manifest,rows,source,catalog,source_tree,ledger):
    """Run only after actual shared AUTH, or explicit format-only inspection."""
    build=manifest['build'];exact_keys(build,('profile','source_commit','source_tree_oid','observation','file_origins','files','claims'))
    need(build['profile']==PROFILE and build['claims']==FALSE_CLAIMS
      and all(type(v)is bool and not v for v in build['claims'].values())and build['files']==manifest['files'])
    expected=bound_build(build['observation'],manifest['files'],source,build['source_commit'],build['source_tree_oid'],catalog,source_tree,ledger)
    need(encoded(build)==encoded(expected))
    extras=obligation_outputs(catalog,build['observation'])
    for name,raw in {**catalog['outputs'],**extras}.items():
        need(manifest['files'].get(name)==row(raw))
    # One payload pass checks every digest/CRC and any copied-source Git object simultaneously.
    for name,origin in build['file_origins'].items():
        actual=rows['payload/'+name];ledger.charge(actual['bytes']);at=crc=0;digest=hashlib.sha256();git=None
        if origin['kind']in('copied-source','project-public'):
            expected=source[origin['source_path']];need(actual['bytes']==expected['bytes'])
            git=hashlib.sha1(b'blob '+str(actual['bytes']).encode()+b'\0')
        while at<actual['bytes']:
            raw=os.pread(fd,min(65536,actual['bytes']-at),actual['offset']+at);need(raw)
            at+=len(raw);digest.update(raw);crc=zlib.crc32(raw,crc);ledger.tick()
            if git is not None:git.update(raw)
        need(digest.hexdigest()==manifest['files'][name]['sha256']and crc==actual['crc32'])
        if git is not None:need(git.hexdigest()==expected['git_blob_oid'])
    return build


@_boundary
def inspect(artifact,source_commit,root=ROOT):
    """Format/source check only: untrusted content is never materialized/executed."""
    ledger=Ledger()
    with operation(ledger):
        catalog=source_catalog(root,ledger);source,tree_oid=committed_source(root,source_commit,ledger)
        bind_catalog_source(root,source,catalog,ledger)
        artifact=Path(artifact).absolute()
        with FileTree(root,ledger)as current,FileTree(artifact.parent,ledger)as received:
            with received.file(artifact.name,MAX_ARTIFACT)as(fd,_):
                manifest,rows=inspect_archive(fd,ledger,hash_payload=False)
                need(manifest['build']['source_commit']==source_commit and manifest['build']['source_tree_oid']==tree_oid)
                validate_received(fd,manifest,rows,source,catalog,current,ledger)
            current.check();received.check()
        return _summary(ledger,source_commit=source_commit,files=len(manifest['files']),format_and_source_verified=True)


def _fixed_authorize(record,artifact,sbom,bundle,roots,source_commit,root,ledger):
    # All public entrypoints validate these pins afresh; no caller verifier/runner exists.
    with FileTree(root,ledger)as pinned:
        raw={name:pinned.read(name,MAX_RECORD,expected=SOURCE_PINS[name])for name in
          ('tools/artifact_evidence_io.py','tools/artifact_process.py','tools/dependency_policy.py','tools/distribution_artifacts.py')}
        pinned.check()
    io=_private_module(raw['tools/artifact_evidence_io.py'],'_web_auth_io',Path(root)/'tools/artifact_evidence_io.py')
    worker=_private_module(raw['tools/artifact_process.py'],'_web_auth_worker',Path(root)/'tools/artifact_process.py')
    policy=_private_module(raw['tools/dependency_policy.py'],'_web_auth_policy',Path(root)/'tools/dependency_policy.py')
    common=_private_module(raw['tools/distribution_artifacts.py'],'_web_auth_common',Path(root)/'tools/distribution_artifacts.py',
      {'tools.artifact_evidence_io':io,'tools.artifact_process':worker,'tools.dependency_policy':policy})
    need(time.monotonic()+65<=ledger.deadline and ledger.fds+80<=MAX_FDS)
    def bounded_runner(argv,timeout=60,output_limit=16_000_000):
        return _run_real_verifier(common,argv,ledger,timeout,output_limit)
    return common.authorize_release(record,artifact,sbom,bundle,roots,FIXED_AUTH_ROUTE,source_commit,
      root=Path(root),runner=bounded_runner)


def _materialize(stage,fd,manifest,rows,ledger):
    """Authenticated static data only. No server, subprocess, browser or JS launch."""
    os.mkdir('site',0o700,dir_fd=stage.tree.fd)
    with FileTree(stage.path/'site',ledger,private=True)as output:
        for name in sorted(manifest['files']):
            parts=path_name(name).split('/');owned=[];parent=output.fd
            try:
                for part in parts[:-1]:
                    try:os.mkdir(part,0o700,dir_fd=parent)
                    except FileExistsError:pass
                    parent=output._open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=parent,owned=owned)
                    output._private(parent,True)
                target=output._open(parts[-1],os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=parent,owned=owned)
                actual=rows['payload/'+name];ledger.charge(actual['bytes']);at=0;h=hashlib.sha256()
                while at<actual['bytes']:
                    raw=os.pread(fd,min(65536,actual['bytes']-at),actual['offset']+at);need(raw)
                    at+=len(raw);h.update(raw);_write_all(target,raw,ledger)
                need(h.hexdigest()==manifest['files'][name]['sha256']);os.fsync(target)
            finally:
                failure=None
                while owned:
                    try:ledger.close(owned.pop())
                    except BaseException as error:
                        if failure is None:failure=error
                if failure is not None:raise WebOutputUncertain()from None
        need(set(output.inventory())==set(manifest['files']))
        for name,expected in manifest['files'].items():
            actual=output.describe(name);need({k:v for k,v in actual.items()if k!='crc32'}==expected)
        output.check();need(set(output.inventory())==set(manifest['files']))


@_boundary
def verify_managed(artifact,packet,spdx,bundle,trusted_roots,destination,source_commit,root=ROOT):
    """Genuine current policy + protected signature before first member interpretation."""
    ledger=Ledger(managed=True)
    with operation(ledger):
        # Complete independent fixed obligations are reconstructed before auth; no received member is read yet.
        catalog=source_catalog(root,ledger)
        source,tree_oid=committed_source(root,source_commit,ledger)
        bind_catalog_source(root,source,catalog,ledger)
        inputs={'artifact.bin':(Path(artifact),MAX_ARTIFACT),'packet.json':(Path(packet),MAX_RECORD),
          'sbom.json':(Path(spdx),MAX_RECORD),'bundle.json':(Path(bundle),MAX_PACKET),'roots.jsonl':(Path(trusted_roots),MAX_ROOTS)}
        with contextlib.ExitStack()as stack:
            received={};paths={}
            for name,(path,limit)in inputs.items():
                path=path.absolute()
                if path.parent not in received:received[path.parent]=stack.enter_context(FileTree(path.parent,ledger))
                tree=received[path.parent];paths[name]=(tree,path.name,limit)
            with FileTree(root,ledger)as current:
                for name,expected in SOURCE_PINS.items():current.read(name,MAX_RECORD,expected=expected)
                target=Path(destination).absolute()
                # Exact held-chain capacity before creation or opaque evidence copying.
                need(ledger.fds+len(target.parent.parts)+len(target.parts)+80<=MAX_FDS)
                with PrivateStage(destination,ledger)as stage:
                    captured={}
                    for name,(tree,path,limit)in paths.items():
                        with stage.new_file(name)as fd:
                            with tree.file(path,limit)as(source_fd,info):
                                h=hashlib.sha256();at=0
                                while at<info.st_size:
                                    raw=os.read(source_fd,min(65536,info.st_size-at));need(raw);at+=len(raw);h.update(raw);_write_all(fd,raw,ledger)
                                captured[name]={'bytes':at,'sha256':h.hexdigest()}
                        # Snapshot sealed quarantine identities without another body pass. No wrapper writes follow.
                        with stage.tree.file(name,limit,expected_size=at,charge=False):pass
                    record_raw=stage.tree.read('packet.json',MAX_RECORD);record=parse(record_raw,ledger)
                    sbom_raw=stage.tree.read('sbom.json',MAX_RECORD);parse(sbom_raw,ledger)
                    need(type(record)is dict and record.get('source_commit')==source_commit and record.get('route')==FIXED_AUTH_ROUTE)
                    need(record.get('artifact')==captured['artifact.bin'])
                    ledger.reserve_auth(captured['artifact.bin']['bytes'])
                    stage.check();current.check()
                    for tree,_,_ in paths.values():tree.check()
                    result=_fixed_authorize(record,stage.path/'artifact.bin',stage.path/'sbom.json',stage.path/'bundle.json',
                      stage.path/'roots.jsonl',source_commit,root,ledger)
                    need(result.get('state')=='AUTHORIZED'and result.get('release_authorized')is True and result.get('attestation_verified')is True)
                    # Actual AUTH is necessary but not sufficient: exact new build binding must be in its authenticated Graph.
                    nodes=record.get('graph',{}).get('nodes');need(type(nodes)is list)
                    bound=[node for node in nodes if node.get('key')=='web:build-observation']
                    need(len(bound)==1 and type(bound[0].get('details'))is dict and set(bound[0]['details'])=={'build'})
                    stage.check();current.check()
                    for tree,_,_ in paths.values():tree.check()
                    with stage.tree.file('artifact.bin',captured['artifact.bin']['bytes'],expected_size=captured['artifact.bin']['bytes'],charge=False)as(fd,_):
                        manifest,rows=inspect_archive(fd,ledger,hash_payload=False)
                        need(manifest['build']['source_commit']==source_commit and manifest['build']['source_tree_oid']==tree_oid
                          and encoded(manifest['build'])==encoded(bound[0]['details']['build']))
                        validate_received(fd,manifest,rows,source,catalog,current,ledger)
                        stage.check();current.check();_materialize(stage,fd,manifest,rows,ledger)
                    for tree,_,_ in paths.values():tree.check()
                    current.check();stage.check()
                return _summary(ledger,state='MATERIALIZED',attestation_verified=True,release_authorized=True,
                  source_commit=source_commit,artifact=captured['artifact.bin'],files=len(manifest['files']),
                  execution_started=False)


@contextlib.contextmanager
def operation(ledger):
    try:
        with original_deadline(ledger):yield
    except BaseException:
        if ledger.output_attempted:raise WebOutputUncertain()from None
        raise


def bind_catalog_source(root,source,catalog,ledger):
    inputs={**catalog['selected_inputs'],**catalog['runtime_inputs']}
    # The complete current producer/helper/source identities must exist in the selected Git tree.
    for name in ('tools/web_checker_artifact.py','scripts/web-checker-artifact.py',
      'tools/web_runtime_obligations.py','sbom/web-runtime/manifest.json',*BUILD_INPUTS):
        need(name in source)
        if name not in inputs:inputs[name]={'bytes':source[name]['bytes']}
    with FileTree(root,ledger)as tree:
        for name,expected in inputs.items():
            need(name in source and source[name]['bytes']==expected['bytes'])
            raw=tree.read(name,MAX_RECORD)
            need(len(raw)==expected['bytes']and git_oid(raw)==source[name]['git_blob_oid'])
            if 'sha256'in expected:need(sha(raw)==expected['sha256'])
        tree.check()


def _run_real_verifier(common,argv,ledger,timeout,output_limit):
    need(timeout==60 and output_limit==16_000_000 and not ledger.verifier_invoked)
    ledger.tick();begin=time.monotonic()
    need(begin>=ledger.started and begin+65<=ledger.deadline)
    ledger.verifier_invoked=True
    try:result=common.run_attestation(argv,timeout=60,output_limit=16_000_000)
    finally:
        end=time.monotonic();need(begin<=end and end-begin<=65)
        ledger.crypto_seconds=end-begin
    ledger.tick()
    if result.returncode==0:preflight_json(result.stdout,ledger,16_000_000)
    return result
