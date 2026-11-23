"""Bind received source snapshots to caller-trusted Git objects, without extraction.

SPDX-License-Identifier: Apache-2.0
"""
import hashlib
import builtins
import json
import os
from pathlib import Path
import re
import selectors
import signal
import subprocess
import sys
import time
import types

ROOT = Path(__file__).resolve().parents[1]
PROFILE = 'source-snapshot-trusted-git-binding/v1'
FOUNDATION = {
    'scripts/source_snapshot.py': '24df10061afea39710fb65799d54d386c177caed80629a4f15bc5384fc2c17ee',
    'scripts/source_snapshot_v2.py': 'baa1ce4b9b0066ad4161d472d5d3df190f6e7bc5817b29c58ce35686f130fb46',
    'scripts/source_snapshot_v3.py': '473384baa48cedcdff91dbc03598ee0ce77a0118dc97fb0cf815499630bab4a8',
}
MAX_ARCHIVE = 64_000_000
MAX_METADATA = 5_000_000
MAX_FILES = 16_384
MAX_FILE = 32_000_000
MAX_TOTAL = 256_000_000
MAX_LISTING = 2_000_000
DEADLINE_SECONDS = 60
CLEANUP_SECONDS = 5
OID = re.compile(r'[0-9a-f]{40}')
CODES = frozenset({'invalid_request', 'foundation_changed', 'archive_refused',
                   'git_unavailable', 'git_identity', 'tree_refused', 'inventory_mismatch',
                   'blob_mismatch', 'resource_limit', 'deadline', 'unavailable'})
ENV = {'PATH': '/usr/bin:/bin', 'LC_ALL': 'C', 'GIT_CONFIG_NOSYSTEM': '1',
       'GIT_CONFIG_SYSTEM': '/dev/null', 'GIT_CONFIG_GLOBAL': '/dev/null',
       'GIT_NO_LAZY_FETCH': '1', 'GIT_TERMINAL_PROMPT': '0', 'GIT_OPTIONAL_LOCKS': '0'}


class Refused(ValueError):
    def __init__(self, code):
        self.code = code if code in CODES else 'unavailable'
        super().__init__('Source archive binding unavailable.')


def need(value, code):
    if not value:
        raise Refused(code)


def _remaining(deadline):
    value = deadline - time.monotonic()
    need(value > 0, 'deadline')
    return value


def _supervise(argv, payload, deadline, consume, *, new_session=False):
    """Stream bounded chunks; consume owns its own total cap. No stderr capture."""
    _remaining(deadline)
    selector = None
    complete = False
    child = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                             stderr=subprocess.DEVNULL, close_fds=True, bufsize=0,
                             start_new_session=new_session, env=ENV)
    try:
        selector = selectors.DefaultSelector()
        os.set_blocking(child.stdin.fileno(), False)
        os.set_blocking(child.stdout.fileno(), False)
        selector.register(child.stdout, selectors.EVENT_READ, 'output')
        offset = 0
        if payload:
            selector.register(child.stdin, selectors.EVENT_WRITE, 'input')
        else:
            child.stdin.close()
        eof = False
        while not eof:
            for key, _ in selector.select(min(.1, _remaining(deadline))):
                if key.data == 'input':
                    try:
                        offset += os.write(key.fileobj.fileno(), memoryview(payload)[offset:offset + 65536])
                    except BlockingIOError:
                        continue
                    except BrokenPipeError:
                        raise Refused('unavailable') from None
                    if offset == len(payload):
                        selector.unregister(key.fileobj)
                        key.fileobj.close()
                else:
                    try:
                        block = os.read(key.fileobj.fileno(), 65536)
                    except BlockingIOError:
                        continue
                    if not block:
                        selector.unregister(key.fileobj)
                        eof = True
                        break
                    consume(block)
            _remaining(deadline)
        code = child.wait(timeout=_remaining(deadline))
        complete = True
        need(code == 0, 'git_unavailable' if not new_session else 'unavailable')
    finally:
        try:
            if not complete and child.returncode is None:
                try:
                    if new_session:
                        os.killpg(child.pid, signal.SIGKILL)
                    else:
                        child.kill()
                except ProcessLookupError:
                    pass
                finally:
                    child.wait(timeout=CLEANUP_SECONDS)
        finally:
            try:
                if selector is not None:
                    selector.close()
            finally:
                try:
                    child.stdin.close()
                finally:
                    child.stdout.close()


def _capture(argv, payload, deadline, limit, *, new_session=False):
    result = bytearray()
    def consume(block):
        need(len(result) + len(block) <= limit, 'resource_limit')
        result.extend(block)
    _supervise(argv, payload, deadline, consume, new_session=new_session)
    return bytes(result)


