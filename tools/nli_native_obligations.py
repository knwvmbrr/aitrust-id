"""Exact optional NLI native source/notice observations; never imports a model."""
import gzip
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import tarfile
import time
import tomllib

ROOT = Path(__file__).resolve().parents[1]
PROFILE = 'nli-native-dependency-observations/v1'
STORE = 'sbom/nli-native/sources/'
MANIFEST = 'sbom/nli-native/manifest.json'
MAX_ARCHIVE = 16 * 1024**2
MAX_EXPANDED = 128 * 1024**2
MAX_RETAINED = 8 * 1024**2
MAX_TOTAL = 32 * 1024**2
MAX_FILES = 20000
FAMILIES = ('PyYAML', 'hf-xet', 'ml_dtypes', 'numpy', 'onnx', 'onnxruntime', 'protobuf', 'tokenizers')
CLAIMS = {'permission_cleared': False, 'distribution_approved': False,
          'source_build_reproduced': False, 'independent_accuracy': False}


def need(value):
    if not value:
        raise ValueError('NLI native source evidence refused.')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True, allow_nan=False).encode('ascii')


def document(raw):
    def unique(items):
        out = {}
        for key, value in items:
            need(key not in out)
            out[key] = value
        return out
    return json.loads(raw.decode('utf-8', 'strict'), object_pairs_hook=unique,
                      parse_constant=lambda _: need(False))


def read(path, limit=MAX_RETAINED):
    path = Path(path).absolute()
    need(not any(p.is_symlink() for p in (path, *path.parents)))
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and 0 < before.st_size <= limit)
        result = bytearray()
        while len(result) <= limit:
            part = os.read(fd, min(65536, limit + 1 - len(result)))
            if not part:
                break
            result.extend(part)
        identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
        need(len(result) == before.st_size and identity(before) == identity(os.fstat(fd))
             == identity(os.stat(path, follow_symlinks=False)))
        return bytes(result)
    finally:
        os.close(fd)


def safe(name):
    need(type(name) is str and 0 < len(name) <= 512 and not name.startswith('/')
         and '\\' not in name and ':' not in name
         and all(ord(c) >= 32 and ord(c) != 127 for c in name)
         and all(p not in ('', '.', '..') for p in name.rstrip('/').split('/')))


def selected_member(name):
    leaf = PurePosixPath(name).name.lower()
    return (any(word in leaf for word in ('license', 'licence', 'copying', 'notice', 'copyright', 'authors', 'patents'))
            or leaf in ('cargo.toml', 'cargo.lock', 'pyproject.toml', 'setup.py',
                        'setup.cfg', 'meson.build', 'cmakelists.txt', '.gitmodules',
                        '.git_archival.txt', 'version.py', '_version.py')
            or leaf.startswith('readme'))


def notice_member(name):
    return any(any(word in part.lower() for word in
                   ('license', 'licence', 'copying', 'notice', 'copyright', 'authors', 'patents'))
               for part in PurePosixPath(name).parts)


class Expanded:
    def __init__(self, stream):
        self.stream, self.total = stream, 0

    def read(self, size=-1):
        left = MAX_EXPANDED - self.total
        data = self.stream.read(left + 1 if size < 0 else min(size, left + 1))
        self.total += len(data)
        need(self.total <= MAX_EXPANDED)
        return data


def archive(raw, *, extra=(), limit=MAX_ARCHIVE):
    """Bound PAX and all other expanded bytes before tarfile sees them."""
    need(limit in (MAX_ARCHIVE, 21 * 1024**2))
    need(type(raw) is bytes and 0 < len(raw) <= limit)
    out, seen, retained, files = {}, set(), 0, 0
    source_files = eigen_headers = 0
    with gzip.GzipFile(fileobj=io.BytesIO(raw)) as gz:
        stream = Expanded(gz)
        with tarfile.open(fileobj=stream, mode='r|') as tar:
            for member in tar:
                safe(member.name)
                need(member.name not in seen and len(seen) < MAX_FILES)
                seen.add(member.name)
                need(member.isfile() or member.isdir())
                need(0 <= member.size <= MAX_EXPANDED)
                if member.isdir():
                    need(member.size == 0)
                    continue
                files += 1
                if PurePosixPath(member.name).suffix.lower() in ('.h', '.hpp', '.c', '.cc', '.cpp', '.rs', '.f90'):
                    source_files += 1
                    if '/eigen/' in member.name.lower() and PurePosixPath(member.name).suffix.lower() in ('.h', '.hpp'):
                        eigen_headers += 1
                if selected_member(member.name) or member.name in extra:
                    need(member.size <= MAX_RETAINED and retained + member.size <= MAX_RETAINED)
                    with tar.extractfile(member) as source:
                        value = source.read(member.size + 1)
                    need(len(value) == member.size)
                    retained += len(value)
                    out[member.name] = value
        while stream.read(65536):
            pass
    return out, {'regular_files': files, 'retained_bytes': retained,
                 'expanded_bytes_observed': stream.total,
                 'source_files_observed': source_files, 'eigen_headers_observed': eigen_headers}


