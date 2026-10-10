"""Deterministic committed-source archives; never extract or execute received files."""
import gzip
import hashlib
import io
import json
import re
import subprocess
import tarfile
from pathlib import Path, PurePosixPath

PROFILE = 'aitrust-development-source/1.0.0'
META = '.aitrust-source.json'
PREFIX = 'aitrust-id/'
MAX_FILES = 10_000
MAX_FILE = 32_000_000
MAX_TOTAL = 128_000_000
MAX_ARCHIVE = 64_000_000
COMMIT = re.compile(r'[0-9a-f]{40}')
SHA256 = re.compile(r'[0-9a-f]{64}')
PUBLIC_TEMPLATE = 'deploy/.env.example'
PUBLIC_TEMPLATE_SHA256 = 'bfc713439cb8581f639ca7f5ec150e8c4f608128c2688849011173bcc844ff8c'


def safe_name(name):
    if (not isinstance(name, str) or not name.isascii() or len(name) > 400
            or not re.fullmatch(r'[A-Za-z0-9_./-]+', name)
            or name.startswith('/') or any(p in ('', '.', '..') for p in name.split('/'))):
        raise ValueError('Unsafe source archive path')
    parts = PurePosixPath(name).parts
    forbidden = {'.git', '.DS_Store', 'node_modules', '.venv', 'venv',
                 'aitrust-id-coordination', 'private.pem', 'authorized_keys',
                 'id_ed25519', 'id_rsa'}
    if (any(p in forbidden or (p == '.env' or p.startswith('.env.'))
            and name != PUBLIC_TEMPLATE for p in parts)
            or name == META):
        raise ValueError('Private or reserved source path')
    return name


def public_template(name, data):
    if name == PUBLIC_TEMPLATE and hashlib.sha256(data).hexdigest() != PUBLIC_TEMPLATE_SHA256:
        raise ValueError('Reviewed public credential template changed')


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate source metadata key')
        result[key] = value
    return result


def parse(raw):
    if len(raw) > 5_000_000:
        raise ValueError('Source metadata limit')
    return json.loads(raw.decode('utf-8'), object_pairs_hook=unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite metadata')))


def git(root, *args):
    return subprocess.check_output(['git', '--no-replace-objects', '-C', str(root), *args], timeout=60)


def build(root, commit):
    if not COMMIT.fullmatch(commit):
        raise ValueError('Exact source commit required')
    actual = git(root, 'rev-parse', '--verify', commit + '^{commit}').decode().strip()
    if actual != commit:
        raise ValueError('Source identity mismatch')
    entries = git(root, 'ls-tree', '-rzl', commit).split(b'\0')
    files = []
    total = 0
    for entry in entries:
        if not entry:
            continue
        header, raw_name = entry.split(b'\t', 1)
        mode, kind, oid, size = header.decode('ascii').split()
        name = safe_name(raw_name.decode('ascii'))
        if kind != 'blob' or mode not in ('100644', '100755'):
            raise ValueError('Source links or submodules refused')
        length = int(size)
        total += length
        if length > MAX_FILE or total > MAX_TOTAL or len(files) >= MAX_FILES:
            raise ValueError('Committed source limit')
        data = git(root, 'cat-file', 'blob', oid)
        if len(data) != length:
            raise ValueError('Git blob length mismatch')
        public_template(name, data)
        files.append((name, int(mode[-3:], 8), data))
    if not files:
        raise ValueError('Empty committed source')
    files.sort(key=lambda row: row[0])
    metadata = {'profile': PROFILE, 'source_commit': commit,
                'kind': 'development_source_snapshot', 'tag_release_validated': False,
                'installed_dependencies_included': False,
                'files': [{'path': name, 'mode': mode, 'bytes': len(data),
                           'sha256': hashlib.sha256(data).hexdigest()}
                          for name, mode, data in files]}
    manifest = json.dumps(metadata, sort_keys=True, separators=(',', ':')).encode('utf-8')
    buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode='wb', filename='', mtime=0) as compressed:
        with tarfile.open(fileobj=compressed, mode='w', format=tarfile.USTAR_FORMAT) as archive:
            for name, mode, data in [(META, 0o644, manifest), *files]:
                member = tarfile.TarInfo(PREFIX + name)
                member.size = len(data)
                member.mode = mode
                member.mtime = member.uid = member.gid = 0
                member.uname = member.gname = ''
                archive.addfile(member, io.BytesIO(data))
    raw = buffer.getvalue()
    if len(raw) > MAX_ARCHIVE:
        raise ValueError('Compressed archive limit')
    inspect(raw, commit)
    return raw


