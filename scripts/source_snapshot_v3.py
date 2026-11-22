"""Versioned 256 MB source serializer; immutable v1/v2 observers stay unchanged.

Wire format and canonical small-archive bytes are unchanged. Inspection streams
bounded gzip/tar records, with source and metadata charged separately.
"""
import gzip
import hashlib
import io
import json
import tarfile
import zlib

if __package__:
    from . import source_snapshot as legacy
else:
    import source_snapshot as legacy

PROFILE = legacy.PROFILE
META = legacy.META
PREFIX = legacy.PREFIX
MAX_FILES = 16_384
MAX_FILE = legacy.MAX_FILE
MAX_TOTAL = 256_000_000
MAX_METADATA = 5_000_000
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
    if type(commit) is not str or not COMMIT.fullmatch(commit):
        raise ValueError('Exact source commit required')
    actual = git(root, 'rev-parse', '--verify', commit + '^{commit}').decode().strip()
    if actual != commit:
        raise ValueError('Source identity mismatch')
    entries = git(root, 'ls-tree', '-rzl', commit).split(b'\0')
    if entries[-1:] != [b''] or len(entries) - 1 > MAX_FILES:
        raise ValueError('Committed source limit')
    files = []
    planned = []
    names = set()
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
        if length < 0 or length > MAX_FILE or total > MAX_TOTAL or len(files) >= MAX_FILES:
            raise ValueError('Committed source limit')
        if name in names or not COMMIT.fullmatch(oid):
            raise ValueError('Duplicate source path or invalid object identity')
        names.add(name)
        planned.append((name, mode, oid, length))
    for name, mode, oid, length in planned:
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
    if len(manifest) > MAX_METADATA:
        raise ValueError('Source metadata limit')
    buffer = _BoundedOutput()
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



class _BoundedOutput(io.BytesIO):
    def write(self, raw):
        if self.tell() + len(raw) > MAX_ARCHIVE:
            raise ValueError('Compressed archive limit')
        return super().write(raw)


def expanded_limit():
    # Source + one metadata payload; each has one header and <=511-byte padding.
    # Two end blocks, then at most RECORDSIZE-1 bytes to a canonical record end.
    return MAX_TOTAL + MAX_METADATA + (MAX_FILES + 1) * (512 + 511) + 1024 + tarfile.RECORDSIZE - 1


class _Inflated:
    """One gzip member, <=64KiB buffered chunks, no complete expanded tar copy."""
    def __init__(self, raw):
        self.raw = memoryview(raw)
        self.offset = self.total = self.position = 0
        self.pending = b''
        self.buffer = bytearray()
        self.decoder = zlib.decompressobj(31)
        self.finished = False

    def read(self, size):
        if type(size) is not int or not 0 <= size <= 65536:
            raise ValueError('Source read limit')
        while len(self.buffer) < size and not self.finished:
            if self.pending:
                block = self.pending
            elif self.offset < len(self.raw):
                block = self.raw[self.offset:self.offset + 65536]
                self.offset += len(block)
            else:
                raise ValueError('Truncated compressed source')
            try:
                data = self.decoder.decompress(block, min(65536, expanded_limit() - self.total + 1))
            except zlib.error:
                raise ValueError('Compressed source framing refused') from None
            self.pending = self.decoder.unconsumed_tail
            self.total += len(data)
            if self.total > expanded_limit():
                raise ValueError('Expanded archive limit')
            self.buffer.extend(data)
            if self.decoder.eof:
                if self.decoder.unused_data or self.pending or self.offset != len(self.raw):
                    raise ValueError('Extra compressed source data')
                self.finished = True
        value = bytes(self.buffer[:size])
        del self.buffer[:size]
        self.position += len(value)
        return value

    def take(self, size):
        value = self.read(size)
        if len(value) != size:
            raise ValueError('Truncated source archive')
        return value


