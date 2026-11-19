"""Bounded offline Rolldown notice/source mapping; never loads native addons."""
import base64
from datetime import datetime, timezone
import hashlib
import gzip
import io
import json
from pathlib import Path
import re
import tarfile
import tomllib

from protocol.evidence import read_evidence

ROOT = Path(__file__).resolve().parents[1]
PROFILE = 'rolldown-platform-source-observations/1.0.0'
MANIFEST = 'sbom/reviews/rolldown-source.json'
COMMIT = 'f7de35f45bcd4cb8e4b6d8d11e74fbfb20b03127'
PREFIX = 'node_modules/@rolldown/binding-'
MAX_ARCHIVE = 64 * 1024 * 1024
MAX_TOTAL = 300 * 1024 * 1024
MAX_MEMBER = 32 * 1024 * 1024
FILES = ('tools/rolldown_cohort.py', 'scripts/verify-rolldown-cohort.py',
         'tests/test_rolldown_cohort.py', 'docs/rolldown-source-review.md')
# NAPI target declarations mapped to the published package selectors; not ABI proof.
TARGETS = {
    'android-arm-eabi': ('armv7-linux-androideabi', ['android'], ['arm'], None),
    'android-arm64': ('aarch64-linux-android', ['android'], ['arm64'], None),
    'darwin-arm64': ('aarch64-apple-darwin', ['darwin'], ['arm64'], None),
    'darwin-x64': ('x86_64-apple-darwin', ['darwin'], ['x64'], None),
    'freebsd-x64': ('x86_64-unknown-freebsd', ['freebsd'], ['x64'], None),
    'linux-arm-gnueabihf': ('armv7-unknown-linux-gnueabihf', ['linux'], ['arm'], None),
    'linux-arm64-gnu': ('aarch64-unknown-linux-gnu', ['linux'], ['arm64'], ['glibc']),
    'linux-arm64-musl': ('aarch64-unknown-linux-musl', ['linux'], ['arm64'], ['musl']),
    'linux-ppc64-gnu': ('powerpc64le-unknown-linux-gnu', ['linux'], ['ppc64'], ['glibc']),
    'linux-s390x-gnu': ('s390x-unknown-linux-gnu', ['linux'], ['s390x'], ['glibc']),
    'linux-x64-gnu': ('x86_64-unknown-linux-gnu', ['linux'], ['x64'], ['glibc']),
    'linux-x64-musl': ('x86_64-unknown-linux-musl', ['linux'], ['x64'], ['musl']),
    'openharmony-arm64': ('aarch64-unknown-linux-ohos', ['openharmony'], ['arm64'], None),
    'win32-arm64-msvc': ('aarch64-pc-windows-msvc', ['win32'], ['arm64'], None),
    'win32-x64-msvc': ('x86_64-pc-windows-msvc', ['win32'], ['x64'], None),
}
SOURCE_FILES = ('LICENSE', 'THIRD-PARTY-LICENSE', 'Cargo.toml', 'Cargo.lock',
                'rust-toolchain.toml', 'crates/rolldown_binding/Cargo.toml',
                'crates/rolldown_binding/build.rs', 'packages/rolldown/package.json',
                'packages/rolldown/build-binding.ts', '.github/workflows/reusable-release-build.yml')
FLAGS = ('permission_cleared', 'release_approved', 'complete_transitive_coverage',
         'reproducible_build_verified', 'publisher_signature_verified', 'actual_toolchain_verified')


def need(ok):
    if not ok:
        raise ValueError('rolldown source evidence refused')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()


def read(path, limit=MAX_ARCHIVE):
    path = Path(path)
    need(not any(p.is_symlink() for p in [path, *path.parents]) and path.is_file())
    with path.open('rb') as handle:
        raw = handle.read(limit + 1)
    need(len(raw) <= limit)
    return raw


class ExpandedReader:
    """Bound decompressed tar bytes, including metadata before TarInfo exists."""
    def __init__(self, handle):
        self.handle = handle
        self.consumed = 0

    def read(self, size=-1):
        remaining = MAX_TOTAL - self.consumed
        requested = remaining + 1 if size < 0 else min(size, remaining + 1)
        data = self.handle.read(requested)
        self.consumed += len(data)
        need(self.consumed <= MAX_TOTAL)
        return data


