"""Exact policy-approved PS source ZIPs; no interpreter or inspected text."""
import hashlib
import io
import json
import os
from pathlib import Path
import re
import secrets
import stat
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PROFILE = 'ai-trust-id-ps-source/v1'
MANIFEST = '.aitrust-ps-source.json'
FILES = frozenset({
    'scripts/check-ps.py', 'scripts/worker_process.py',
    'scripts/build-device-detector.py', 'services/evaluator/app.py',
    'protocol/normalization.py', 'protocol/unicode15-data.json',
    'LICENSE', 'eval/vectors/unicode/LICENSE.txt', 'docs/ps-source-distribution.md',
})
MAX_MEMBER = 2_000_000
MAX_TOTAL = 4_000_000
MAX_ARCHIVE = 4_100_000
STAMP = (1980, 1, 1, 0, 0, 0)
MODE = (stat.S_IFREG | 0o644) << 16


def require(ok):
    if not ok:
        raise ValueError('PS source distribution refused')


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True,
                      allow_nan=False, separators=(',', ':')).encode() + b'\n'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def directory(path):
    """Walk absolute directories without following a supplied path component."""
    path = Path(path).absolute()
    descriptor = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in path.parts[1:]:
            require(part not in ('.', '..'))
            following = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                                dir_fd=descriptor)
            os.close(descriptor)
            descriptor = following
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def read_member(root_fd, name, limit=MAX_MEMBER):
    parts = name.split('/')
    require(all(part not in ('', '.', '..') for part in parts))
    parent = os.dup(root_fd)
    try:
        for part in parts[:-1]:
            following = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            os.close(parent)
            parent = following
        descriptor = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        with os.fdopen(descriptor, 'rb') as stream:
            before = os.fstat(stream.fileno())
            require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and before.st_size <= limit)
            raw = stream.read(limit + 1)
            after = os.fstat(stream.fileno())
            require(len(raw) <= limit and len(raw) == before.st_size and
                    (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) ==
                    (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns))
            return raw
    finally:
        os.close(parent)


def policy(root, route_check=None):
    if route_check is None:
        from tools.dependency_policy import require_route
        route_check = require_route
    value = route_check('ps-source', root=root)
    require(type(value) is dict and set(value) ==
            {'profile', 'route', 'files', 'prerequisites', 'policy_sha256'})
    require(type(value['profile']) is str and 0 < len(value['profile']) <= 100 and
            value['route'] == 'ps-source' and type(value['policy_sha256']) is str and
            re.fullmatch('[a-f0-9]{64}', value['policy_sha256']))
    require(type(value['files']) is list and len(value['files']) == len(FILES))
    seen = set()
    for entry in value['files']:
        require(type(entry) is dict and set(entry) == {'path', 'sha256', 'bytes'})
        require(type(entry['path']) is str and entry['path'] in FILES and entry['path'] not in seen)
        seen.add(entry['path'])
        require(type(entry['bytes']) is int and 0 < entry['bytes'] <= MAX_MEMBER and
                type(entry['sha256']) is str and re.fullmatch('[a-f0-9]{64}', entry['sha256']))
    require(seen == FILES and sum(entry['bytes'] for entry in value['files']) <= MAX_TOTAL)
    require(type(value['prerequisites']) is list and 0 < len(value['prerequisites']) <= 16)
    # Snapshot mutable policy results before subsequent validation or I/O.
    raw = canonical(value)
    require(len(raw) <= 64_000)
    value = json.loads(raw)
    value['files'].sort(key=lambda entry: entry['path'])
    return value


def manifest(value):
    return {'profile': PROFILE, 'route': 'ps-source', 'policy_profile': value['profile'],
            'policy_sha256': value['policy_sha256'], 'files': value['files'],
            'prerequisites': value['prerequisites'], 'source_only': True,
            'interpreter_bundled': False, 'independent_accuracy_evidence': False}


def capture(root, route_check):
    root = Path(root).absolute()
    value = policy(root, route_check)
    descriptor = directory(root)
    try:
        members = {entry['path']: read_member(descriptor, entry['path']) for entry in value['files']}
        for entry in value['files']:
            require(len(members[entry['path']]) == entry['bytes'] and
                    digest(members[entry['path']]) == entry['sha256'])
        require(policy(root, route_check) == value)
        require(all(read_member(descriptor, name) == raw for name, raw in members.items()))
        # A replaced root must not leave us reading an unrelated old directory.
        current = directory(root)
        try:
            require((os.fstat(current).st_dev, os.fstat(current).st_ino) ==
                    (os.fstat(descriptor).st_dev, os.fstat(descriptor).st_ino))
        finally:
            os.close(current)
        return value, members
    finally:
        os.close(descriptor)