def cargo_graph(raw):
    need(type(raw) is bytes and 0 < len(raw) <= MAX_RETAINED)
    value = tomllib.loads(raw.decode('utf-8'))
    need(type(value.get('version')) is int and value['version'] in (3, 4))
    packages = value.get('package')
    need(type(packages) is list and 0 < len(packages) <= 1000)
    nodes, names = {}, {}
    for row in packages:
        need(type(row) is dict and {'name', 'version'} <= set(row)
             <= {'name', 'version', 'source', 'checksum', 'dependencies'})
        name, version = row['name'], row['version']
        need(type(name) is str and re.fullmatch(r'[A-Za-z0-9_-]{1,128}', name)
             and type(version) is str and re.fullmatch(r'[0-9][A-Za-z0-9.+_-]{0,127}', version))
        identifier = name + '@' + version
        need(identifier not in nodes)
        if 'source' in row:
            need(row['source'] == 'registry+https://github.com/rust-lang/crates.io-index'
                 and type(row.get('checksum')) is str
                 and re.fullmatch(r'[a-f0-9]{64}', row['checksum']))
        else:
            need('checksum' not in row)
        need(type(row.get('dependencies', [])) is list and len(row.get('dependencies', [])) <= 1000)
        nodes[identifier] = row
        names.setdefault(name, []).append(identifier)
    result = []
    for identifier, row in nodes.items():
        dependencies = []
        for item in row.get('dependencies', []):
            need(type(item) is str and len(item) <= 512)
            parts = item.split(' ')
            need(len(parts) in (1, 2))
            matches = names.get(parts[0], []) if len(parts) == 1 else ['@'.join(parts)]
            need(len(matches) == 1 and matches[0] in nodes and matches[0] not in dependencies)
            dependencies.append(matches[0])
        result.append({'id': identifier, 'name': row['name'], 'version': row['version'],
                       'archive_sha256': row.get('checksum'),
                       'dependency_ids': sorted(dependencies)})
    return sorted(result, key=lambda row: row['id'])

EVIDENCE = 'sbom/nli-native/evidence.json'
EVIDENCE_SHA = '5b6d4fd0b88eff23fe2d3512f551f42649e3af7b71aa60865e07605955696b32'
BASE_INPUTS = {
    'sbom/reviews/nli/manifest.json': 'c1c2cd50b49421ee8b12f45183698d1e6995a67b1a016b482c7d41aad9efada2',
    'research/nli/requirements-mac.lock': '02960b1ea4f3a0b8d31ecba9ca376261383abefc6111dc3054f2f3fe5115e88c',
    'research/nli/requirements-linux.lock': 'e149a6705f77d47139d66e93b159db048c28dbb8be3e79f32c58e567f820701d',
    'research/nli/wheel-provenance-mac.json': '58a70430251ee95c37bdbc692b3e98a0738ebacbb5206f671e8afc9534ebe339',
    'research/nli/wheel-provenance-linux.json': '978e017c6024ab926739765b7600b93062b8556f99741f41412ed691ae72f9f3',
}
OWN = ('tools/nli_native_obligations.py', 'scripts/verify-nli-native-obligations.py',
       'tests/test_nli_native_obligations.py', 'docs/nli-native-obligations-plan.md',
       'docs/nli-native-obligations.md')
GAPS = [
    'Published Rust lock unions include optional/dev/target alternatives, not an exhaustive incorporated native graph.',
    'Exact ONNX Runtime1.31 source/build identity and applicable covered-source material were not recovered; current404 is retrieval evidence, not proof of proprietary licensing or source absence.',
    'NumPy Linux shipped GNU runtime terms/source obligations require distribution-specific source or valid offer/relinking handling; NumPy project source is not automatically all GCC runtime source.',
    'Private acquired source archives and preserved grants are not an already published distribution source offer.',
    'Binary reproduction, compiler identity, signatures, model accuracy and global legal/distribution permission are not established.',
]


