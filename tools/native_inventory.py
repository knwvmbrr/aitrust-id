"""Inspect captured npm artifacts without installing, extracting or executing them."""
import base64
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import tarfile

from protocol.evidence import unique, reject, finite
from scripts.source_snapshot import read_file
from scripts.license_notices import verify as verify_notices

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = 'sbom/native/manifest.json'
SOURCES = ('package-lock.json', 'site/package-lock.json', 'sbom/notices/manifest.json',
           'tools/native_inventory.py', 'scripts/verify-native-dependencies.py',
           'tests/test_native_inventory.py', 'scripts/source_snapshot.py',
           'scripts/license_notices.py', 'protocol/evidence.py', 'protocol/corpus.py')
PROFILE = 'npm-native-observations/1.0.0'
SHA = re.compile(r'[0-9a-f]{64}')
FORMATS = {'elf', 'wasm', 'pe-candidate', 'macho-or-fat-candidate', 'ar',
           'script', 'unclassified-native-name'}
MAX_ARCHIVE = 52_428_800
MAX_TOTAL = 536_870_912
MAX_MEMBER = 134_217_728
MAX_MEMBERS = 100_000
# Exact already-locked build artifacts observed above the default member budget.
# A different archive or member cannot inherit these size exceptions.
MEMBER_OVERRIDES = {
    '35c96f82088c5f311f309bb6fa2df302787235f8a91cb92ab5e9eb49c26683e7': {'package/bin/workerd': 135408472},
    '84370161e97a6821535cd6071a22da927b4843104a87e06fcfc4c2d792be693c': {'package/bin/workerd': 134840256},
    '7468a3a0645419e86180245c3669d20bea6e93bc15bd627f48b13a1e5ef5dd07': {'package/bin/workerd': 139110920},
}


def member_limit(row, name):
    return MEMBER_OVERRIDES.get(row['artifact_sha256'], {}).get(name, MAX_MEMBER)


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def parse(raw):
    value = json.loads(raw.decode('utf-8', 'strict'), object_pairs_hook=unique, parse_constant=reject)
    finite(value)
    require(type(value) is dict, 'Object metadata required')
    return value


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def safe_member(name):
    require(type(name) is str and 0 < len(name) <= 1024 and not name.startswith('/')
            and '\\' not in name and all(ord(c) >= 32 and not 0xD800 <= ord(c) <= 0xDFFF for c in name)
            and not any(p in ('', '.', '..') for p in name.rstrip('/').split('/')),
            'Unsafe archive member')


def classify(name, head):
    if head.startswith(b'\x7fELF'): return 'elf'
    if head.startswith(b'\x00asm'): return 'wasm'
    if head.startswith(b'MZ'): return 'pe-candidate'
    if head[:4] in (b'\xfe\xed\xfa\xce', b'\xfe\xed\xfa\xcf', b'\xce\xfa\xed\xfe',
                    b'\xcf\xfa\xed\xfe', b'\xca\xfe\xba\xbe', b'\xbe\xba\xfe\xca',
                    b'\xca\xfe\xba\xbf', b'\xbf\xba\xfe\xca'):
        return 'macho-or-fat-candidate'
    if head.startswith(b'!<arch>\n'): return 'ar'
    candidate = name.lower().endswith(('.node', '.wasm', '.dll', '.exe', '.dylib', '.so', '.a')) or '.so.' in name
    if candidate or '/bin/' in name:
        return 'script' if head.startswith(b'#!') else 'unclassified-native-name'
    return None