def inspect(raw, expected_commit):
    if (type(raw) is not bytes or not raw or len(raw) > MAX_ARCHIVE
            or type(expected_commit) is not str or not COMMIT.fullmatch(expected_commit)):
        raise ValueError('Source commit or archive limit')
    reader = _Inflated(raw)
    observed, seen = [], set()
    total = 0
    metadata = None
    metadata_raw = None
    while True:
        header = reader.take(512)
        if not any(header):
            if any(reader.take(512)):
                raise ValueError('Source end blocks refused')
            minimum_end = reader.position
            while True:
                block = reader.read(65536)
                if not block:
                    break
                if any(block):
                    raise ValueError('Extra source archive data')
            expected_end = ((minimum_end + tarfile.RECORDSIZE - 1) // tarfile.RECORDSIZE) * tarfile.RECORDSIZE
            if reader.total != expected_end:
                raise ValueError('Noncanonical source record padding')
            break
        try:
            member = tarfile.TarInfo.frombuf(header, 'ascii', 'strict')
            generated = tarfile.TarInfo(member.name)
            generated.size, generated.mode = member.size, member.mode
            generated.mtime = generated.uid = generated.gid = 0
            generated.uname = generated.gname = ''
            canonical_header = generated.tobuf(format=tarfile.USTAR_FORMAT, encoding='ascii', errors='strict')
        except (tarfile.HeaderError, ValueError, UnicodeError):
            raise ValueError('Source header refused') from None
        name = member.name
        if (canonical_header != header or not member.isfile()
                or member.type not in (tarfile.REGTYPE, tarfile.AREGTYPE)
                or not name.startswith(PREFIX) or name in seen
                or member.size < 0 or member.mode not in (0o644, 0o755)
                or member.uid != 0 or member.gid != 0 or member.mtime != 0
                or member.uname or member.gname):
            raise ValueError('Unsafe or noncanonical archive member')
        relative = name[len(PREFIX):]
        is_metadata = relative == META
        if is_metadata:
            if seen or member.mode != 0o644 or not 0 < member.size <= MAX_METADATA:
                raise ValueError('Source metadata must be first and bounded')
        else:
            safe_name(relative)
            if metadata is None or len(observed) >= MAX_FILES or member.size > MAX_FILE:
                raise ValueError('Source member limit')
            total += member.size
            if total > MAX_TOTAL:
                raise ValueError('Expanded source limit')
        seen.add(name)
        digest = hashlib.sha256()
        collected = bytearray() if is_metadata else None
        remaining = member.size
        while remaining:
            data = reader.take(min(65536, remaining))
            remaining -= len(data)
            digest.update(data)
            if collected is not None:
                collected.extend(data)
        padding = (-member.size) % 512
        if padding and any(reader.take(padding)):
            raise ValueError('Nonzero source member padding')
        if is_metadata:
            try:
                metadata_raw = bytes(collected)
                metadata = parse(metadata_raw)
            except (ValueError, RecursionError):
                raise ValueError('Source metadata refused') from None
        else:
            value = digest.hexdigest()
            if relative == PUBLIC_TEMPLATE and value != PUBLIC_TEMPLATE_SHA256:
                raise ValueError('Reviewed public credential template changed')
            observed.append({'path': relative, 'mode': member.mode,
                             'bytes': member.size, 'sha256': value})
    if (not isinstance(metadata, dict) or not isinstance(metadata.get('files'), list)
            or any(type(row) is not dict or set(row) != {'path', 'mode', 'bytes', 'sha256'}
                   or type(row['mode']) is not int or type(row['bytes']) is not int
                   or type(row['path']) is not str or type(row['sha256']) is not str
                   for row in metadata.get('files', []))):
        raise ValueError('Source metadata record types refused')
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
    expected_metadata = {'profile': PROFILE, 'source_commit': expected_commit,
                         'kind': 'development_source_snapshot', 'tag_release_validated': False,
                         'installed_dependencies_included': False, 'files': observed}
    expected_raw = json.dumps(expected_metadata, sort_keys=True, separators=(',', ':')).encode('utf-8')
    if metadata_raw != expected_raw:
        raise ValueError('Noncanonical source metadata')
    return {'profile': PROFILE, 'source_commit': expected_commit,
            'source_files': len(observed), 'source_bytes': total,
            'sha256': hashlib.sha256(raw).hexdigest(), 'tag_release_validated': False,
            'installed_dependencies_authenticated': False}