def member_bytes(root, row):
    need(type(row['bytes']) is int and 0 <= row['bytes'] <= MAX_RETAINED)
    if row['bytes'] == 0:
        need(row['path'] is None and row['sha256'] == sha(b''))
        return b''
    need(type(row['path']) is str and re.fullmatch(STORE + r'[a-f0-9]{64}\.txt', row['path']))
    raw = read(root / row['path'])
    need(len(raw) == row['bytes'] and sha(raw) == row['sha256'] == Path(row['path']).stem)
    return raw


def actions(license_value):
    out = ['retain applicable complete copyright/license/disclaimer and NOTICE texts',
           'do not infer incorporation or permission from a package license label']
    text = license_value or ''
    if 'MPL' in text:
        out.append('make applicable covered Source Code Form available under MPL with prescribed notice; no claim this private cache is a published source offer')
    if 'GPL' in text:
        out.append('apply exact GNU runtime/source or relinking conditions and any applicable exception; no blanket exception from a notice filename')
    if 'Apache' in text:
        out.append('preserve applicable attribution/NOTICE and identify modifications; no upstream endorsement or trademark grant inferred')
    if not license_value:
        out.append('license declaration absent; inspect actual source grant, never infer proprietary status from absence')
    return out


def record(identifier, name, version, license_value, notices, dependencies, evidence, **extra):
    need(type(identifier) is str and 0 < len(identifier) <= 300)
    need(type(name) is str and 0 < len(name) <= 256)
    need(license_value is None or type(license_value) is str and len(license_value) <= 1024)
    return {'id': identifier, 'name': name, 'version': version,
            'license_declared': license_value, 'notice_paths': sorted(set(notices)),
            'term_actions': actions(license_value), 'dependency_ids': sorted(set(dependencies)),
            'evidence_paths': sorted(set(evidence)), **extra}


