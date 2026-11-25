"""Finite source-copy admission, separate from runtime or tag approval.

The installed trusted checkout supplies the classifier and the selected policy.
Neither a received archive nor an evidence packet can select permissions.
"""
from pathlib import Path
from contextlib import contextmanager
import hashlib
import os
import signal
import stat
import types
import sys

from tools.artifact_evidence_io import Capture, need, sha

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = 'source-snapshot-unreviewed'  # Retained registry ID, not the status.
EXPRESSION = 'LicenseRef-Source-Snapshot-Finite-Copy-Grants'
NOTICES = ['LICENSE', 'NOTICE', 'spec/LICENSE', 'eval/vectors/unicode/LICENSE.txt']
PREREQUISITES = [
    'Independently obtained CPython 3.12 or newer and a supported POSIX OS; no interpreter or OS is bundled.',
    'Only exact committed source copying with the finite reviewed grants and carried notices is admitted; runtime, SDK, model and compiled redistribution rights remain separate.',
    'Managed use requires the caller-selected trusted Git commit, protected-main artifact attestation, separately trusted roots and successful finite source-entry-point probes.',
]
SCOPE = ('Canonical whole-repository source snapshot with finite per-component copy grants, '
         'trusted-Git byte binding and retained notices; no bundled runtime, platform or model '
         'permission, whole-project legal clearance or independent tag accuracy.')
COMPONENT_FILES = frozenset({
    *NOTICES, 'eval/dependencies/source-snapshot-release.json',
    'eval/dependencies/source-snapshot-release-v2.json',
    'eval/dependencies/source-snapshot-additions-v3.json',
    'tools/source_release_policy.py', 'tools/source_release_policy_v2.py',
    'tools/source_release_policy_v3.py', 'tools/source_release_policy_v4.py',
    'eval/dependencies/source-snapshot-additions-v4.json',
    'tools/source_release_policy_v5.py','eval/dependencies/source-snapshot-additions-v5.json',
    'tools/source_release_policy_v6.py','eval/dependencies/source-snapshot-additions-v6.json',
    'tools/source_snapshot_binding.py', 'tools/source_snapshot_admission.py',
    'scripts/source_snapshot.py', 'scripts/source_snapshot_v2.py',
    'scripts/source_snapshot_v3.py', 'scripts/build-source-snapshot.py',
    'scripts/worker_process.py', 'tools/artifact_evidence_io.py',
    'tools/source_snapshot_managed.py', 'scripts/verify-managed-source.py',
    'docs/source-snapshot-managed-consumer.md',
})


@contextmanager
def _phase_critical():
    old=signal.pthread_sigmask(signal.SIG_BLOCK,{signal.SIGALRM,signal.SIGINT})
    try:yield
    finally:signal.pthread_sigmask(signal.SIG_SETMASK,old)


def _file_identity(info):
    return(info.st_dev,info.st_ino,info.st_mode,info.st_nlink,info.st_size,info.st_mtime_ns,info.st_ctime_ns)


def _source_room(extra=1):
    need(type(extra)is int and 0<=extra<=80);count=0
    with os.scandir('/dev/fd'if sys.platform=='darwin'else'/proc/self/fd')as entries:
        for unused in entries:count+=1;need(count+extra<=80)
    return count


def _source_spawn_room():
    n=_source_room(0);need(max(2*n+16,n+32)<=80);return n