def members(raw, source=False):
    need(type(raw) is bytes and 0 < len(raw) <= MAX_ARCHIVE)
    result = {}; total = 0
    source_prefix = 'rolldown-' + COMMIT + '/'
    link = source_prefix + 'packages/rolldown/tests/fixtures/builtin-plugin/import-glob/follow-symlinks/linked/my-lib'
    with gzip.GzipFile(fileobj=io.BytesIO(raw)) as expanded, \
            tarfile.open(fileobj=ExpandedReader(expanded), mode='r|') as archive:
        for entry in archive:
            name = entry.name
            need(type(name) is str and 0 < len(name) <= 512 and not name.startswith('/')
                 and '\\' not in name and all(ord(c) >= 32 for c in name)
                 and not any(p in ('', '.', '..') for p in name.rstrip('/').split('/')))
            need(name not in result and len(result) < 100000)
            if source:
                need(name.startswith(source_prefix) or name == source_prefix.rstrip('/'))
            else:
                need(name.startswith('package/') or name == 'package')
            allowed_link = source and name == link and entry.issym() and entry.linkname == '../packages/my-lib'
            need(entry.isfile() or entry.isdir() or allowed_link)
            need(0 <= entry.size <= MAX_MEMBER)
            total += entry.size; need(total <= MAX_TOTAL)
            data = archive.extractfile(entry).read() if entry.isfile() else None
            need(data is None or len(data) == entry.size)
            result[name] = data
    return result


def selected(root):
    lock = read_evidence(root / 'site/package-lock.json')['packages']
    inventory = read_evidence(root / 'sbom/native/manifest.json', limit=8_000_000)['artifacts']
    notices = read_evidence(root / 'sbom/notices/manifest.json', limit=8_000_000)['npm']
    names = sorted(k for k in lock if k.startswith(PREFIX) or k == 'node_modules/rolldown')
    need(names == sorted([PREFIX + k for k in TARGETS] + ['node_modules/rolldown']))
    result = []
    for name in names:
        entry = lock[name]; need(entry['version'] == '1.2.13')
        rows = [r for r in inventory if r['lock'] == 'site/package-lock.json' and r['package_path'] == name]
        texts = [r for r in notices if r['lock'] == 'site/package-lock.json' and r['package_path'] == name]
        need(len(rows) == len(texts) == 1)
        row, text = rows[0], texts[0]
        need(all(row[k] == entry[k] for k in ('version', 'integrity')))
        need(text['resolved'] == entry['resolved'] and text['artifact_sha256'] == row['artifact_sha256'])
        need(row['license_declared'] == entry['license'] == 'MIT' and len(row['native_candidates']) == 1)
        result.append({'package_path': name, 'lock': entry, 'native': row, 'notice': text})
    return result


def inspect_archive(raw, row):
    entry = row['lock']; algorithm, digest = entry['integrity'].split('-', 1)
    need(algorithm in ('sha256', 'sha512'))
    need(hashlib.new(algorithm, raw).digest() == base64.b64decode(digest, validate=True))
    need(sha(raw) == row['native']['artifact_sha256'])
    data = members(raw); package_raw = data['package/package.json']
    package = json.loads(package_raw.decode('utf-8'))
    need(package['name'] == row['package_path'].removeprefix('node_modules/') and package['version'] == '1.2.13')
    need(package['license'] == 'MIT')
    candidate = row['native']['native_candidates'][0]; content = data[candidate['member']]
    need(type(content) is bytes and len(content) == candidate['bytes'] and sha(content) == candidate['sha256'])
    if row['package_path'] != 'node_modules/rolldown':
        suffix = row['package_path'].removeprefix(PREFIX); target, os, cpu, libc = TARGETS[suffix]
        need(all(package.get(k) == v for k, v in [('os', os), ('cpu', cpu), ('libc', libc)]))
        need(candidate['member'] == 'package/' + package['main'] == 'package/rolldown-binding.' + suffix + '.node')
        need(all(row['lock'].get(k) == package.get(k) for k in ('os', 'cpu')))
        need('libc' not in row['lock'] or row['lock']['libc'] == package.get('libc'))
        selectors = {'target': target, 'os': os, 'cpu': cpu, 'libc': libc}
        bundled = {}
    else:
        need(candidate['member'] == 'package/bin/cli.mjs' and content.startswith(b'#!/usr/bin/env node'))
        need(package['optionalDependencies'] == {'@rolldown/binding-' + k: '1.2.13' for k in TARGETS})
        need(package['napi']['binaryName'] == 'rolldown-binding' and package['napi']['packageName'] == '@rolldown/binding')
        need(set(package['napi']['targets']) == {v[0] for v in TARGETS.values()} | {'wasm32-wasip1-threads'})
        selectors = None
        bundled = {name: {'sha256': sha(data['package/' + name]), 'bytes': len(data['package/' + name])}
                   for name in ('LICENSE', 'THIRD-PARTY-LICENSE')}
    return {'package_path': row['package_path'], 'archive_sha256': sha(raw), 'archive_bytes': len(raw),
            'package_json_sha256': sha(package_raw), 'package_json': package,
            'native_member': candidate, 'selector': selectors, 'bundled_notices': bundled,
            'binary_executed': False}