def inspect(raw, row):
    require(type(raw) is bytes and 0 < len(raw) <= MAX_ARCHIVE, 'Archive input limit')
    algorithm, encoded = row['integrity'].split('-', 1)
    require(algorithm in ('sha256', 'sha512'), 'Artifact integrity algorithm refused')
    expected = base64.b64decode(encoded, validate=True)
    require(len(expected) == {'sha256': 32, 'sha512': 64}[algorithm]
            and hashlib.new(algorithm, raw).digest() == expected
            and sha(raw) == row['artifact_sha256'], 'Artifact differs from pinned observation')
    natives, declarations, nested, blobs = [], [], [], {}
    seen, total = set(), 0
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r|gz') as archive:
        for member in archive:
            safe_member(member.name)
            prefix = 'emscripten/' if row.get('package_path') == 'node_modules/@types/emscripten' else 'package/'
            require(member.name.startswith(prefix) or member.isdir() and member.name == prefix[:-1],
                    'Artifact member root differs from package profile')
            require(member.name not in seen and len(seen) < MAX_MEMBERS, 'Duplicate/member count limit')
            seen.add(member.name)
            require(member.isdir() or member.isfile(), 'Archive links/special files refused')
            require(0 <= member.size <= member_limit(row, member.name), 'Archive member limit')
            total += member.size
            require(total <= MAX_TOTAL, 'Archive expanded byte limit')
            if member.isdir(): continue
            stream = archive.extractfile(member)  # Memory-only stream; never extract a path.
            head = stream.read(min(16, member.size))
            kind = classify(member.name, head)
            inner = member.name.lower().endswith(('.zip', '.whl', '.jar', '.tgz', '.tar.gz', '.tar.bz2'))
            declaration = member.name in ('package/README.md', 'package/versions.json')
            require(not declaration or member.size <= 2_000_000, 'Declaration byte limit')
            if not (kind or inner or declaration): continue
            digest = hashlib.sha256(head)
            chunks = [head] if declaration else None
            length = len(head)
            while chunk := stream.read(1_048_576):
                length += len(chunk)
                require(length <= member.size, 'Archive member overflow')
                digest.update(chunk)
                if chunks is not None: chunks.append(chunk)
            require(length == member.size, 'Archive member truncated')
            identity = {'member': member.name, 'bytes': length, 'sha256': digest.hexdigest()}
            if kind:
                require(len(natives) < 2048, 'Native candidate count limit')
                natives.append({**identity, 'format': kind})
            if inner:
                require(len(nested) < 2048, 'Nested archive count limit')
                nested.append(identity)
            if declaration:
                data = b''.join(chunks)
                text = data.decode('utf-8', 'strict')
                if member.name.endswith('versions.json'):
                    versions = parse(data)
                    require(len(versions) <= 512 and all(type(k) is str and 0 < len(k) <= 100
                            and type(v) is str and 0 < len(v) <= 200 for k, v in versions.items()),
                            'Bundled version metadata refused')
                    purpose = 'bundled_version_declaration'
                elif re.search(r'^#{1,6}\s+Licen[sc](?:e|ing)\b', text, re.I | re.M):
                    purpose = 'upstream_licensing_declaration'
                else:
                    continue
                blobs[identity['sha256']] = data
                declarations.append({**identity, 'kind': purpose,
                                     'blob': 'sources/' + identity['sha256'] + '.txt'})
    return {'native_candidates': sorted(natives, key=lambda r: r['member']),
            'declarations': sorted(declarations, key=lambda r: r['member']),
            'uninspected_nested_archives': sorted(nested, key=lambda r: r['member'])}, blobs


def source_hashes(root=ROOT):
    return {p: sha(read_file(root / p, 8_000_000)) for p in SOURCES}


def inputs(root=ROOT, snapshot=None):
    verify_notices(root)
    names = ('sbom/notices/manifest.json', 'package-lock.json', 'site/package-lock.json')
    captured = {name: read_file(root/name, 8_000_000) for name in names}
    if snapshot is not None:
        require(all(sha(raw) == snapshot[name] for name,raw in captured.items()),
                'Captured dependency inputs differ from source snapshot')
    value = parse(captured[names[0]])
    locked = {(name,path): row for name in names[1:]
              for path,row in parse(captured[name])['packages'].items() if path}
    rows = value['npm']
    require(len(rows) == len(locked), 'Incomplete captured dependency inputs')
    identities = [(row['lock'],row['package_path']) for row in rows]
    require(len(set(identities)) == len(identities) and set(identities) == set(locked),
            'Duplicate or missing captured artifact identity')
    for row in rows:
        item = locked[(row['lock'],row['package_path'])]
        require(all(row[k] == item[k] for k in ('version','integrity','resolved'))
                and row['license_declared'] == item.get('license'), 'Captured lock identity mismatch')
    return rows


def collect(archive_dir, root=ROOT, *, observer):
    require(type(observer) is str and re.fullmatch(r'[A-Za-z][A-Za-z0-9 ._-]{0,79}', observer),
            'Observer attribution refused')
    before = source_hashes(root)
    artifacts, blobs = [], {}
    for row in inputs(root, before):
        cache_key = sha(row['integrity'].encode()) + '.tgz'
        raw = read_file(Path(archive_dir) / cache_key, MAX_ARCHIVE)
        observed, texts = inspect(raw, row)
        artifacts.append({k: row[k] for k in ('lock', 'package_path', 'version',
                                               'integrity', 'artifact_sha256', 'license_declared')} | observed)
        blobs.update(texts)
    require(before == source_hashes(root), 'Observation sources changed')
    return {'profile': PROFILE, 'captured_at': datetime.now(timezone.utc).isoformat(),
            'observed_by': observer, 'sources': before, 'artifacts': artifacts,
            'permissions_reviewed': False, 'complete_transitive_coverage': False,
            'independent_accuracy_evidence': False}, blobs