class _SourceReadset:
    """Private source-only snapshots; callers supply fixed code-derived sets, never packet authority.

    Keeps only owned directory anchors. Every released file and full named chain
    must be reopened and checked before the caller returns permission/evidence.
    """
    def __init__(self, expected, *, anchors, budget=0, artifact_paths=()):
        need(type(expected)is dict and 0<len(expected)<=256 and type(budget)is int and 0<=budget<=64_000_000)
        self.expected={Path(n).absolute():h for n,h in expected.items()};need(len(self.expected)==len(expected))
        need(all(type(h)is str and len(h)==64 and all(c in '0123456789abcdef'for c in h)for h in self.expected.values()))
        self.artifacts={Path(n).absolute()for n in artifact_paths};need(len(self.artifacts)<=1 and self.artifacts<=self.expected.keys())
        self.archive_total=0;self.dirs={};self.files={};self.private={};self.anchors=[];self.total=budget;self.closed=False
        try:
            for path in dict.fromkeys(Path(n).absolute()for n in anchors):
                with self._walk(path,directory=True,initial=True)as(fd,unused):
                    _source_room()
                    with _phase_critical():
                        owned=os.dup(fd)
                        try:self.anchors.append((path,owned,None))
                        except BaseException:os.close(owned);raise
                        info=os.fstat(owned);self.anchors[-1]=(path,owned,(info.st_dev,info.st_ino,info.st_mode))
        except BaseException:self.close();raise

    @contextmanager
    def _walk(self,path,*,directory=False,initial=False):
        path=Path(path).absolute();need('..'not in path.parts and '.'not in path.parts)
        owned=[]
        try:
            _source_room()
            with _phase_critical():fd=os.open(path.anchor,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_NONBLOCK);owned.append(fd)
            self._directory(Path(path.anchor),fd,initial)
            parts=path.parts[1:]if directory else path.parts[1:-1];prefix=Path(path.anchor)
            for part in parts:
                prefix=prefix/part
                _source_room()
                with _phase_critical():
                    child=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=fd);owned.append(child)
                    old=owned.pop(0);os.close(old)
                fd=child;self._directory(prefix,fd,initial)
            yield fd,path.name
        finally:
            errors=[]
            with _phase_critical():
                while owned:
                    try:os.close(owned.pop())
                    except BaseException as error:errors.append(error)
            if errors:raise errors[0]

    def _directory(self,path,fd,initial):
        info=os.fstat(fd);need(stat.S_ISDIR(info.st_mode));identity=(info.st_dev,info.st_ino,info.st_mode)
        if initial:
            need(path not in self.dirs or self.dirs[path]==identity);self.dirs[path]=identity
        else:need(path in self.dirs and self.dirs[path]==identity)
        if path in self.private:
            try:os.stat('.git',dir_fd=fd,follow_symlinks=False)
            except FileNotFoundError:pass
            else:need(False)
            if self.private[path]:need(info.st_uid==os.getuid()and stat.S_IMODE(info.st_mode)==0o700)

    def read(self,path,*,initial=False,retain=False):
        need(not self.closed);path=Path(path).absolute();need(path in self.expected)
        raw=bytearray()if retain else None
        with self._walk(path,initial=initial)as(parent,name):
            fd=None
            try:
                _source_room()
                with _phase_critical():fd=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=parent)
                before=os.fstat(fd);limit=64_000_000 if path in self.artifacts else 16_000_000
                need(stat.S_ISREG(before.st_mode)and before.st_nlink==1 and 0<before.st_size<=limit)
                identity=_file_identity(before)
                if not initial:need(path in self.files and identity==self.files[path])
                if path in self.artifacts:
                    need(not retain and self.archive_total+before.st_size<=128_000_000);self.archive_total+=before.st_size
                else:need(self.total+before.st_size<=64_000_000);self.total+=before.st_size
                digest=hashlib.sha256();at=0
                while at<before.st_size:
                    block=os.read(fd,min(65536,before.st_size-at));need(block);digest.update(block);at+=len(block)
                    if raw is not None:raw.extend(block)
                need(not os.read(fd,1)and digest.hexdigest()==self.expected[path]
                  and identity==_file_identity(os.fstat(fd))==_file_identity(os.stat(name,dir_fd=parent,follow_symlinks=False)))
                if initial:self.files[path]=identity
                return bytes(raw)if raw is not None else None
            finally:
                if fd is not None:
                    with _phase_critical():owned,fd=fd,None;os.close(owned)

    def absorb(self,capture,expected,*,artifact_paths=()):
        """Private incremental source phase; references may never be replaced."""
        need(not self.closed and type(expected)is dict and expected and capture.total_read>=self.total)
        expected={Path(n).absolute():h for n,h in expected.items()}
        need(len(self.expected.keys()|expected.keys())<=256 and all(type(h)is str and len(h)==64 and all(c in '0123456789abcdef'for c in h)for h in expected.values()))
        artifacts={Path(n).absolute()for n in artifact_paths};need(artifacts<=expected.keys()and len(self.artifacts|artifacts)<=1)
        capture.check();byfd={value[0]:Path(*parts)for parts,value in capture.directory_cache.items()};files={}
        for parent,name,fd,identity in capture.files:
            need(parent in byfd);path=byfd[parent]/name;need(path in expected and(path not in files or files[path]==identity));files[path]=identity
        need(files.keys()==expected.keys())
        for path,h in expected.items():need(path not in self.expected or(self.expected[path]==h and(path not in self.files or self.files[path]==files[path])))
        for parts,(fd,identity)in capture.directory_cache.items():
            path=Path(*parts);need(path not in self.dirs or self.dirs[path]==identity)
            if fd in capture.private_directories:
                need(path not in self.private or self.private[path]==capture.private_directories[fd]);self.private[path]=capture.private_directories[fd]
            self.dirs[path]=identity
        for path in artifacts:
            if path not in self.files:self.archive_total+=files[path][4]
        need(self.archive_total<=128_000_000 and capture.total_read<=64_000_000)
        self.expected.update(expected);self.files.update(files);self.artifacts|=artifacts;self.total=capture.total_read;capture.check()

    @classmethod
    def from_capture(cls,capture,expected,*,anchors,artifact_paths=()):
        capture.check();result=cls(expected,anchors=anchors,budget=capture.total_read,artifact_paths=artifact_paths)
        try:result.absorb(capture,expected,artifact_paths=artifact_paths);return result
        except BaseException:result.close();raise

    def check(self):
        need(not self.closed and self.files.keys()==self.expected.keys())
        for path,fd,identity in self.anchors:
            need((os.fstat(fd).st_dev,os.fstat(fd).st_ino,os.fstat(fd).st_mode)==identity)
        for path in self.expected:self.read(path)
        # Check even empty/extra recorded chain components and named anchors.
        for path in self.dirs:
            with self._walk(path,directory=True)as(fd,unused):self._directory(path,fd,False)

    def close(self):
        if self.closed:return
        self.closed=True;errors=[]
        with _phase_critical():
            while self.anchors:
                path,fd,identity=self.anchors.pop()
                try:os.close(fd)
                except BaseException as error:errors.append(error)
        if errors:raise errors[0]

    def __enter__(self):return self
    def __exit__(self,*unused):self.close()