def inspect(raw, expected):
    require(type(raw) is bytes and 0 < len(raw) <= MAX_ARCHIVE)
    expected_manifest = canonical(manifest(expected))
    entries = {entry['path']: entry for entry in expected['files']}
    entries[MANIFEST] = {'bytes': len(expected_manifest), 'sha256': digest(expected_manifest)}
    verified = {}
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            infos = archive.infolist()
            require(not archive.comment and len(infos) == len(entries) and
                    [item.filename for item in infos] == sorted(entries))
            for item in infos:
                require(item.filename in entries and not item.is_dir() and item.date_time == STAMP and
                        item.create_system == 3 and item.external_attr == MODE and
                        not item.extra and not item.comment and item.flag_bits == 0 and
                        item.compress_type == zipfile.ZIP_STORED and item.compress_size == item.file_size)
                entry = entries[item.filename]
                require(item.file_size == entry['bytes'] and item.file_size <= MAX_MEMBER)
                with archive.open(item) as stream:
                    member = stream.read(item.file_size + 1)
                require(len(member) == entry['bytes'] and digest(member) == entry['sha256'])
                verified[item.filename] = member
                if item.filename == MANIFEST:
                    require(member == expected_manifest)
    except (zipfile.BadZipFile, NotImplementedError, RuntimeError, EOFError) as error:
        raise ValueError('PS source distribution refused') from error
    # Reject trailing/prefix bytes, hidden members and alternate encodings: the
    # accepted file is exactly the deterministic format this builder emits.
    require(raw == assemble(verified))
    return manifest(expected)


def assemble(members):
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_STORED, allowZip64=False) as archive:
        for name, raw in sorted(members.items()):
            item = zipfile.ZipInfo(name, STAMP)
            item.create_system = 3
            item.external_attr = MODE
            item.compress_type = zipfile.ZIP_STORED
            archive.writestr(item, raw)
    return output.getvalue()


def build(root=ROOT, *, route_check=None):
    value, members = capture(root, route_check)
    members[MANIFEST] = canonical(manifest(value))
    raw = assemble(members)
    inspect(raw, value)
    return raw


def verify(raw, root=ROOT, *, route_check=None):
    value, _ = capture(root, route_check)
    return inspect(raw, value)


def verify_file(path, root=ROOT, *, route_check=None):
    path = Path(path).absolute()
    parent = directory(path.parent)
    try:
        raw = read_member(parent, path.name, MAX_ARCHIVE)
    finally:
        os.close(parent)
    result = verify(raw, root, route_check=route_check)
    return {'profile': PROFILE, 'pass': True, 'sha256': digest(raw), 'bytes': len(raw),
            'member_count': len(result['files']) + 1, 'policy_sha256': result['policy_sha256']}


def export(path, root=ROOT, *, route_check=None):
    path = Path(path).absolute()
    require(re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]*[.]zip', path.name) is not None)
    parent = directory(path.parent)
    temporary = None
    temporary_identity = None
    try:
        try:
            os.stat(path.name, dir_fd=parent, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise ValueError('PS source distribution refused')
        raw = build(root, route_check=route_check)
        candidate = '.ps-source-' + secrets.token_hex(16)
        descriptor = os.open(candidate, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
        temporary = candidate
        info = os.fstat(descriptor)
        temporary_identity = (info.st_dev, info.st_ino)
        with os.fdopen(descriptor, 'w+b') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
            stream.seek(0)
            require(stream.read(MAX_ARCHIVE + 1) == raw)
        result = verify(raw, root, route_check=route_check)
        require(read_member(parent, temporary, MAX_ARCHIVE) == raw)
        info = os.stat(temporary, dir_fd=parent, follow_symlinks=False)
        require((info.st_dev, info.st_ino) == temporary_identity)
        current = directory(path.parent)
        try:
            require((os.fstat(current).st_dev, os.fstat(current).st_ino) ==
                    (os.fstat(parent).st_dev, os.fstat(parent).st_ino))
        finally:
            os.close(current)
        os.link(temporary, path.name, src_dir_fd=parent, dst_dir_fd=parent, follow_symlinks=False)
        return {'profile': PROFILE, 'pass': True, 'sha256': digest(raw), 'bytes': len(raw),
                'member_count': len(result['files']) + 1, 'policy_sha256': result['policy_sha256']}
    finally:
        try:
            if temporary is not None:
                try:
                    info = os.stat(temporary, dir_fd=parent, follow_symlinks=False)
                except FileNotFoundError:
                    pass
                else:
                    if (info.st_dev, info.st_ino) == temporary_identity:
                        os.unlink(temporary, dir_fd=parent)
        finally:
            os.close(parent)
