"""Bounded source/grant observations for the exact optional MCP wheel runtime.

No source extraction or execution. Publisher declarations and source observations
are separate from an exhaustive compiled-closure or distribution authorization.
"""
import gzip
import functools
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re

MAX_ARCHIVE = 32 * 1024**2
MAX_EXPANDED = 512 * 1024**2
MAX_MEMBER = 32 * 1024**2
MAX_MEMBERS = 100_000
MAX_METADATA = 65_536
MAX_RETAINED = 4 * 1024**2
OPENSSL_EXCEPTION = ('325b5c806167c13b40b1ffeadfe0248197c00eccc4cf123ec1e28d2d2fd216d9', 55_235_667)
INPUTS = 'sbom/mcp-runtime/source-inputs.json'
INPUTS_SHA256 = 'd03511a97bc046bae63b5d801192e329858bb751ebc3b9f13c8d79a2029e80b6'


class SourceError(ValueError):
    pass


def need(ok):
    if not ok:
        raise SourceError('MCP source obligations unavailable.')


def refusal(function):
    @functools.wraps(function)
    def bounded(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except (OSError, ValueError, TypeError, KeyError, IndexError, OverflowError,
                RuntimeError, EOFError, RecursionError):
            raise SourceError('MCP source obligations unavailable.') from None
    return bounded


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def name(raw):
    need(type(raw) is str and 0 < len(raw) <= 512 and not raw.startswith('/') and
         '\\' not in raw and '\0' not in raw and not any(ord(c) < 32 for c in raw) and
         all(x not in ('', '.', '..') for x in raw.rstrip('/').split('/')))
    return raw.rstrip('/')


def number(raw):
    value = raw.rstrip(b'\0 ').lstrip(b' ')
    need(not value or re.fullmatch(b'[0-7]+', value))
    return int(value or b'0', 8)


def string(raw):
    parts = raw.split(b'\0', 1)
    need(len(parts) == 1 or not parts[1].strip(b'\0'))
    return parts[0].decode('utf-8')


def pax(raw):
    """Bounded PAX framing is parsed before any metadata-sized allocation."""
    need(len(raw) <= MAX_METADATA)
    cursor = 0
    result = {}
    while cursor < len(raw):
        space = raw.find(b' ', cursor, cursor+12)
        need(space != -1 and re.fullmatch(b'[1-9][0-9]{0,7}', raw[cursor:space]))
        size = int(raw[cursor:space])
        need(size > space-cursor+2 and cursor+size <= len(raw) and raw[cursor+size-1:cursor+size] == b'\n')
        entry = raw[space+1:cursor+size-1]
        key, sep, value = entry.partition(b'=')
        need(sep and len(key) < 100 and key not in result)
        result[key] = value
        cursor += size
    need(not any(k in result for k in (b'linkpath', b'GNU.sparse.map', b'GNU.sparse.size')))
    return result


def header_notice(prefix):
    """Retain a complete leading comment block, never a guessed full-file grant."""
    if b'\0' in prefix:
        return b''
    lines = prefix.splitlines(keepends=True)
    kept = []
    in_block = False
    for line in lines:
        s = line.lstrip()
        if in_block:
            kept.append(line)
            if b'*/' in line:
                in_block = False
            continue
        if not s.strip() or s.startswith((b'//', b'# ', b'#!', b';')):
            kept.append(line)
        elif s.startswith(b'/*'):
            kept.append(line)
            in_block = b'*/' not in line
        else:
            break
    raw = b''.join(kept)
    if in_block or not re.search(br'copyright|spdx-license-identifier|permission is hereby granted|licensed under', raw, re.I):
        return b''
    return raw


@refusal
def observe(raw, expected_sha256):
    need(type(raw) is bytes and sha(raw) == expected_sha256 and
         (0 < len(raw) <= MAX_ARCHIVE or (expected_sha256, len(raw)) == OPENSSL_EXCEPTION))
    expanded = 0
    retained = 0
    count = 0
    paths = set()
    rows = []
    notices = {}
    metadata = {}
    inherited = {}
    linked_unretained = 0
    with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
        def read(size):
            nonlocal expanded
            need(type(size) is int and 0 <= size <= MAX_MEMBER and expanded+size <= MAX_EXPANDED)
            data = stream.read(size)
            need(len(data) == size)
            expanded += len(data)
            return data
        while True:
            block = read(512)
            if block == bytes(512):
                need(read(512) == bytes(512))
                while True:
                    data = stream.read(65536)
                    if not data:
                        break
                    expanded += len(data)
                    need(expanded <= MAX_EXPANDED and not data.strip(b'\0'))
                break
            count += 1
            need(count <= MAX_MEMBERS)
            need(number(block[148:156]) == sum(block[:148])+8*32+sum(block[156:]))
            path = string(block[:100])
            prefix = string(block[345:500]) if block[257:262] == b'ustar' else ''
            path = prefix+'/'+path if prefix else path
            size = number(block[124:136])
            kind = block[156:157]
            need(size <= MAX_MEMBER)
            if kind in (b'x', b'g', b'L', b'K'):
                need(size <= MAX_METADATA and kind != b'K')
                data = read(size)
                if kind in (b'x', b'g'):
                    parsed = pax(data)
                    if kind == b'g':
                        need(b'path' not in parsed and b'size' not in parsed)
                        inherited.update(parsed)
                    else:
                        need(not metadata)
                        metadata = parsed
                else:
                    need(not metadata)
                    metadata = {b'path': data.rstrip(b'\0')}
                read((-size) % 512)
                continue
            if b'path' in metadata:
                path = metadata[b'path'].decode('utf-8')
            need(b'size' not in metadata or metadata[b'size'] == str(size).encode())
            path = name(path)
            need(path not in paths)
            paths.add(path)
            metadata = {}
            leaf = PurePosixPath(path).name
            notice_file = bool(re.fullmatch(r'(?i)(?:licen[cs]e|copying|notice|authors|copyright)(?:[._-].*)?', leaf))
            nonruntime = {'test', 'tests', 'testing', 'fuzz', 'fuzzing', 'benches', 'examples'}
            source_file = (not nonruntime.intersection(PurePosixPath(path).parts) and
                           path.endswith(('.rs', '.c', '.h', '.S', '.py', '.in')))
            manifest_file = leaf in ('Cargo.toml', 'Cargo.toml.orig', 'Cargo.lock', '.cargo_vcs_info.json')
            readme = bool(re.fullmatch(r'(?i)readme(?:[._-].*)?', leaf))
            if kind in (b'1', b'2'):
                need(not notice_file and not manifest_file)
                linked_unretained += 1
            else:
                need(kind in (b'\0', b'0', b'5'))
            selected = kind in (b'\0', b'0') and (notice_file or manifest_file or readme)
            need(not selected or size <= 2_000_000)
            digest = hashlib.sha256()
            whole = bytearray()
            prefix = bytearray()
            left = size
            while left:
                chunk = read(min(left, 65536))
                left -= len(chunk)
                digest.update(chunk)
                if selected:
                    whole.extend(chunk)
                if source_file and len(prefix) < 16384:
                    prefix.extend(chunk[:16384-len(prefix)])
            read((-size) % 512)
            if kind == b'5':
                need(size == 0)
            role = 'source_metadata' if manifest_file else 'source_readme' if readme else 'source_notice'
            data = bytes(whole) if selected else header_notice(bytes(prefix)) if source_file else b''
            if data:
                retained += len(data)
                need(retained <= MAX_RETAINED)
                if not selected:
                    role = 'leading_source_notice_observation'
                rows.append({'member': path, 'member_sha256': digest.hexdigest(), 'member_bytes': size,
                             'retained_sha256': sha(data), 'retained_bytes': len(data), 'role': role})
                notices[sha(data)] = data
    need(not metadata)
    return {'archive_sha256': expected_sha256, 'archive_bytes': len(raw), 'members_observed': count,
            'expanded_bytes': expanded, 'linked_unretained': linked_unretained,
            'retained': rows, 'exact_compiled_closure': False}, notices


@refusal
def collect(root, caches):
    """Replay the complete finite 150-source cohort from explicit local caches.

    A single private JSON can be published by the CLI without partial multi-file
    outputs. It includes raw public terms, not package source/test keys/corpora.
    """
    from tools.artifact_evidence_io import Capture
    need(type(caches) is list and 1 <= len(caches) <= 4)
    with Capture() as capture:
        raw = capture.read(Path(root)/INPUTS, 256_000, private=False)
        need(sha(raw) == INPUTS_SHA256)
        inputs = json.loads(raw)
        need(inputs['profile'] == 'mcp-pinned-native-source-inputs/v1' and len(inputs['packages']) == 150)
        packages = []
        texts = {}
        read_total = 0
        for entry in inputs['packages']:
            filename = entry['filename']
            need(Path(filename).name == filename and re.fullmatch(r'[A-Za-z0-9_.+\-]+', filename))
            found = None
            # A path's absence selects another explicit cache. A malformed or
            # changed present file is a refusal, never a silent fallback.
            for cache in caches:
                candidate = Path(cache)/filename
                try:
                    candidate.lstat()
                except FileNotFoundError:
                    continue
                found = candidate
                break
            need(found is not None and 0 < entry['bytes'] <= 55_235_667)
            read_total += entry['bytes']
            need(read_total <= 128*1024**2)
            buffer = io.BytesIO()
            observed = capture.artifact(found, entry['bytes'], copy_to=buffer)
            need(observed == {'bytes': entry['bytes'], 'sha256': entry['sha256']})
            record, retained = observe(buffer.getvalue(), entry['sha256'])
            selected = [x for x in record['retained'] if x['role'] in
                        ('source_notice', 'leading_source_notice_observation')]
            for row in selected:
                texts[row['retained_sha256']] = retained[row['retained_sha256']].decode('utf-8')
            packages.append({**entry, **record, 'retained': selected})
        need(len(texts) <= 5000 and sum(len(x.encode()) for x in texts.values()) <= 8_000_000)
        capture.check()
    return {'profile': 'mcp-native-source-notice-observations/v1',
            'input_sha256': INPUTS_SHA256, 'packages': packages,
            'texts': dict(sorted(texts.items())),
            'complete_compiled_closure': False, 'distribution_approved': False}