def expected(root=ROOT):
    root = Path(root)
    inputs = {}
    for path, digest in BASE_INPUTS.items():
        need(sha(read(root / path)) == digest)
        inputs[path] = digest
    raw = read(root / EVIDENCE, 16 * 1024**2)
    need(sha(raw) == EVIDENCE_SHA)
    index = document(raw)
    need(set(index) == {'format', 'captured_at', 'source_archives', 'cargo_locks',
                       'rust_archives', 'supplements', 'copied_wheel_notices',
                       'claims', 'external_source_records'})
    need(index['format'] == 'nli-native-retained-evidence/v1'
         and canonical(index['claims']) == canonical(CLAIMS))
    inputs[EVIDENCE] = EVIDENCE_SHA
    for path in OWN:
        inputs[path] = sha(read(root / path))
    old = document(read(root / 'sbom/reviews/nli/manifest.json'))
    sources = {}

    def bind(row):
        if row['path'] is None:
            member_bytes(root, row)
            return
        path = row['path']
        previous = sources.get(path)
        value = {'path': path, 'sha256': row['sha256'], 'bytes': row['bytes']}
        need(previous is None or previous == value)
        if previous is None:
            need(type(row['bytes']) is int and 0 < row['bytes'] <= MAX_RETAINED
                 and sum(r['bytes'] for r in sources.values()) + row['bytes'] <= MAX_TOTAL)
            member_bytes(root, row)
            sources[path] = value

    archives = [*index['source_archives'], *index['rust_archives']]
    for arc in archives:
        need(type(arc['members']) is list and len(arc['members']) <= MAX_FILES)
        seen = set()
        for item in arc['members']:
            safe(item['member']); need(item['member'] not in seen); seen.add(item['member']); bind(item)
        if 'publisher_metadata' in arc:
            bind(arc['publisher_metadata'])
            meta = document(member_bytes(root, arc['publisher_metadata']))
            match = [v for v in meta['urls'] if v['filename'] == arc['filename']]
            need(len(match) == 1 and match[0]['url'] == arc['url']
                 and match[0]['digests']['sha256'] == arc['sha256']
                 and match[0]['size'] == arc['bytes'])
    for row in index['supplements']:
        if 'members' in row:
            for member in row['members']: bind(member)
        else: bind(row)
    for row in [*index['external_source_records'], *index['cargo_locks'], *index['copied_wheel_notices']]:
        bind(row)
    need(len(sources) <= 10000)
    need({p.relative_to(root).as_posix() for p in (root / STORE).iterdir()} == set(sources))

    nodes = {}
    lock_nodes = {}
    selected_locks = [r for r in index['cargo_locks'] if r['role'] == 'selected_published_build_lock']
    need({r['family'] for r in selected_locks} == {'hf-xet', 'tokenizers'} and len(selected_locks) == 2)
    for lock in selected_locks:
        lock_nodes[lock['family']] = cargo_graph(member_bytes(root, lock))
    dependency_union = {}
    registry = {}
    for family, rows in lock_nodes.items():
        table = {r['id']: r for r in rows}
        def identifier(item):
            return ('crate:' if table[item]['archive_sha256'] else 'workspace:' + family + ':') + item
        for item in rows:
            key = identifier(item['id'])
            dependency_union.setdefault(key, set()).update(identifier(v) for v in item['dependency_ids'])
            if item['archive_sha256']:
                if item['id'] in registry: need(registry[item['id']]['archive_sha256'] == item['archive_sha256'])
                registry[item['id']] = item
            else:
                project = next(a for a in index['source_archives'] if a['family'] == family)
                notices = [m['path'] for m in project['members'] if m['bytes'] and notice_member(m['member'])]
                nodes[key] = record(key, item['name'], item['version'], 'Apache-2.0', notices, [],
                                    [lock['path'], *notices], archive_sha256=project['sha256'],
                                    source_identity={'kind': 'published_sdist_workspace_declaration', 'url': project['url'], 'exact_binary_correspondence': False})
    need(len(registry) == len(index['rust_archives']) == 540)
    for arc in index['rust_archives']:
        ident = arc['name'] + '@' + arc['version']; need(ident in registry)
        need(arc['sha256'] == registry[ident]['archive_sha256'])
        manifest = [m for m in arc['members'] if m['member'].endswith('/Cargo.toml') and m['member'].count('/') == 1]
        need(len(manifest) == 1)
        package = tomllib.loads(member_bytes(root, manifest[0]).decode('utf-8'))['package']
        need(package['name'] == arc['name'] and package['version'] == arc['version'])
        license_file = package.get('license-file')
        if license_file is not None:
            safe(license_file)
        declared_member = arc['name'] + '-' + arc['version'] + '/' + license_file if license_file else None
        notices = [m['path'] for m in arc['members'] if m['bytes'] and
                   (notice_member(m['member']) or m['member'] == declared_member)]
        key = 'crate:' + ident
        nodes[key] = record(key, arc['name'], arc['version'], package.get('license'), notices, [],
                            [manifest[0]['path'], *notices], archive_sha256=arc['sha256'],
                            source_identity={'kind': 'checksummed_published_registry_source', 'url': arc['url'],
                                             'license_file_declared': license_file,
                                             'declared_license_file_present': any(m['member'] == declared_member for m in arc['members']) if declared_member else None,
                                             'exact_binary_correspondence': False})
    for key, dependencies in dependency_union.items(): nodes[key]['dependency_ids'] = sorted(dependencies)

    project_notices = {}
    for family in FAMILIES:
        wheels = [w for w in old['wheels'] if w['name'] == family]
        need(len(wheels) == 2 and {w['platform'] for w in wheels} == {'linux', 'mac'})
        source = next((a for a in index['source_archives'] if a['family'] == family), None)
        notices = [r['path'] for r in index['copied_wheel_notices'] if r['package'] == family]
        if source:
            notices += [m['path'] for m in source['members'] if m['bytes'] and notice_member(m['member'])]
        license_value = next(o['terms_reviewed'] for o in old['obligations'] if o['name'] == family)
        deps = [key for key in nodes if key.startswith('workspace:' + family + ':')]
        project_key = 'project:' + family + '@' + wheels[0]['version']
        evidence = list(notices)
        if source: evidence.append(source['publisher_metadata']['path'])
        nodes[project_key] = record(project_key, family, wheels[0]['version'], license_value,
                                    notices, deps, evidence,
                                    platforms=['linux', 'mac'],
                                    source_identity={'kind': 'published_sdist_and_shipped_wheel_terms' if source else 'shipped_wheel_terms_source_unrecovered',
                                                     'url': source['url'] if source else None,
                                                     'source_archive_sha256': source['sha256'] if source else None,
                                                     'preferred_source_observed': source is not None,
                                                     'distributed_source_offer_fulfilled': False,
                                                     'exact_binary_correspondence': False})
        project_notices[family] = notices
        for wheel in wheels:
            key = 'wheel:' + wheel['platform'] + ':' + family + '@' + wheel['version']
            rows = [x for x in index['copied_wheel_notices'] if x['platform'] == wheel['platform'] and x['package'] == family]
            need(len(rows) == len(wheel['notices']))
            for row in rows:
                match = next(v for v in wheel['notices'] if v['member'] == row['original_member'])
                need(row['wheel_sha256'] == wheel['sha256'] and row['sha256'] == match['sha256'] and row['bytes'] == match['bytes'])
            nodes[key] = record(key, family, wheel['version'], wheel['declared_license'],
                                [x['path'] for x in rows], [project_key],
                                [x['path'] for x in rows], platforms=[wheel['platform']],
                                archive_sha256=wheel['sha256'],
                                source_identity={'kind': 'existing_exact_native_wheel_observation', 'url': wheel['pypi_url'],
                                                 'native_members': wheel['native_members'], 'source_equivalence': False})

    libyaml = next(s for s in index['supplements'] if s['name'] == 'LibYAML')
    yaml_notices = [m['path'] for m in libyaml['members'] if m['bytes'] and any(x in PurePosixPath(m['member']).name.lower() for x in ('license', 'copying'))]
    need(yaml_notices)
    recipe = [s['path'] for s in index['supplements'] if s['name'] == 'PyYAML build declaration']
    key = 'component:LibYAML@0.2.5'
    nodes[key] = record(key, 'LibYAML', '0.2.5', 'MIT', yaml_notices, [], [*yaml_notices, *recipe],
                        source_identity={'kind': 'upstream_source_and_declared_default_build_recipe', 'url': libyaml['url'],
                                         'archive_sha256': libyaml['sha256'], 'recipe_inputs_overrideable': True,
                                         'actual_wheel_build_recipe_attested': False})
    nodes['project:PyYAML@6.0.3']['dependency_ids'].append(key)
    eigen = next(a for a in index['source_archives'] if a['family'] == 'ml_dtypes')
    key = 'component:Eigen-in-ml_dtypes@0.6.0'
    nodes[key] = record(key, 'Eigen covered source within ml_dtypes', '0.6.0-source-package', 'MPL-2.0',
                        project_notices['ml_dtypes'], [], [m['path'] for m in eigen['members'] if m['bytes']],
                        source_identity={'kind': 'preferred_headers_in_exact_published_sdist', 'url': eigen['url'],
                                         'archive_sha256': eigen['sha256'], 'published_source_present': True,
                                         'distributed_source_offer_fulfilled': False, 'exact_binary_correspondence': False})
    nodes['project:ml_dtypes@0.6.0']['dependency_ids'].append(key)

    gnu_supplement = next(s['path'] for s in index['supplements'] if s['name'] == 'GNU libquadmath complete LGPL terms')
    for name, terms in [('OpenBLAS/LAPACK', 'BSD-3-Clause'), ('libgfortran', 'GPL-3.0-or-later WITH GCC-exception-3.1'), ('libquadmath', 'LGPL-2.1-or-later')]:
        key = 'component:numpy-linux:' + name.replace('/', '-')
        numpy_terms = project_notices['numpy'] + ([gnu_supplement] if name == 'libquadmath' else [])
        nodes[key] = record(key, name, None, terms, numpy_terms, [], numpy_terms, platforms=['linux'],
                            source_identity={'kind': 'publisher_shipped_numpy_terms_and_native_member_observation',
                                             'component_version_unestablished': True, 'corresponding_source_or_offer_delivered': False})
        nodes['project:numpy@2.5.4']['dependency_ids'].append(key)

    supplement = next(s for s in index['supplements'] if s['name'] == 'ONNX vendored protobuf source grant')
    for name, version, terms in [('abseil-cpp', '20250127.0', 'Apache-2.0'), ('protobuf', '25.1', 'Publisher ONNX NOTICE: Apache-2.0; upstream protobuf source grant: BSD-3-Clause'), ('nanobind', '2.14.0', 'BSD-3-Clause')]:
        key = 'component:ONNX:' + name + '@' + version
        notices = project_notices['onnx'] + ([supplement['path']] if name == 'protobuf' else [])
        nodes[key] = record(key, name, version, terms, notices, [], notices,
                            source_identity={'kind': 'ONNX_publisher_NOTICE_version_declaration_with_supplement_where_present',
                                             'exact_linkage_or_modifications_authenticated': False})
        nodes['project:onnx@1.23.2']['dependency_ids'].append(key)

    ort = next(r for r in index['external_source_records'] if r['name'] == 'notice-sections.json')
    mapping = document(member_bytes(root, ort))
    whole = read(root / mapping['source']['path'])
    need(sha(whole) == mapping['source']['sha256'] and len(whole) == mapping['source']['bytes'] and mapping['section_count'] == 70)
    for section in mapping['sections']:
        start, end = section['start_byte'], section['end_byte']
        need(type(start) is int and type(end) is int and 0 <= start < end <= len(whole)
             and sha(whole[start:end]) == section['sha256'])
        key = 'ORT-notice:' + str(section['ordinal'])
        nodes[key] = record(key, section['heading'], None, None, project_notices['onnxruntime'], [],
                            [ort['path'], *project_notices['onnxruntime']],
                            source_identity={'kind': 'publisher_third_party_notice_section',
                                             'start_byte': start, 'end_byte': end, 'section_sha256': section['sha256'],
                                             'incorporation_established': False, 'component_version_inferred': False})
        nodes['project:onnxruntime@1.31.0']['dependency_ids'].append(key)
    need(len(nodes) <= 3000 and all(set(v['dependency_ids']) <= set(nodes) for v in nodes.values()))
    return {'profile': PROFILE, 'inputs': inputs, 'sources': sorted(sources.values(), key=lambda row: row['path']),
            'packages': [nodes[k] for k in sorted(nodes)],
            'coverage': {'native_wheel_occurrences': 16, 'families': list(FAMILIES),
                         'published_Rust_registry_sources': len(registry), 'published_lock_graphs': 2,
                         'complete_native_dependency_graph': False, 'distribution_source_offer_complete': False},
            'gaps': GAPS, 'claims': CLAIMS}