def inspect(raw, expected_commit):
    if not COMMIT.fullmatch(expected_commit) or len(raw) > MAX_ARCHIVE:
        raise ValueError('Source commit or archive limit')
    observed = []
    seen = set()
    total = 0
    metadata = None
    # Bound decompression too: padding and extensions need not declare file sizes.
    expanded_limit = MAX_TOTAL + MAX_FILES * 2048 + 5_000_000
    with gzip.GzipFile(fileobj=io.BytesIO(raw), mode='rb') as compressed:
        expanded = compressed.read(expanded_limit + 1)
    if len(expanded) > expanded_limit:
        raise ValueError('Expanded archive limit')
    with tarfile.open(fileobj=io.BytesIO(expanded), mode='r|') as archive:
        for member in archive:
            name = member.name
            if (not member.isfile() or member.type not in (tarfile.REGTYPE, tarfile.AREGTYPE)
                    or member.pax_headers or not name.startswith(PREFIX)
                    or name in seen or len(seen) > MAX_FILES
                    or member.size < 0 or member.size > MAX_FILE
                    or member.mode not in (0o644, 0o755)
                    or member.uid != 0 or member.gid != 0 or member.mtime != 0
                    or member.uname or member.gname):
                raise ValueError('Unsafe or noncanonical archive member')
            seen.add(name)
            total += member.size
            if total > MAX_TOTAL:
                raise ValueError('Expanded source limit')
            relative = name[len(PREFIX):]
            if relative != META:
                safe_name(relative)
            elif seen != {PREFIX + META} or member.mode != 0o644:
                raise ValueError('Source metadata must be first')
            stream = archive.extractfile(member)  # Reads memory only; never writes/extracts a path.
            data = stream.read(member.size + 1)
            if len(data) != member.size:
                raise ValueError('Truncated archive member')
            if relative == META:
                metadata = parse(data)
            else:
                public_template(relative, data)
                observed.append({'path': relative, 'mode': member.mode, 'bytes': len(data),
                                 'sha256': hashlib.sha256(data).hexdigest()})
    required = {'profile', 'source_commit', 'kind', 'tag_release_validated',
                'installed_dependencies_included', 'files'}
    if (not isinstance(metadata, dict) or set(metadata) != required
            or metadata['profile'] != PROFILE or metadata['source_commit'] != expected_commit
            or metadata['kind'] != 'development_source_snapshot'
            or metadata['tag_release_validated'] is not False
            or metadata['installed_dependencies_included'] is not False
            or not observed or metadata['files'] != observed
            or [r['path'] for r in observed] != sorted(r['path'] for r in observed)):
        raise ValueError('Source inventory or identity mismatch')
    return {'profile': PROFILE, 'source_commit': expected_commit,
            'source_files': len(observed), 'source_bytes': sum(r['bytes'] for r in observed),
            'sha256': hashlib.sha256(raw).hexdigest(), 'tag_release_validated': False,
            'installed_dependencies_authenticated': False}


def read_file(path, limit):
    path = Path(path)
    if (path.is_symlink() or any(p.is_symlink() for p in path.parents)
            or not path.is_file()):
        raise ValueError('Missing or symlinked verification input')
    with path.open('rb') as stream:
        raw = stream.read(limit + 1)
    if not raw or len(raw) > limit:
        raise ValueError('Verification input limit')
    return raw