def _git(root, *args):
    # Callers below use only literal verbs and independently validated object IDs.
    return ['/usr/bin/git', '--no-replace-objects', '-c', 'protocol.allow=never',
            '-c', 'core.useReplaceRefs=false', '-C', str(root), *args]


def _foundation():
    captured = {}
    for name, expected in FOUNDATION.items():
        path = ROOT / name
        need(not path.is_symlink(), 'foundation_changed')
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            data = os.read(fd, 100_001)
            need(len(data) <= 100_000 and hashlib.sha256(data).hexdigest() == expected,
                 'foundation_changed')
            captured[name] = data
        finally:
            os.close(fd)
    # Only SHA-pinned captured code executes; no package initializer or reread.
    legacy = types.ModuleType('_binding_pinned_snapshot_v1')
    exec(compile(captured['scripts/source_snapshot.py'], '<pinned-source-v1>', 'exec'), legacy.__dict__)
    current = types.ModuleType('_binding_pinned_snapshot_v3')
    normal_import = builtins.__import__
    def pinned_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == 'source_snapshot' and level == 0:
            return legacy
        return normal_import(name, globals, locals, fromlist, level)
    current.__dict__['__builtins__'] = dict(vars(builtins), __import__=pinned_import)
    exec(compile(captured['scripts/source_snapshot_v3.py'], '<pinned-source-v3>', 'exec'), current.__dict__)
    return current