def verify(root=ROOT, source_cache=None, crate_caches=()):
    root = Path(root)
    deadline = time.monotonic() + 120
    before = {p: sha(read(root / p)) for p in (*BASE_INPUTS, EVIDENCE, *OWN)}
    raw_manifest = read(root / MANIFEST, 16 * 1024**2)
    actual = document(raw_manifest)
    rebuilt = expected(root)
    need(canonical(actual) == canonical(rebuilt))
    replayed = 0
    if source_cache is not None:
        index = document(read(root / EVIDENCE, 16 * 1024**2))
        source_cache = Path(source_cache)
        for item in [*index['source_archives'], *[s for s in index['supplements'] if 'members' in s]]:
            need(time.monotonic() < deadline)
            limit = 21 * 1024**2 if item.get('family') == 'numpy' else MAX_ARCHIVE
            raw = read(source_cache / item['filename'], limit)
            need(len(raw) == item['bytes'] and sha(raw) == item['sha256'])
            extras = [r['member'] for r in item['members']]
            members, _ = archive(raw, extra=extras, limit=limit)
            need(set(members) == {r['member'] for r in item['members']})
            for row in item['members']: need(members[row['member']] == member_bytes(root, row))
            replayed += 1
        for item in index['rust_archives']:
            need(time.monotonic() < deadline)
            choices = [Path(c) / item['filename'] for c in (*crate_caches, source_cache / 'crates')]
            files = [p for p in choices if p.exists()]
            need(files)
            raw = read(files[0], MAX_ARCHIVE)
            need(len(raw) == item['bytes'] and sha(raw) == item['sha256'])
            members, _ = archive(raw, extra=[r['member'] for r in item['members']])
            need(set(members) == {r['member'] for r in item['members']})
            for row in item['members']: need(members[row['member']] == member_bytes(root, row))
            replayed += 1
    need(all(sha(read(root / row['path'])) == row['sha256'] for row in rebuilt['sources']))
    need(read(root / MANIFEST, 16 * 1024**2) == raw_manifest)
    need(time.monotonic() < deadline)
    need(before == {p: sha(read(root / p)) for p in before})
    return {'pass': True, 'profile': PROFILE, 'native_wheel_occurrences': 16,
            'packages': len(rebuilt['packages']), 'dependency_edges': sum(len(p['dependency_ids']) for p in rebuilt['packages']),
            'retained_sources': len(rebuilt['sources']), 'retained_bytes': sum(s['bytes'] for s in rebuilt['sources']),
            'actual_source_archive_replay': source_cache is not None, 'archives_replayed': replayed,
            'native_binary_executed': False, 'permission_cleared': False,
            'complete_native_dependency_graph': False, 'claims': CLAIMS}