def _rows(root):
    from tools.dependency_policy import load
    value,unused=load(root);return value['components'][COMPONENT]['files']


@contextmanager
def _captured_copy(root):
    need(Path(root).resolve()==ROOT)
    rows=_rows(root);need(type(rows)is list and len(rows)==len(COMPONENT_FILES)and {r['path']for r in rows}==COMPONENT_FILES)
    expected={ROOT/r['path']:r['sha256']for r in rows};sizes={ROOT/r['path']:r['bytes']for r in rows}
    with _SourceReadset(expected,anchors=(ROOT,))as source:
        raw={}
        for path in expected:
            value=source.read(path,initial=True,retain=path.name in('source_release_policy_v6.py','source-snapshot-additions-v6.json'))
            need(type(sizes[path])is int and source.files[path][4]==sizes[path])
            if value is not None:raw[path.name]=value
        namespace=types.ModuleType('_captured_active_source_copy_v6');namespace.__file__=str(ROOT/'tools/source_release_policy_v6.py')
        exec(compile(raw['source_release_policy_v6.py'],'<captured-active-source-copy-v6>','exec'),namespace.__dict__)
        method=sha(raw['source_release_policy_v6.py']);table=sha(raw['source-snapshot-additions-v6.json'])
        need(namespace.ROOT==ROOT and namespace.POLICY=='eval/dependencies/source-snapshot-additions-v6.json'and namespace.POLICY_SHA256==table)
        yield namespace,method,table
        source.check();need(_rows(root)==rows)