def _object_hash(kind, raw):
    return hashlib.sha1(kind.encode() + b' ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


class _Blobs:
    """Incremental exact --batch protocol; retains no complete source blob."""
    def __init__(self, rows, deadline):
        self.rows = rows
        self.deadline = deadline
        self.index = 0
        self.phase = 'header'
        self.header = bytearray()
        self.remaining = 0
        self.total = 0

    def consume(self, block):
        self.total += len(block)
        need(self.total <= MAX_TOTAL + MAX_FILES * 100, 'resource_limit')
        view = memoryview(block)
        while view:
            _remaining(self.deadline)
            need(self.index < len(self.rows), 'blob_mismatch')
            row = self.rows[self.index]
            if self.phase == 'header':
                at = bytes(view).find(b'\n')
                if at < 0:
                    self.header.extend(view)
                    need(len(self.header) <= 100, 'blob_mismatch')
                    return
                self.header.extend(view[:at])
                need(bytes(self.header) == (row['oid'] + ' blob ' + str(row['bytes'])).encode(),
                     'blob_mismatch')
                self.header.clear()
                self.remaining = row['bytes']
                self.sha256 = hashlib.sha256()
                self.sha1 = hashlib.sha1(b'blob ' + str(self.remaining).encode() + b'\0')
                self.phase = 'data' if self.remaining else 'trailer'
                view = view[at + 1:]
            elif self.phase == 'data':
                count = min(self.remaining, len(view))
                data = view[:count]
                self.sha256.update(data)
                self.sha1.update(data)
                self.remaining -= count
                view = view[count:]
                if not self.remaining:
                    self.phase = 'trailer'
            else:
                need(view[0] == 10 and self.sha1.hexdigest() == row['oid']
                     and self.sha256.hexdigest() == row['sha256'], 'blob_mismatch')
                self.index += 1
                self.phase = 'header'
                view = view[1:]

    def finish(self):
        need(self.index == len(self.rows) and self.phase == 'header' and not self.header,
             'blob_mismatch')


def _verify_inner(raw, root, commit):
    deadline = time.monotonic() + DEADLINE_SECONDS
    snapshot = _foundation()
    try:
        observed = snapshot.inspect(raw, commit)
        # inspect has checked all framing, metadata types, canonical bytes and rows.
        reader = snapshot._Inflated(raw)
        header = reader.take(512)
        size = int(header[124:136].rstrip(b'\0 ').lstrip(b' ') or b'0', 8)
        need(0 < size <= MAX_METADATA, 'archive_refused')
        metadata_raw = bytearray()
        while len(metadata_raw) < size:
            _remaining(deadline)
            metadata_raw.extend(reader.take(min(65536, size - len(metadata_raw))))
        archive_rows = json.loads(metadata_raw)['files']
    except (ValueError, RecursionError, UnicodeError, KeyError):
        raise Refused('archive_refused') from None
    _remaining(deadline)
    commit_raw = _capture(_git(root, 'cat-file', 'commit', commit), b'', deadline, 1_000_000)
    need(_object_hash('commit', commit_raw) == commit, 'git_identity')
    first = commit_raw.split(b'\n', 1)[0]
    need(re.fullmatch(rb'tree [0-9a-f]{40}', first), 'git_identity')
    tree_oid = first[5:].decode('ascii')
    listing = _capture(_git(root, 'ls-tree', '-rzl', '--full-tree', commit), b'', deadline, MAX_LISTING)
    need(listing.endswith(b'\0'), 'tree_refused')
    records = listing[:-1].split(b'\0')
    need(0 < len(records) <= MAX_FILES, 'resource_limit')
    rows = []
    seen = set()
    total = 0
    for record in records:
        _remaining(deadline)
        try:
            head, name = record.split(b'\t', 1)
            mode, kind, oid, length = head.decode('ascii').split()
            name = snapshot.safe_name(name.decode('ascii'))
        except (ValueError, UnicodeError):
            raise Refused('tree_refused') from None
        need(mode in ('100644', '100755') and kind == 'blob' and OID.fullmatch(oid)
             and re.fullmatch(r'0|[1-9][0-9]*', length) and name not in seen, 'tree_refused')
        count = int(length)
        total += count
        need(count <= MAX_FILE and total <= MAX_TOTAL, 'resource_limit')
        seen.add(name)
        rows.append({'path': name, 'mode': int(mode[-3:], 8), 'bytes': count, 'oid': oid})
    rows.sort(key=lambda row: row['path'])
    need(len(rows) == len(archive_rows), 'inventory_mismatch')
    for git_row, archive_row in zip(rows, archive_rows):
        need(all(git_row[k] == archive_row[k] for k in ('path', 'mode', 'bytes')), 'inventory_mismatch')
        git_row['sha256'] = archive_row['sha256']
    parser = _Blobs(rows, deadline)
    requests = ''.join(row['oid'] + '\n' for row in rows).encode('ascii')
    _supervise(_git(root, 'cat-file', '--batch'), requests, deadline, parser.consume)
    parser.finish()
    _remaining(deadline)
    return {'profile': PROFILE, 'pass': True, 'source_commit': commit, 'source_tree': tree_oid,
            'source_files': len(rows), 'source_bytes': total, 'archive_sha256': observed['sha256'],
            'trusted_git_bytes_matched': True, 'signature_verified': False,
            'rights_approved': False, 'release_authorized': False}


def verify(raw, *, root, commit):
    """Caller owns trust in root/commit. Received bytes cannot select either."""
    try:
        need(type(raw) is bytes and 0 < len(raw) <= MAX_ARCHIVE
             and type(commit) is str and OID.fullmatch(commit), 'invalid_request')
        root = Path(root)
        need(root.is_absolute() and root == root.resolve(strict=True) and root.is_dir()
             and len(str(root)) <= 4096 and not any(ord(c) < 32 for c in str(root)), 'invalid_request')
        deadline = time.monotonic() + DEADLINE_SECONDS
        result = _capture([sys.executable, '-I', '-S', '-B', str(Path(__file__).resolve()),
                           '--binding-worker', str(root), commit], raw, deadline, 4096,
                          new_session=True)
        body = json.loads(result)
        need(type(body) is dict, 'unavailable')
        if body.get('pass') is False:
            raise Refused(body.get('code'))
        need(type(body) is dict and set(body) == {'profile', 'pass', 'source_commit', 'source_tree',
             'source_files', 'source_bytes', 'archive_sha256', 'trusted_git_bytes_matched',
             'signature_verified', 'rights_approved', 'release_authorized'}, 'unavailable')
        need(body['profile'] == PROFILE and body['pass'] is True and body['source_commit'] == commit
             and OID.fullmatch(body['source_tree']) and type(body['source_files']) is int
             and 0 < body['source_files'] <= MAX_FILES and type(body['source_bytes']) is int
             and 0 <= body['source_bytes'] <= MAX_TOTAL
             and body['archive_sha256'] == hashlib.sha256(raw).hexdigest()
             and body['trusted_git_bytes_matched'] is True
             and all(body[k] is False for k in ('signature_verified', 'rights_approved', 'release_authorized')),
             'unavailable')
        return body
    except Refused:
        raise
    except subprocess.TimeoutExpired:
        raise Refused('deadline') from None
    except (OSError, ValueError, TypeError, KeyError, RecursionError):
        raise Refused('unavailable') from None


def _main():
    result = {'pass': False, 'code': 'invalid_request'}
    try:
        need(len(sys.argv) == 4 and sys.argv[1] == '--binding-worker'
             and OID.fullmatch(sys.argv[3]), 'invalid_request')
        raw = sys.stdin.buffer.read(MAX_ARCHIVE + 1)
        need(0 < len(raw) <= MAX_ARCHIVE, 'resource_limit')
        result = _verify_inner(raw, Path(sys.argv[2]), sys.argv[3])
    except Refused as error:
        result = {'pass': False, 'code': error.code}
    except subprocess.TimeoutExpired:
        result = {'pass': False, 'code': 'deadline'}
    except Exception:
        result = {'pass': False, 'code': 'unavailable'}
    print(json.dumps(result, sort_keys=True, separators=(',', ':')))


if __name__ == '__main__':
    _main()
