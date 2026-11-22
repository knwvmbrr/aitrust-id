"""Bounded 16,384-file source serializer; preserves the v1 archive format.

V1 stays byte-identical for historical source observers. Only immutable helpers
and constants are reused; neither build nor inspect mutates legacy globals.
"""
import gzip
import hashlib
import io
import json
import tarfile

if __package__:
    from . import source_snapshot as legacy
else:
    import source_snapshot as legacy

PROFILE = legacy.PROFILE
META = legacy.META
PREFIX = legacy.PREFIX
MAX_FILES = 16_384
MAX_FILE = legacy.MAX_FILE
MAX_TOTAL = legacy.MAX_TOTAL
MAX_ARCHIVE = legacy.MAX_ARCHIVE
COMMIT = legacy.COMMIT
SHA256 = legacy.SHA256
PUBLIC_TEMPLATE = legacy.PUBLIC_TEMPLATE
PUBLIC_TEMPLATE_SHA256 = legacy.PUBLIC_TEMPLATE_SHA256
safe_name = legacy.safe_name
public_template = legacy.public_template
parse = legacy.parse
unique = legacy.unique
git = legacy.git
read_file = legacy.read_file
# Exposed stdlib module is also used by the unchanged read_file implementation.
os = legacy.os


def build(root, commit):
    if not COMMIT.fullmatch(commit):
        raise ValueError('Exact source commit required')
    actual = git(root, 'rev-parse', '--verify', commit + '^{commit}').decode().strip()
    if actual != commit:
        raise ValueError('Source identity mismatch')
    entries = git(root, 'ls-tree', '-rzl', commit).split(b'\0')
    if entries[-1:] != [b''] or len(entries) - 1 > MAX_FILES:
        raise ValueError('Committed source limit')
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