def verify(root=ROOT, archive_dir=None):
    before = source_hashes(root)
    raw_manifest = read_file(root / MANIFEST, 8_000_000)
    value = parse(raw_manifest)
    require(set(value) == {'profile', 'captured_at', 'observed_by', 'sources', 'artifacts',
                          'permissions_reviewed', 'complete_transitive_coverage', 'independent_accuracy_evidence'}
            and value['profile'] == PROFILE and type(value['observed_by']) is str
            and re.fullmatch(r'[A-Za-z][A-Za-z0-9 ._-]{0,79}', value['observed_by'])
            and all(value[k] is False for k in ('permissions_reviewed', 'complete_transitive_coverage',
                                               'independent_accuracy_evidence')),
            'Unsupported inventory or clearance promotion')
    stamp = datetime.fromisoformat(value['captured_at'])
    require(stamp.tzinfo is not None and stamp <= datetime.now(timezone.utc), 'Invalid observation time')
    require(value['sources'] == before, 'Native inventory source drift')
    expected = {(r['lock'], r['package_path']): r for r in inputs(root, before)}
    rows = value['artifacts']
    require(type(rows) is list and len(rows) == len(expected), 'Missing artifact coverage')
    identities, referenced, saved = set(), set(), {}
    counts = {'native_candidates': 0, 'licensing_declarations': 0, 'version_declarations': 0,
              'uninspected_nested_archives': 0}
    for row in rows:
        require(type(row) is dict and set(row) == {'lock', 'package_path', 'version', 'integrity',
                'artifact_sha256', 'license_declared', 'native_candidates', 'declarations',
                'uninspected_nested_archives'}, 'Artifact inventory fields refused')
        identity = (row['lock'], row['package_path'])
        require(identity in expected and identity not in identities, 'Unknown/duplicate artifact')
        identities.add(identity)
        require(all(row[k] == expected[identity][k] for k in ('version', 'integrity',
                'artifact_sha256', 'license_declared')), 'Artifact observation identity changed')
        for group in ('native_candidates', 'declarations', 'uninspected_nested_archives'):
            entries = row[group]
            require(type(entries) is list and len(entries) <= 2048, 'Invalid member inventory')
            names = []
            for member in entries:
                fields = {'member', 'bytes', 'sha256'} | ({'format'} if group == 'native_candidates'
                    else {'kind', 'blob'} if group == 'declarations' else set())
                require(type(member) is dict and set(member) == fields, 'Member inventory fields refused')
                safe_member(member['member']); names.append(member['member'])
                require(type(member['bytes']) is int and 0 <= member['bytes'] <= member_limit(row, member['member'])
                        and type(member['sha256']) is str and SHA.fullmatch(member['sha256']), 'Invalid member identity')
                if group == 'native_candidates':
                    require(member['format'] in FORMATS, 'Unknown candidate format')
                    counts[group] += 1
                elif group == 'declarations':
                    require(member['kind'] in ('upstream_licensing_declaration', 'bundled_version_declaration')
                            and member['blob'] == 'sources/' + member['sha256'] + '.txt', 'Declaration identity refused')
                    path = 'sbom/native/' + member['blob']
                    data = read_file(root / path, 2_000_000)
                    require(len(data) == member['bytes'] and sha(data) == member['sha256'], 'Declaration bytes changed')
                    data.decode('utf-8', 'strict')
                    referenced.add(path); saved[path] = data
                    counts['licensing_declarations' if member['kind'] == 'upstream_licensing_declaration'
                           else 'version_declarations'] += 1
                else: counts[group] += 1
            require(names == sorted(set(names)), 'Duplicate or unordered member inventory')
        if archive_dir is not None:
            file = Path(archive_dir) / (sha(row['integrity'].encode()) + '.tgz')
            observed, _ = inspect(read_file(file, MAX_ARCHIVE), expected[identity])
            require(all(observed[k] == row[k] for k in observed), 'Archive observation does not reproduce')
    require((root/'sbom/native/sources').is_dir() and not (root/'sbom/native/sources').is_symlink(),
            'Unsafe declaration directory')
    actual = {'sbom/native/sources/' + p.name for p in (root/'sbom/native/sources').iterdir()}
    require(actual == referenced, 'Missing/orphan declaration file')
    require(before == source_hashes(root) and raw_manifest == read_file(root/MANIFEST, 8_000_000)
            and all(data == read_file(root/p, 2_000_000) for p,data in saved.items())
            and actual == {'sbom/native/sources/' + p.name for p in (root/'sbom/native/sources').iterdir()},
            'Inventory changed during verification')
    return {'captured_at': datetime.now(timezone.utc).isoformat(), 'pass': True,
            'profile': PROFILE, 'artifacts': len(rows), **counts,
            'archive_replay': archive_dir is not None, 'binary_bytes_replayed': archive_dir is not None,
            'inventory_sha256': sha(raw_manifest), 'observation_authenticated': False, 'permission_cleared': False,
            'complete_transitive_coverage': False, 'independent_accuracy_evidence': False}