def _checked_result(result,copy,method,table,source_commit,archive=False):
    need(type(result)is dict and result.get('pass')is True and result.get('source_copy_profile_satisfied')is True
      and result.get('method_sha256')==method and result.get('policy_sha256')==table
      and type(result.get('source_commit'))is str and copy.OID.fullmatch(result['source_commit'])
      and all(result.get(key)is False for key in copy.FALSE_CLAIMS))
    if source_commit is not None:need(result['source_commit']==source_commit)
    if archive:
        need(result.get('profile')=='source-copy-archive-obligations/v6'and result.get('status')=='COPY_OBLIGATIONS_AND_GIT_BYTES_BOUND'
          and result.get('trusted_git_bytes_matched')is True and result.get('signature_verified')is False)
    else:need(result.get('profile')==copy.PROFILE and result.get('status')=='SOURCE_COPY_PROFILE_SATISFIED')
    count=result.get('source_files'if archive else'files');size=result.get('source_bytes')
    need(type(count)is int and 0<count<=copy.MAX_FILES and type(size)is int and 0<=size<=copy.MAX_TOTAL)
    return result


def review(root=ROOT,source_commit=None):
    """Execute fresh captured trusted V5, never a cached module or status."""
    with _captured_copy(root)as(copy,method,table):
        return _checked_result(copy.verify(root=root,source_commit=source_commit),copy,method,table,source_commit)


def review_archive(raw,*,source_commit,root=ROOT):
    with _captured_copy(root)as(copy,method,table):
        need(type(raw)is bytes and 0<len(raw)<=copy.MAX_ARCHIVE)
        result=_checked_result(copy.verify_archive(raw,source_commit=source_commit),copy,method,table,source_commit,archive=True)
        need(result.get('archive_sha256')==sha(raw)and type(result.get('archive_bytes'))is int and result['archive_bytes']==len(raw))
        return result

def component_status(component, selected, root=ROOT):
    """A reviewed copy-only component cannot approve any sibling route."""
    if component['required_processing_payment'] is True:
        return 'paid', 'required_processing_payment'
    if component['source_available'] is False:
        return 'prohibited', 'required_processor_declared_closed'
    try:
        need(component['assessment'] == 'reviewed_source_distribution'
             and component['license_expression'] == EXPRESSION
             and component['source_available'] is True
             and component['required_processing_payment'] is False
             and component['notice_paths'] == NOTICES and component['review_scope'] == SCOPE)
        need(selected == {'kind': 'whole-repository',
            'dependencies': [{'component': COMPONENT, 'required': True}],
            'prerequisites': PREREQUISITES,
            'entrypoints': ['scripts/build-source-snapshot.py'], 'release_scope': SCOPE})
        need(type(selected['dependencies'][0]['required']) is bool)
        rows = component['files']
        need(type(rows) is list and len(rows) == len(COMPONENT_FILES)
             and {row['path'] for row in rows} == COMPONENT_FILES)
        # review owns a sequential exact row capture and fresh V5 execution.
        need(_rows(root)==rows)
        review(root)
        need(_rows(root)==rows)
        return 'allowed', 'finite_current_source_copy_grants_only'
    except (OSError, ValueError, TypeError, KeyError, ImportError, RuntimeError,
            OverflowError, RecursionError, UnicodeError):
        return 'blocked_unknown', 'source_copy_facts_or_consumer_changed'