def source_projection(texts):
    package = json.loads(texts['packages/rolldown/package.json'].decode('utf-8'))
    need(package['name'] == 'rolldown' and package['version'] == '1.2.13')
    need(package['napi']['binaryName'] == 'rolldown-binding' and package['napi']['packageName'] == '@rolldown/binding')
    need(set(package['napi']['targets']) == {v[0] for v in TARGETS.values()} | {'wasm32-wasip1-threads'})
    recipe = texts['.github/workflows/reusable-release-build.yml'].decode('utf-8')
    need(all(target in recipe for target, *_ in TARGETS.values()))
    workspace = tomllib.loads(texts['Cargo.toml'].decode('utf-8'))
    binding = tomllib.loads(texts['crates/rolldown_binding/Cargo.toml'].decode('utf-8'))
    lock = tomllib.loads(texts['Cargo.lock'].decode('utf-8'))
    toolchain = tomllib.loads(texts['rust-toolchain.toml'].decode('utf-8'))
    need(workspace['workspace']['package']['license'] == 'MIT')
    need(binding['package']['name'] == 'rolldown_binding' and binding['package']['license']['workspace'] is True)
    packages = lock['package']; need(1 <= len(packages) <= 5000)
    sources = {'registry': 0, 'git': 0, 'workspace_or_path': 0, 'other': 0}
    for item in packages:
        src = item.get('source')
        kind = 'workspace_or_path' if src is None else 'registry' if src.startswith('registry+') else 'git' if src.startswith('git+') else 'other'
        sources[kind] += 1
    return {'declared_rust_channel': toolchain['toolchain']['channel'], 'workspace_license': 'MIT',
            'cargo_lock_package_count': len(packages), 'cargo_lock_source_counts': sources,
            'targets_declared': sorted(package['napi']['targets']), 'binary_to_source_reproduced': False,
            'cargo_lock_is_compiled_dependency_graph': False}


def verify(root=ROOT, archive_dir=None, source_dir=None):
    value = read_evidence(root / MANIFEST, limit=2_000_000)
    need(set(value) == {'profile', 'captured_at', 'source_commit', 'status', 'sources', 'selected_inputs_sha256',
                       'packages', 'upstream_archive', 'source_texts', 'source_projection', 'limits', *FLAGS})
    need(value['profile'] == PROFILE and value['source_commit'] == COMMIT and value['status'] == 'bounded_source_and_notice_evidence')
    stamp = datetime.fromisoformat(value['captured_at']); need(stamp.tzinfo is not None and stamp <= datetime.now(timezone.utc))
    need(all(value[k] is False for k in FLAGS))
    need(value['sources'] == {name: sha(read(root / name, 2_000_000)) for name in FILES})
    rows = selected(root); need(sha(encoded(rows)) == value['selected_inputs_sha256'])
    need(len(value['packages']) == 16 and [p['package_path'] for p in value['packages']] == [r['package_path'] for r in rows])
    total = 0; wrapper = None
    for row, item in zip(rows, value['packages']):
        need(set(item) == {'package_path', 'archive_sha256', 'archive_bytes', 'package_json_sha256', 'package_json', 'native_member', 'selector', 'bundled_notices', 'binary_executed'})
        need(item['archive_sha256'] == row['native']['artifact_sha256'] and item['native_member'] == row['native']['native_candidates'][0])
        need(type(item['archive_bytes']) is int and 0 < item['archive_bytes'] <= MAX_ARCHIVE and item['binary_executed'] is False)
        package = item['package_json']; need(package['name'] == row['package_path'].removeprefix('node_modules/') and package['version'] == '1.2.13' and package['license'] == 'MIT')
        need(re.fullmatch('[a-f0-9]{64}', item['package_json_sha256']))
        if row['package_path'] == 'node_modules/rolldown':
            wrapper = item; need(item['selector'] is None)
            need(package['optionalDependencies'] == {'@rolldown/binding-' + k: '1.2.13' for k in TARGETS})
            need(set(item['bundled_notices']) == {'LICENSE', 'THIRD-PARTY-LICENSE'})
        else:
            target, os, cpu, libc = TARGETS[row['package_path'].removeprefix(PREFIX)]
            need(item['selector'] == {'target': target, 'os': os, 'cpu': cpu, 'libc': libc} and item['bundled_notices'] == {})
            need(all(package.get(k) == expected for k, expected in [('os', os), ('cpu', cpu), ('libc', libc)]))
            need(row['lock'].get('os') == os and row['lock'].get('cpu') == cpu)
            need('libc' not in row['lock'] or row['lock']['libc'] == libc)
            need(item['native_member']['member'] == 'package/' + package['main'])
        if archive_dir is not None:
            raw = read(Path(archive_dir) / (sha(row['lock']['integrity'].encode()) + '.tgz'))
            total += len(raw); need(total <= MAX_TOTAL)
            need(inspect_archive(raw, row) == item)
    upstream = value['upstream_archive']
    need(set(upstream) == {'filename', 'url', 'final_url', 'bytes', 'sha256', 'captured_at', 'publisher_signature_verified', 'archive_checksum_basis'})
    need(upstream['filename'] == 'rolldown-source.tar.gz' and upstream['url'] == upstream['final_url'] == 'https://codeload.github.com/rolldown/rolldown/tar.gz/' + COMMIT)
    need(upstream['publisher_signature_verified'] is False and upstream['archive_checksum_basis'] == 'observed_sha256_not_independent_publisher_checksum')
    need(type(upstream['bytes']) is int and 0 < upstream['bytes'] <= MAX_ARCHIVE and re.fullmatch('[a-f0-9]{64}', upstream['sha256']))
    texts = {}; need(len(value['source_texts']) == len(SOURCE_FILES))
    for item in value['source_texts']:
        need(set(item) == {'member', 'path', 'sha256', 'bytes'})
        need(item['member'] in SOURCE_FILES and item['member'] not in texts)
        need(re.fullmatch('[a-f0-9]{64}', item['sha256']) and item['path'] == 'sbom/reviews/sources/' + item['sha256'] + '.txt')
        raw = read(root / item['path'], 2_000_000); raw.decode('utf-8', 'strict')
        need(sha(raw) == item['sha256'] and len(raw) == item['bytes']); texts[item['member']] = raw
    need(source_projection(texts) == value['source_projection'])
    need(wrapper['package_json']['napi'] == json.loads(texts['packages/rolldown/package.json'])['napi'])
    for name in ('LICENSE', 'THIRD-PARTY-LICENSE'):
        need(wrapper['bundled_notices'][name] == {'sha256': sha(texts[name]), 'bytes': len(texts[name])})
    if source_dir is not None:
        raw = read(Path(source_dir) / upstream['filename']); need(sha(raw) == upstream['sha256'] and len(raw) == upstream['bytes'])
        replay = members(raw, source=True)
        need(all(replay['rolldown-' + COMMIT + '/' + name] == content for name, content in texts.items()))
    return {'pass': True, 'profile': PROFILE, 'package_archives': 16, 'native_addons': 15,
            'binary_bytes_replayed': archive_dir is not None, 'source_archive_replayed': source_dir is not None,
            'notice_files': 2, 'source_texts': len(texts), **{key: False for key in FLAGS}}
