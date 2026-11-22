"""Exact publisher-wheel MCP bundles; format validity never grants release approval.

The caller selects a trusted source checkout, not an archive-selected policy.
No inspected text, service environment, interpreter or installer is bundled.
"""
import base64
import ast
import csv
import functools
from email.parser import BytesParser
import hashlib
import io
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import stat
import struct
import sys
import zipfile
import zlib

from tools.artifact_evidence_io import Capture, OutputCommitUncertain, encoded, identity, snapshot, verify_written
from tools.artifact_process import run_worker

ROOT = Path(__file__).resolve().parents[1]
PROFILE = 'ai-trust-id-mcp-wheel-bundle/v1'
INDEX = 'sbom/mcp-runtime/targets.json'
PROFILE_FILE = 'sbom/mcp-runtime/manifest.json'
INDEX_SHA256 = '882635362b7129b2fa8842d995a211ba85f537e60c548d400c459c8e004390d1'
LOCK_SHA256 = '82375e677571a53a1d3c8b5f13312ae8f81da2a05e4bea0ab59417d4486d95ea'
TARGETS = frozenset(f'cp{v}-{p}' for v in ('312', '313') for p in
                   ('macosx_11_0_arm64', 'linux_x86_64_glibc_2_34'))
MAX_ARCHIVE = 32 * 1024**2
MAX_MEMBER = 16_000_000
MAX_WHEEL_MEMBERS = 4096
MAX_WHEEL_EXPANDED = 64 * 1024**2
MAX_BUNDLE_MEMBERS = 512
STAMP = (1980, 1, 1, 0, 0, 0)
MODE = (stat.S_IFREG | 0o644) << 16
SOURCES = frozenset({
    'tools/tag_api.py', 'scripts/ai-tools-server.py', 'scripts/tag-api.py',
    'scripts/check-tags.py', 'scripts/check-ps.py', 'scripts/worker_process.py',
    'scripts/build-device-detector.py', 'services/evaluator/app.py',
    'protocol/normalization.py', 'protocol/unicode15-data.json',
    'scripts/aitrust.py', 'protocol/assertions.py', 'spec/assertion.schema.json',
    'services/gateway/app.py', 'services/anonymizer/app.py',
    'services/anonymizer/model_identity.py', 'services/anonymizer/requirements.lock',
    'protocol/replay_identity.py', 'services/anonymizer/replay_metadata.py',
    'integrations/mcp/requirements.lock', 'LICENSE', 'NOTICE', 'spec/LICENSE',
    'eval/vectors/unicode/LICENSE.txt', 'docs/mcp-stdio-distribution.md',
    'tools/mcp_distribution.py', 'scripts/mcp-distribution.py',
    'tools/artifact_evidence_io.py', 'tools/artifact_process.py', INDEX,
    'tools/mcp_runtime_obligations.py', 'scripts/collect-mcp-notices.py',
    'tools/mcp_runtime_probe.py',
    'sbom/mcp-runtime/source-inputs.json', 'sbom/mcp-runtime/obligations.json.gz',
    'sbom/mcp-runtime/THIRD-PARTY-NOTICES.txt', 'sbom/mcp-runtime/SCHEMA-ATTRIBUTION.txt',
    'sbom/cffi-libffi/manifest.json', 'sbom/cffi-libffi/LIBFFI-NOTICES.txt',
    'sbom/mcp-rust-stdlib/manifest.json', 'sbom/mcp-rust-stdlib/RUST-STDLIB-NOTICES.txt',
})


class DistributionError(ValueError):
    """Bounded fixed diagnostics contain no input, environment or private path."""


class InstallCapacityUnavailable(DistributionError):
    """Required reserve is unavailable; no private workspace was created."""


def need(condition):
    if not condition:
        raise DistributionError('MCP distribution unavailable.')


def refusal(function):
    @functools.wraps(function)
    def bounded(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except OutputCommitUncertain:
            raise
        except InstallCapacityUnavailable:
            raise
        except (OSError, ValueError, TypeError, KeyError, IndexError, OverflowError,
                RuntimeError, RecursionError, UnicodeError, zipfile.BadZipFile,
                struct.error, zlib.error, csv.Error, SyntaxError):
            raise DistributionError('MCP distribution unavailable.') from None
    return bounded


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return encoded(value) + b'\n'


def unique(pairs):
    result = {}
    for key, value in pairs:
        need(key not in result)
        result[key] = value
    return result


def decode(raw):
    need(type(raw) is bytes and len(raw) <= 4_000_000)
    return json.loads(raw, object_pairs_hook=unique,
                      parse_constant=lambda _: need(False))


def safe(name):
    need(type(name) is str and 0 < len(name) <= 240 and name.isascii()
         and re.fullmatch(r'[A-Za-z0-9_.+\-/]+', name)
         and not name.startswith('/') and all(x not in ('', '.', '..') for x in name.split('/')))
    return name


def index(capture, root):
    raw = capture.read(Path(root) / INDEX, 128_000, private=False)
    need(sha(raw) == INDEX_SHA256)
    value = decode(raw)
    need(set(value['targets']) == TARGETS)
    lock = capture.read(Path(root) / 'integrations/mcp/requirements.lock', 128_000, private=False)
    need(sha(lock) == LOCK_SHA256)
    blocks = re.split(r'(?m)^(?=[a-zA-Z0-9_-]+==)', lock.decode('ascii'))
    by_name = {re.match(r'([a-zA-Z0-9_-]+)==', x)[1]: x for x in blocks
               if re.match(r'([a-zA-Z0-9_-]+)==', x)}
    wheels = {}
    for target, rows in value['targets'].items():
        need(type(rows) is list and len(rows) == 30 and len({x['name'] for x in rows}) == 30)
        for row in rows:
            safe(row['filename'])
            need('/' not in row['filename'] and row['sha256'] in by_name[row['name']]
                 and type(row['bytes']) is int and 0 < row['bytes'] < MAX_MEMBER)
            if row['filename'] in wheels:
                need(wheels[row['filename']] == row)
            wheels[row['filename']] = row
    need(len(wheels) == 40 and sum(x['bytes'] for x in wheels.values()) == 21_811_126)
    return value, wheels


def preflight(raw, *, count_limit=MAX_WHEEL_MEMBERS, expanded_limit=MAX_WHEEL_EXPANDED):
    """Bound central-directory allocation and raw identities BEFORE ZipFile."""
    need(type(raw) is bytes and 22 <= len(raw) <= MAX_ARCHIVE)
    end = len(raw) - 22
    need(raw[end:end+4] == b'PK\x05\x06')
    disk, cd_disk, count_disk, count, size, offset, comment = struct.unpack_from('<4H2IH', raw, end+4)
    need(disk == cd_disk == comment == 0 and count == count_disk and
         0 < count <= count_limit and offset + size == end and size <= 2_000_000)
    cursor = offset
    names = []
    expanded = 0
    spans = []
    for _ in range(count):
        need(cursor + 46 <= end and raw[cursor:cursor+4] == b'PK\x01\x02')
        flags, method = struct.unpack_from('<HH', raw, cursor+8)
        compressed, uncompressed = struct.unpack_from('<II', raw, cursor+20)
        nlen, extra, note, volume = struct.unpack_from('<4H', raw, cursor+28)
        local = struct.unpack_from('<I', raw, cursor+42)[0]
        need(flags == 0 and method in (0, 8) and volume == 0 and
             compressed != 0xffffffff and uncompressed <= MAX_MEMBER and
             local + 30 <= offset and cursor + 46+nlen+extra+note <= end)
        name = raw[cursor+46:cursor+46+nlen].decode('ascii')
        need('\0' not in name)
        safe(name[:-1] if name.endswith('/') else name)
        need(name not in names)
        names.append(name)
        need(raw[local:local+4] == b'PK\x03\x04')
        lflags, lmethod = struct.unpack_from('<HH', raw, local+6)
        lsize, lraw = struct.unpack_from('<II', raw, local+18)
        ln, le = struct.unpack_from('<HH', raw, local+26)
        need(lflags == flags and lmethod == method and
             raw[local+30:local+30+ln] == name.encode('ascii') and
             ln == nlen and lsize == compressed and lraw == uncompressed)
        start, finish = local, local+30+ln+le+compressed
        need(finish <= offset)
        spans.append((start, finish))
        expanded += uncompressed
        need(expanded <= expanded_limit)
        cursor += 46+nlen+extra+note
    need(cursor == end and len(names) == len(set(names)))
    ordered = sorted(spans)
    need(ordered[0][0] == 0 and all(a[1] == b[0] for a, b in zip(ordered, ordered[1:]))
         and ordered[-1][1] == offset)
    return names


def publisher_graph(content, member, scope):
    """Canonical sanitized projection; raw publisher paths never become IDs."""
    raw = content[member]
    data = decode(raw)
    refs = {}
    components = {}
    source_roots = {'cryptography': 'cryptography@50.0.2',
                    'pydantic-core': 'pydantic-core@2.50.4', 'rpds-py': 'rpds-py@2026.9.1'}
    def walk(component, depth=0):
        need(depth <= 8 and type(component) is dict)
        if not component:
            return
        name, version = component['name'], component.get('version')
        need(type(name) is str and len(name) <= 200 and name.isascii() and
             re.fullmatch('[A-Za-z0-9_.+ -]+', name) and
             (version is None or type(version) is str and len(version) <= 100))
        purl = component.get('purl', '')
        registry = purl.startswith('pkg:cargo/') and 'download_url=file:' not in purl
        if registry or name == 'openssl':
            key = name+'@'+version
            source_root = key
        else:
            key = 'local:'+scope+':'+name+'@'+(version or 'unspecified')
            source_root = source_roots.get(scope)
        if 'bom-ref' in component:
            need(component['bom-ref'] not in refs)
            refs[component['bom-ref']] = key
        hashes = [x['content'] for x in component.get('hashes', []) if x.get('alg') == 'SHA-256']
        need(len(hashes) <= 1 and all(type(x) is str and re.fullmatch('[0-9a-f]{64}', x) for x in hashes))
        row = {'id': key, 'name': name, 'version': version, 'source_root_id': source_root,
               'licenses_declared': component.get('licenses', []),
               'source_archive_sha256': hashes[0] if hashes else None}
        if key in components:
            need(components[key] == row)
        components[key] = row
        need(len(components) <= 512 and len(encoded(row)) <= 16_000)
        for child in component.get('components', []):
            walk(child, depth+1)
    walk(data.get('metadata', {}).get('component', {}))
    for component in data.get('components', []):
        walk(component)
    edges = set()
    for dependency in data.get('dependencies', []):
        need(dependency['ref'] in refs)
        for target in dependency.get('dependsOn', []):
            need(target in refs)
            edges.add((refs[dependency['ref']], refs[target]))
            need(len(edges) <= 4096)
    return {'member': member, 'sha256': sha(raw),
            'components': [components[k] for k in sorted(components)],
            'dependency_edges': [list(x) for x in sorted(edges)],
            'role': 'wheel-bound publisher declaration, not exhaustive compiled inventory'}


def release_version(value):
    need(type(value) is str and len(value) <= 80 and re.fullmatch(r'[0-9]+(?:\.[0-9]+)*', value))
    parts = tuple(map(int, value.split('.')))
    need(len(parts) <= 8)
    return parts+(0,)*(8-len(parts))


def marker_matches(marker, environment):
    """Finite reviewed PEP508 marker subset; parse structure, never eval/exec."""
    need(type(marker) is str and len(marker) <= 512)
    tree = ast.parse(marker, mode='eval')
    need(len(list(ast.walk(tree))) <= 80)
    def value(node):
        if isinstance(node, ast.Name):
            need(node.id in environment)
            return environment[node.id], node.id
        need(isinstance(node, ast.Constant) and type(node.value) is str and len(node.value) <= 80)
        return node.value, None
    def walk(node):
        if isinstance(node, ast.BoolOp):
            need(isinstance(node.op, (ast.And, ast.Or)) and 1 < len(node.values) <= 16)
            values = [walk(x) for x in node.values]
            return all(values) if isinstance(node.op, ast.And) else any(values)
        need(isinstance(node, ast.Compare) and len(node.ops) == len(node.comparators) == 1)
        left, ln = value(node.left)
        right, rn = value(node.comparators[0])
        if ln in ('python_version', 'python_full_version') or rn in ('python_version', 'python_full_version'):
            left, right = release_version(left), release_version(right)
        op = node.ops[0]
        need(isinstance(op, (ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE)))
        if isinstance(op, ast.Eq): return left == right
        if isinstance(op, ast.NotEq): return left != right
        if isinstance(op, ast.Lt): return left < right
        if isinstance(op, ast.LtE): return left <= right
        if isinstance(op, ast.Gt): return left > right
        return left >= right
    return walk(tree.body)


def requirement_parts(text):
    need(type(text) is str and len(text) <= 512 and text.count(';') <= 1)
    spec, _, marker = text.partition(';')
    found = re.fullmatch(r'\s*([A-Za-z0-9][A-Za-z0-9_.-]*)(?:\[([A-Za-z0-9_,.-]+)\])?\s*(.*?)\s*', spec)
    need(found is not None)
    name = re.sub('[-_.]+', '-', found[1]).lower()
    extras = [] if found[2] is None else sorted(set(found[2].split(',')))
    need(len(extras) <= 16)
    constraint = found[3].strip()
    if constraint.startswith('('):
        need(constraint.endswith(')'))
        constraint = constraint[1:-1].strip()
    constraints = []
    for item in constraint.split(',') if constraint else []:
        match = re.fullmatch(r'\s*(==|!=|>=|<=|>|<)\s*([0-9]+(?:\.[0-9]+)*(?:\.\*)?)\s*', item)
        need(match is not None and (not match[2].endswith('.*') or match[1] in ('==', '!=')))
        constraints.append((match[1], match[2]))
    return name, extras, constraints, marker.strip()


def version_satisfies(version, constraints):
    selected = release_version(version)
    for op, value in constraints:
        if value.endswith('.*'):
            prefix = tuple(map(int, value[:-2].split('.')))
            matches = selected[:len(prefix)] == prefix
            if (not matches if op == '==' else matches): return False
        else:
            bound = release_version(value)
            if not {'==': selected == bound, '!=': selected != bound, '>=': selected >= bound,
                    '<=': selected <= bound, '>': selected > bound, '<': selected < bound}[op]: return False
    return True


@refusal
def dependency_graph(target, selected, records):
    """Exact finite artifact extras/markers; not a general pip replacement."""
    need(target in TARGETS and len(selected) == 30)
    packages = {x['name']: x for x in selected}
    need(len(packages) == 30)
    by_file = {x['filename']: x for x in records}
    by_name = {x['name']: by_file[x['filename']] for x in selected}
    py = '3.12' if target.startswith('cp312-') else '3.13'
    mac = 'macosx' in target
    base = {'python_version': py, 'python_full_version': py+'.0', 'extra': '',
            'sys_platform': 'darwin' if mac else 'linux', 'platform_system': 'Darwin' if mac else 'Linux',
            'platform_python_implementation': 'CPython', 'implementation_name': 'cpython'}
    extras = {name: set() for name in packages}
    edges = set()
    for _ in range(32):
        changed = False
        for owner in sorted(packages):
            need(owner in by_name and len(by_name[owner]['requires_dist']) <= 128)
            for text in by_name[owner]['requires_dist']:
                name, requested, constraints, marker = requirement_parts(text)
                active = not marker or any(marker_matches(marker, {**base, 'extra': x}) for x in ['', *sorted(extras[owner])])
                if not active: continue
                need(name in packages and version_satisfies(packages[name]['version'], constraints))
                edges.add((owner, name))
                before = len(extras[name])
                extras[name].update(requested)
                need(len(extras[name]) <= 16)
                changed |= len(extras[name]) != before
        if not changed: break
    else:
        need(False)
    reachable = {'mcp', 'jsonschema', 'rfc3339-validator'}
    for _ in range(30):
        following = reachable | {b for a, b in edges if a in reachable}
        if following == reachable: break
        reachable = following
    need(reachable == set(packages))
    return {'roots': ['jsonschema', 'mcp', 'rfc3339-validator'],
            'edges': [list(x) for x in sorted(edges)],
            'selected_extras': {k: sorted(v) for k, v in sorted(extras.items()) if v}}


@refusal
def wheel(raw, expected):
    """Inspect only exact trusted wheel bytes; execute no package source."""
    need(len(raw) == expected['bytes'] and sha(raw) == expected['sha256'])
    names = preflight(raw)
    records = []
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        infos = z.infolist()
        need([x.filename for x in infos] == names)
        content = {}
        for info in infos:
            need(info.orig_filename == info.filename and
                 stat.S_IFMT(info.external_attr >> 16) in (0, stat.S_IFREG, stat.S_IFDIR))
            data = z.read(info)
            need(len(data) == info.file_size)
            if info.is_dir():
                need(not data)
            else:
                content[info.filename] = data
                records.append({'path': info.filename, 'bytes': len(data), 'sha256': sha(data)})
        roots = {n.split('/')[0] for n in content if '.dist-info/' in n}
        need(len(roots) == 1)
        dist = roots.pop()
        metadata = BytesParser().parsebytes(content[dist+'/METADATA'])
        norm = lambda s: re.sub('[-_.]+', '-', s).lower()
        need(norm(metadata['Name']) == norm(expected['name']) and metadata['Version'] == expected['version'])
        wm = BytesParser().parsebytes(content[dist+'/WHEEL'])
        need(wm['Wheel-Version'] == '1.0')
        record_name = dist+'/RECORD'
        rows = list(csv.reader(io.StringIO(content[record_name].decode('utf-8'))))
        need(len(rows) <= MAX_WHEEL_MEMBERS and all(len(x) == 3 for x in rows))
        seen = set()
        for name, hashed, size in rows:
            safe(name)
            need(name not in seen and name in content)
            seen.add(name)
            if name == record_name:
                need(hashed == size == '')
            else:
                need(hashed.startswith('sha256=') and size == str(len(content[name])) and
                     hashed[7:] == base64.urlsafe_b64encode(hashlib.sha256(content[name]).digest()).decode().rstrip('='))
        need(seen == set(content))
        notice_names = sorted(n for n in content if any(v in n.rsplit('/', 1)[-1].lower()
                              for v in ('license', 'notice', 'copying', 'authors')))
        need(notice_names)
        sboms = sorted(n for n in content if n.startswith(dist+'/sboms/'))
        # The member hashes bind raw publisher SBOMs, including publisher paths;
        # no raw metadata or publisher build paths are printed by the CLI.
        return {'filename': expected['filename'], 'name': expected['name'],
                'version': expected['version'], 'sha256': sha(raw), 'bytes': len(raw),
                'requires_python': metadata['Requires-Python'],
                'requires_dist': metadata.get_all('Requires-Dist', []),
                'license_declared': metadata['License-Expression'] or metadata['License'],
                'members': sorted(records, key=lambda x: x['path']),
                'notice_members': notice_names, 'publisher_sbom_members': sboms,
                'publisher_graphs': [publisher_graph(content, name, norm(expected['name'])) for name in sboms],
                'rust_runtime_observations': [
                    {'member': name, 'native_sha256': sha(content[name]),
                     'source_commits': sorted({x.decode('ascii') for x in
                         re.findall(rb'/rustc/([a-f0-9]{40})/(?:library|compiler)/', content[name])})}
                    for name in sorted(content) if name.endswith(('.so', '.dylib', '.dll', '.pyd'))],
                'native_members': sorted(n for n in content if n.endswith(('.so', '.dylib', '.dll', '.pyd')))}


@refusal
def collect(root, wheelhouse):
    """Authoring operation: exact input inventory, never an admission decision."""
    root = Path(root).absolute()
    with Capture() as capture:
        targets, expected = index(capture, root)
        files = []
        for name in sorted(SOURCES):
            raw = capture.read(root/name, MAX_MEMBER, private=False)
            files.append({'path': name, 'sha256': sha(raw), 'bytes': len(raw)})
        wheels = []
        for name, row in sorted(expected.items()):
            raw = capture.read(Path(wheelhouse)/name, MAX_MEMBER)
            wheels.append(wheel(raw, row))
        evidence, _ = supplement_evidence(root)
        capture.check()
    dependencies = {target: dependency_graph(target, rows, wheels) for target, rows in targets['targets'].items()}
    return {'profile': PROFILE, 'route': 'mcp-stdio', 'targets': targets['targets'], 'dependencies': dependencies,
            'files': files, 'evidence_files': evidence, 'wheels': wheels, 'source_only': False,
            'interpreter_bundled': False, 'installer_bundled': False,
            'native_obligations_complete': False, 'distribution_approved': False,
            'independent_accuracy_evidence': False}


def load(capture, root):
    raw = capture.read(Path(root)/PROFILE_FILE, 4_000_000, private=False)
    value = decode(raw)
    need(type(value) is dict and set(value) == {'profile', 'route', 'targets', 'dependencies', 'files', 'evidence_files', 'wheels',
         'source_only', 'interpreter_bundled', 'installer_bundled', 'native_obligations_complete',
         'distribution_approved', 'independent_accuracy_evidence'})
    need(value['profile'] == PROFILE and value['route'] == 'mcp-stdio' and
         all(value[x] is False for x in ('source_only', 'interpreter_bundled', 'installer_bundled',
             'native_obligations_complete', 'distribution_approved', 'independent_accuracy_evidence')))
    target_index, expected = index(capture, root)
    need(value['targets'] == target_index['targets'] and type(value['files']) is list and
         {x['path'] for x in value['files']} == SOURCES and len(value['files']) == len(SOURCES))
    need(type(value['wheels']) is list and len(value['wheels']) == 40 and
         {x['filename'] for x in value['wheels']} == set(expected))
    need(value['dependencies'] == {target: dependency_graph(target, rows, value['wheels'])
                                  for target, rows in value['targets'].items()})
    for row in value['files']:
        need(set(row) == {'path', 'sha256', 'bytes'} and type(row['bytes']) is int)
        data = capture.read(Path(root)/row['path'], MAX_MEMBER, private=False)
        need(len(data) == row['bytes'] and sha(data) == row['sha256'])
    need(value['evidence_files'] == supplement_evidence(root)[0])
    validate_obligations(capture, root, value)
    return raw, value


def validate_obligations(capture, root, profile):
    from tools.mcp_runtime_obligations import INPUTS_SHA256
    source_raw = capture.read(Path(root)/'sbom/mcp-runtime/source-inputs.json', 256_000, private=False)
    need(sha(source_raw) == INPUTS_SHA256)
    inputs = decode(source_raw)
    source = {x['id']: x for x in inputs['packages']}
    data = read_obligations(capture, root)
    need(data['profile'] == 'mcp-runtime-obligation-map/v1' and data['source_inputs_sha256'] == INPUTS_SHA256)
    need(data['claims'] == {'distribution_approved': False, 'complete_compiled_closure': False,
                           'license_clearance': False, 'complete_project_obligations': False} and
         all(type(x) is bool for x in data['claims'].values()))
    asset = data['notice_asset']
    need(asset['path'] == 'sbom/mcp-runtime/THIRD-PARTY-NOTICES.txt')
    raw = capture.read(Path(root)/asset['path'], 8_000_000, private=False)
    need(type(asset['bytes']) is int and sha(raw) == asset['sha256'] and len(raw) == asset['bytes'] and
         type(asset['members']) is list and 0 < len(asset['members']) <= 5000)
    hashes = set()
    last = 0
    for row in asset['members']:
        need(set(row) == {'sha256', 'offset', 'bytes'} and
             type(row['offset']) is int and type(row['bytes']) is int and
             last <= row['offset'] < row['offset']+row['bytes'] <= len(raw) and
             row['sha256'] not in hashes and sha(raw[row['offset']:row['offset']+row['bytes']]) == row['sha256'])
        last = row['offset']+row['bytes']
        hashes.add(row['sha256'])
    need(type(data['source_packages']) is list and len(data['source_packages']) == len(source) == 150)
    seen = set()
    for row in data['source_packages']:
        need(row['id'] in source and row['id'] not in seen)
        seen.add(row['id'])
        expected = source[row['id']]
        need(type(row['archive_bytes']) is int and row['archive_sha256'] == expected['sha256'] and row['archive_bytes'] == expected['bytes'] and
             row['source_offer_required_under_selected_grant'] is False and row['complete_compiled_closure'] is False and
             type(row['selected_grant']) is str and bool(row['notice_sha256']) and
             set(row['notice_sha256']) <= hashes)
    expected_graphs = sorted([{'wheel': w['filename'], **g} for w in profile['wheels']
                              for g in w['publisher_graphs']], key=lambda g: (g['wheel'], g['member']))
    need(data['publisher_graphs'] == expected_graphs)
    ffi_raw = capture.read(Path(root)/'sbom/cffi-libffi/LIBFFI-NOTICES.txt', 128_000, private=False)
    need(sha(ffi_raw) == data['libffi_evidence']['notice_sha256'] ==
         '2fe3318a85b19fea32d1e5801e7406a7868dc9768f0637c1838821fc1ece7386' and sha(ffi_raw) in hashes)
    ffi_map = capture.read(Path(root)/'sbom/cffi-libffi/manifest.json', 128_000, private=False)
    need(sha(ffi_map) == data['libffi_evidence']['manifest_sha256'] ==
         '4e9b49cfff92b2f0aa117a95f0c852b5ff0dde9a75636308aaa79269a7135dc8')
    rust = capture.read(Path(root)/'sbom/mcp-rust-stdlib/RUST-STDLIB-NOTICES.txt', 256_000, private=False)
    need(sha(rust) == 'dfe5411072f6745ae8a41d4d5a00ab834551173360b3e93d2dd5ed7cd486cf90' and
         sha(rust) in hashes)
    rust_raw = capture.read(Path(root)/'sbom/mcp-rust-stdlib/manifest.json', 256_000, private=False)
    need(sha(rust_raw) == data['rust_stdlib_evidence']['manifest_sha256'] ==
         '47328f3158803a8f1271194c7cc94976ca2de3c6f3f060a89dbac2aafbde2857')
    rust_map = decode(rust_raw)
    wheel_rows = {x['filename']: x for x in profile['wheels']}
    expected_rust = []
    for name, wheel_row in wheel_rows.items():
        for observed in wheel_row['rust_runtime_observations']:
            if observed['source_commits']:
                expected_rust.append({'wheel': name, 'wheel_sha256': wheel_row['sha256'],
                    'native_member': observed['member'], 'native_sha256': observed['native_sha256'],
                    'rust_commits': observed['source_commits']})
    need(len(expected_rust) == 10 and sorted(expected_rust, key=lambda x: x['wheel']) ==
         sorted(rust_map['artifact_bindings'], key=lambda x: x['wheel']) and
         data['rust_stdlib_evidence']['applies_to_wheel_sha256'] == sorted(x['wheel_sha256'] for x in expected_rust))
    return data


@refusal
def decode_obligations(raw):
    """One fixed gzip member; bound expansion before JSON allocation/validation."""
    need(type(raw) is bytes and 18 <= len(raw) <= 2_000_000 and
         raw[:10] == bytes.fromhex('1f8b08000000000002ff'))
    stream = zlib.decompressobj(31)
    expanded = stream.decompress(raw, 4_000_001)
    need(len(expanded) <= 4_000_000 and stream.eof and
         not stream.unused_data and not stream.unconsumed_tail)
    need(sha(expanded) == 'c26b2f4503739275a5f6d8f7686de052a5de065d3016f51293185fcc25cb6675')
    return decode(expanded)


def read_obligations(capture, root):
    return decode_obligations(capture.read(Path(root)/'sbom/mcp-runtime/obligations.json.gz',
                                          2_000_000, private=False))


def supplement_evidence(root):
    """Verify/close bounded raw evidence sequentially, without dropping inputs.

    Fixed manifest roots and every payload hash are independently pinned. The
    complete small collateral also ships, so installed auditing tools remain
    usable without an SDK/source cache or missing repository-relative files.
    """
    specs = [('sbom/cffi-libffi/', '4e9b49cfff92b2f0aa117a95f0c852b5ff0dde9a75636308aaa79269a7135dc8', 36),
             ('sbom/mcp-rust-stdlib/', '47328f3158803a8f1271194c7cc94976ca2de3c6f3f060a89dbac2aafbde2857', 357)]
    rows = []
    members = {}
    total = 0
    for prefix, expected, count in specs:
        with Capture() as captured:
            raw = captured.read(Path(root)/(prefix+'manifest.json'), 256_000, private=False)
            need(sha(raw) == expected)
            manifest = decode(raw)
            need(type(manifest['inputs']) is dict and len(manifest['inputs']) == count)
            for name, digest in sorted(manifest['inputs'].items()):
                safe(name)
                need(name.startswith(prefix) and name not in members and
                     type(digest) is str and re.fullmatch('[0-9a-f]{64}', digest))
                # Keep source parent identities anchored while closing each
                # payload descriptor; never retain hundreds of source files.
                captured.parent(Path(root)/name, private=False)
                need(len(captured.fds) <= 120)
                with Capture() as source:
                    value = source.read(Path(root)/name, 2_000_000, private=False)
                    need(sha(value) == digest)
                    source.check()
                total += len(value)
                need(total <= 8_000_000)
                members[name] = value
                rows.append({'path': name, 'bytes': len(value), 'sha256': digest})
            captured.check()
    return sorted(rows, key=lambda x: x['path']), members


@refusal
def inspect_profile(root=ROOT):
    """No wheel cache/SDK needed; reports source validity, never admission."""
    with Capture() as capture:
        raw, value = load(capture, root)
        capture.check()
    return {'profile': PROFILE, 'profile_sha256': sha(raw), 'target_count': 4,
            'unique_wheel_count': 40, 'wheels_per_target': 30,
            'source_inputs_verified': True, 'release_authorized': False}


def assemble(members):
    out = io.BytesIO()
    need(len(members) <= MAX_BUNDLE_MEMBERS and sum(len(x) for x in members.values()) <= MAX_ARCHIVE-100_000)
    with zipfile.ZipFile(out, 'w', compression=zipfile.ZIP_STORED, allowZip64=False) as z:
        for name, raw in sorted(members.items()):
            safe(name)
            item = zipfile.ZipInfo(name, STAMP)
            item.create_system = 3
            item.external_attr = MODE
            item.compress_type = zipfile.ZIP_STORED
            z.writestr(item, raw)
    result = out.getvalue()
    need(len(result) <= MAX_ARCHIVE)
    return result


def expected_members(capture, root, target, profile_raw, profile):
    need(target in TARGETS)
    members = {'project/'+x['path']: capture.read(Path(root)/x['path'], MAX_MEMBER, private=False)
               for x in profile['files']}
    members['project/'+PROFILE_FILE] = profile_raw
    evidence, payload = supplement_evidence(root)
    need(evidence == profile['evidence_files'])
    members.update({'project/'+name: raw for name, raw in payload.items()})
    rows = profile['targets'][target]
    requirements = ''.join(f"{x['name']}=={x['version']} --hash=sha256:{x['sha256']}\n" for x in rows).encode('ascii')
    members['requirements-selected.txt'] = requirements
    members['.aitrust-mcp.json'] = canonical({'profile': PROFILE, 'route': 'mcp-stdio',
        'target': target, 'profile_sha256': sha(profile_raw), 'wheels': rows,
        'format_validity_is_release_approval': False})
    return members


@refusal
def build(root=ROOT, *, target, wheelhouse):
    with Capture() as capture:
        profile_raw, profile = load(capture, root)
        members = expected_members(capture, root, target, profile_raw, profile)
        indexed = {x['filename']: x for x in profile['wheels']}
        for row in profile['targets'][target]:
            raw = capture.read(Path(wheelhouse)/row['filename'], MAX_MEMBER)
            need(wheel(raw, row) == indexed[row['filename']])
            members['wheels/'+row['filename']] = raw
        raw = assemble(members)
        capture.check()
    return raw


@refusal
def verify(raw, root=ROOT):
    names = preflight(raw, count_limit=MAX_BUNDLE_MEMBERS, expanded_limit=MAX_ARCHIVE)
    with Capture() as capture:
        profile_raw, profile = load(capture, root)
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            members = {}
            for info in z.infolist():
                need(info.orig_filename == info.filename and not info.is_dir() and
                     info.create_system == 3 and info.external_attr == MODE and
                     info.date_time == STAMP and not info.extra and not info.comment and
                     info.flag_bits == 0 and info.compress_type == zipfile.ZIP_STORED)
                members[info.filename] = z.read(info)
        need(set(members) == set(names) and '.aitrust-mcp.json' in members)
        meta = decode(members['.aitrust-mcp.json'])
        target = meta['target']
        expected = expected_members(capture, root, target, profile_raw, profile)
        selected = profile['targets'][target]
        need(set(members) == set(expected) | {'wheels/'+x['filename'] for x in selected})
        need(all(members[k] == v for k, v in expected.items()))
        indexed = {x['filename']: x for x in profile['wheels']}
        for row in selected:
            need(wheel(members['wheels/'+row['filename']], row) == indexed[row['filename']])
        need(raw == assemble(members))
        capture.check()
    return {'profile': PROFILE, 'pass': True, 'target': target, 'sha256': sha(raw),
            'profile_sha256': sha(profile_raw),
            'bytes': len(raw), 'member_count': len(members), 'wheel_count': 30,
            'format_verified': True, 'release_authorized': False,
            'native_obligations_complete': False}, members


def publish_bytes(capture, output, raw, before_link):
    """Complete private file, atomic no-replace link, truthful uncertainty."""
    need(len(raw) <= MAX_ARCHIVE and not Path(output).absolute().is_relative_to(ROOT))
    parent, name = capture.parent(output)
    try:
        os.stat(name, dir_fd=parent, follow_symlinks=False)
    except FileNotFoundError:
        pass
    else:
        raise DistributionError('MCP distribution unavailable.')
    temp = '.mcp-bundle-'+secrets.token_hex(16)
    fd = os.open(temp, os.O_RDWR|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW, 0o600, dir_fd=parent)
    capture.fds.append(fd)
    error = None
    try:
        with os.fdopen(fd, 'wb', closefd=False) as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(fd)
        verify_written(fd, raw)
        before_link()
        capture.check()
        try:
            os.link(temp, name, src_dir_fd=parent, dst_dir_fd=parent, follow_symlinks=False)
        except FileExistsError:
            raise
        except BaseException:
            capture.output_may_exist = True
            raise
        capture.output_may_exist = True
    except BaseException as failure:
        error = failure
    try:
        os.unlink(temp, dir_fd=parent)
    except BaseException as failure:
        if error is None:
            error = failure
    if error is None:
        try:
            os.fsync(parent)
            need(identity(os.fstat(fd)) == identity(os.stat(name, dir_fd=parent, follow_symlinks=False)))
            verify_written(fd, raw)
            capture.check()
        except BaseException as failure:
            error = failure
    if error is not None:
        if capture.output_may_exist:
            raise OutputCommitUncertain() from None
        raise error


@refusal
def export(output, root=ROOT, *, target, wheelhouse):
    raw = build(root, target=target, wheelhouse=wheelhouse)
    result, _ = verify(raw, root)
    with Capture() as capture:
        publish_bytes(capture, output, raw, lambda: verify(raw, root))
    return result


@refusal
def verify_file(path, root=ROOT):
    with Capture() as capture:
        buf = io.BytesIO()
        capture.artifact(path, MAX_ARCHIVE, copy_to=buf)
        result, _ = verify(buf.getvalue(), root)
        capture.check()
    return result


def target_for_runtime(row):
    need(type(row) is dict and set(row) == {'implementation', 'version', 'platform', 'machine', 'libc', 'macos',
                                          'gil_disabled', 'pointer_bits'})
    need(row['implementation'] == 'CPython' and type(row['version']) is list and
         len(row['version']) == 2 and all(type(x) is int for x in row['version']) and
         row['version'] in ([3, 12], [3, 13]) and row['gil_disabled'] is False and
         type(row['pointer_bits']) is int and row['pointer_bits'] == 64)
    prefix = 'cp'+''.join(str(x) for x in row['version'])
    if row['platform'] == 'darwin':
        need(row['machine'] == 'arm64' and type(row['macos']) is str and
             re.fullmatch(r'\d{1,2}(?:\.\d{1,2}){0,2}', row['macos']) and int(row['macos'].split('.')[0]) >= 11)
        return prefix+'-macosx_11_0_arm64'
    need(row['platform'] == 'linux' and row['machine'] == 'x86_64' and
         type(row['libc']) is list and len(row['libc']) == 2 and row['libc'][0] == 'glibc' and
         type(row['libc'][1]) is str and re.fullmatch(r'\d{1,2}\.\d{1,2}', row['libc'][1]) and
         tuple(map(int, row['libc'][1].split('.'))) >= (2, 34))
    return prefix+'-linux_x86_64_glibc_2_34'


RUNTIME_PROBE = """import json,platform,struct,sys,sysconfig
print(json.dumps({'implementation':platform.python_implementation(),'version':list(sys.version_info[:2]),'platform':sys.platform,'machine':platform.machine(),'libc':list(platform.libc_ver()),'macos':platform.mac_ver()[0],'gil_disabled':bool(sysconfig.get_config_var('Py_GIL_DISABLED')),'pointer_bits':struct.calcsize('P')*8}))
"""


def command(argv, *, task_directory, timeout=60, output_limit=128_000):
    # No shell, inherited service credentials, proxy settings, user site or pip
    # configuration. The env process is in the same owned bounded process group.
    preserved_home = ['HOME='+os.environ['HOME']] if 'HOME' in os.environ else []
    fixed = ['/usr/bin/env', '-i', *preserved_home, 'TMPDIR='+str(Path(task_directory)/'tmp'),
             'PATH=/usr/bin:/bin', 'PIP_CONFIG_FILE=/dev/null',
             'PIP_DISABLE_PIP_VERSION_CHECK=1', 'PYTHONDONTWRITEBYTECODE=1', *argv]
    result = run_worker(fixed, input=b'', timeout=timeout, output_limit=output_limit)
    need(result.returncode == 0)
    return result.stdout


@refusal
def materialize(workspace_fd, members):
    """No extraction API, path-following mkdir, raw-fd leak or silent short write."""
    need(len(members) <= MAX_BUNDLE_MEMBERS)
    with Capture() as directories:
        root = os.dup(workspace_fd)
        directories.fds.append(root)
        known = {(): root}
        for name, raw in sorted(members.items()):
            parts = safe(name).split('/')
            parent = root
            key = ()
            for part in parts[:-1]:
                key = (*key, part)
                if key not in known:
                    try:
                        os.mkdir(part, 0o700, dir_fd=parent)
                    except FileExistsError:
                        pass
                    child = os.open(part, os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_NONBLOCK, dir_fd=parent)
                    directories.fds.append(child)
                    need(len(directories.fds) <= 128)
                    directories.directories.append((parent, part, child, identity(os.fstat(child))))
                    known[key] = child
                parent = known[key]
            with Capture() as file:
                fd = os.open(parts[-1], os.O_RDWR|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW, 0o600, dir_fd=parent)
                file.fds.append(fd)
                with os.fdopen(fd, 'wb', closefd=False) as stream:
                    need(stream.write(raw) == len(raw))
                    stream.flush()
                    os.fsync(fd)
                verify_written(fd, raw)
            directories.check()


def verify_materialized(workspace, members):
    for name, expected in sorted(members.items()):
        with Capture() as source:
            raw = source.read(Path(workspace)/name, MAX_MEMBER, private=False)
            need(raw == expected)
            source.check()


def read_payload(capture, path, expected_size):
    if expected_size:
        return capture.read(path, MAX_MEMBER, private=False)
    parent, name = capture.parent(path, private=False)
    fd = os.open(name, os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK, dir_fd=parent)
    capture.fds.append(fd)
    info = os.fstat(fd)
    need(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_size == 0 and not os.read(fd, 1))
    capture.files.append((parent, name, fd, snapshot(info)))
    return b''


def verify_runtime_files(workspace, target, profile):
    """Hash all executable/data wheel payloads; labels alone are not identity."""
    version = '3.12' if target.startswith('cp312-') else '3.13'
    site = Path(workspace)/'venv/lib'/('python'+version)/'site-packages'
    indexed = {w['filename']: w for w in profile['wheels']}
    payloads = {}
    generated = set()
    for wheel_row in profile['targets'][target]:
        wheel_record = indexed[wheel_row['filename']]
        roots = set()
        for row in wheel_record['members']:
            path = safe(row['path'])
            need('.data/' not in path and not path.endswith('.pth'))
            if '.dist-info/' in path:
                roots.add(path.split('/')[0])
            if path.endswith('.dist-info/RECORD'):
                continue
            need(path not in payloads or payloads[path] == row)
            payloads[path] = row
        need(len(roots) == 1)
        dist = roots.pop()
        generated.update(dist+'/'+name for name in ('RECORD', 'INSTALLER', 'REQUESTED', 'direct_url.json'))
    need(len(payloads) <= 4096)
    allowed = set(payloads) | generated
    directories = {str(Path(name).parent) for name in allowed}
    directories |= {str(parent) for name in allowed for parent in Path(name).parents if str(parent) != '.'}
    observed = set()
    with Capture() as anchor:
        anchor.parent(site/'.scope', private=False)
        for parent, dirs, files in os.walk(site, followlinks=False):
            for name in [*dirs, *files]:
                path = Path(parent)/name
                info = path.lstat()
                need(not stat.S_ISLNK(info.st_mode))
                relative = path.relative_to(site).as_posix()
                if stat.S_ISDIR(info.st_mode):
                    need(relative in directories)
                else:
                    need(stat.S_ISREG(info.st_mode) and relative in allowed)
                    observed.add(relative)
                    need(len(observed) <= 5000)
        need(set(payloads) <= observed)
        for name, row in sorted(payloads.items()):
            with Capture() as source:
                raw = read_payload(source, site/name, row['bytes'])
                need(len(raw) == row['bytes'] and sha(raw) == row['sha256'])
                source.check()
        anchor.check()
    return len(payloads)


@refusal
def install(archive, output, *, python=sys.executable, pip_python, root=ROOT):
    """Private owned install plus explicit launch JSON; never release admission.

    A failed prepublication attempt may leave private temporary bytes when the
    filesystem refuses cleanup. No existing destination/workspace is removed.
    """
    need(Path(python).is_absolute() and Path(pip_python).is_absolute())
    with Capture() as capture:
        buf = io.BytesIO()
        capture.artifact(archive, MAX_ARCHIVE, copy_to=buf)
        raw = buf.getvalue()
        result, members = verify(raw, root)
        parent, name = capture.parent(output)
        try:
            os.stat(name, dir_fd=parent, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise DistributionError('MCP distribution unavailable.')
        if shutil.disk_usage(Path(output).absolute().parent).free < 2*1024**3+128*1024**2:
            raise InstallCapacityUnavailable('MCP private installation capacity unavailable.')
        workspace_name = '.mcp-install-'+secrets.token_hex(16)
        os.mkdir(workspace_name, 0o700, dir_fd=parent)
        workspace = Path(output).absolute().parent/workspace_name
        workspace_id = identity(os.stat(workspace_name, dir_fd=parent, follow_symlinks=False))
        try:
            workspace_fd = os.open(workspace_name, os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW, dir_fd=parent)
            capture.fds.append(workspace_fd)
            capture.directories.append((parent, workspace_name, workspace_fd, workspace_id))
            for d in ('tmp',):
                os.mkdir(d, 0o700, dir_fd=workspace_fd)
            target = target_for_runtime(decode(command([str(python), '-I', '-S', '-B', '-c', RUNTIME_PROBE], task_directory=workspace, timeout=5)))
            need(target == result['target'])
            materialize(workspace_fd, members)
            verify_materialized(workspace, members)
            capture.check()
            command([str(python), '-I', '-B', '-m', 'venv', '--without-pip', str(workspace/'venv')], task_directory=workspace)
            command([str(pip_python), '-I', '-B', '-m', 'pip', '--isolated', '--python', str(workspace/'venv'),
                     '--no-cache-dir', 'install', '--no-index', '--no-deps', '--only-binary=:all:', '--require-hashes',
                     '--no-compile', '--find-links', str(workspace/'wheels'), '-r',
                     str(workspace/'requirements-selected.txt')], task_directory=workspace)
            profile = decode(members['project/'+PROFILE_FILE])
            payload_count = verify_runtime_files(workspace, result['target'], profile)
            command([str(pip_python), '-I', '-B', '-m', 'pip', '--isolated', '--python', str(workspace/'venv'),
                     '--no-cache-dir', 'check'], task_directory=workspace, timeout=10)
            installed = decode(command([str(workspace/'venv/bin/python'), '-I', '-B', '-c',
                "import importlib.metadata,json;print(json.dumps(sorted((d.metadata['Name'].lower().replace('_','-'),d.version) for d in importlib.metadata.distributions())))"], task_directory=workspace, timeout=10))
            expected = sorted([x['name'], x['version']] for x in decode(members['.aitrust-mcp.json'])['wheels'])
            need(installed == expected)
            need(verify(raw, root)[0] == result)
            verify_materialized(workspace, members)
            capture.check()
            configuration = {'profile': PROFILE, 'target': result['target'], 'artifact_sha256': result['sha256'],
                'runtime_distributions': installed, 'workspace': str(workspace),
                'runtime_payload_count': payload_count,
                'mcpServers': {'aitrustid': {'command': str(workspace/'venv/bin/python'),
                    'args': ['-I', '-B', str(workspace/'project/scripts/ai-tools-server.py')]}},
                'release_authorized': False, 'privacy_service_installed': False}
            capture.save(output, configuration, 32_000, prepublish=lambda: verify(raw, root))
            return {**result, 'installed': True, 'runtime_distribution_count': len(installed),
                    'runtime_payload_count': payload_count,
                    'configuration_included_in_stdout': False}
        finally:
            # Never follow/remove a replaced workspace or a previously supplied
            # user destination. A successfully published configuration owns its
            # workspace; uncertain publication also retains it for inspection.
            if not capture.output_may_exist:
                try:
                    current = os.stat(workspace_name, dir_fd=parent, follow_symlinks=False)
                    if identity(current) == workspace_id:
                        shutil.rmtree(workspace)
                except OSError:
                    pass


@refusal
def verify_install(archive, connection, *, python=sys.executable, root=ROOT, execute_probe=False):
    need(type(execute_probe) is bool and Path(python).is_absolute())
    with Capture() as capture:
        buffer = io.BytesIO()
        capture.artifact(archive, MAX_ARCHIVE, copy_to=buffer)
        raw = buffer.getvalue()
        result, members = verify(raw, root)
        config = decode(capture.read(connection, 32_000))
        need(set(config) == {'profile', 'target', 'artifact_sha256', 'runtime_distributions', 'workspace',
                             'runtime_payload_count', 'mcpServers', 'release_authorized', 'privacy_service_installed'} and
             config['profile'] == PROFILE and config['target'] == result['target'] and
             config['artifact_sha256'] == result['sha256'] and config['release_authorized'] is False and
             config['privacy_service_installed'] is False)
        workspace = Path(config['workspace'])
        need(workspace.is_absolute())
        capture.directory(workspace)
        expected_launch = {'aitrustid': {'command': str(workspace/'venv/bin/python'),
                           'args': ['-I', '-B', str(workspace/'project/scripts/ai-tools-server.py')]}}
        need(config['mcpServers'] == expected_launch and
             Path(os.path.realpath(workspace/'venv/bin/python')) == Path(os.path.realpath(python)))
        verify_materialized(workspace, members)
        profile = decode(members['project/'+PROFILE_FILE])
        payload_count = verify_runtime_files(workspace, result['target'], profile)
        expected_packages = sorted([x['name'], x['version']] for x in profile['targets'][result['target']])
        need(config['runtime_distributions'] == expected_packages and type(config['runtime_payload_count']) is int and
             config['runtime_payload_count'] == payload_count)
        with Capture() as runtime:
            venv_config = runtime.read(workspace/'venv/pyvenv.cfg', 16_000, private=False).decode('utf-8')
            need(len(re.findall(r'(?m)^include-system-site-packages = false$', venv_config)) == 1 and
                 not re.search(r'(?m)^include-system-site-packages = (?!false$)', venv_config))
            runtime.check()
        actual_runtime = decode(command([str(python), '-I', '-S', '-B', '-c', RUNTIME_PROBE],
                                        task_directory=workspace, timeout=5))
        need(target_for_runtime(actual_runtime) == result['target'])
        proof = None
        if execute_probe:
            # Paths are derived and code is verified above. Never execute a
            # command/argument chosen by a received configuration record.
            proof = decode(command([str(workspace/'venv/bin/python'), '-I', '-B',
                str(workspace/'project/tools/mcp_runtime_probe.py')], task_directory=workspace,
                timeout=45, output_limit=32_000))
            need(proof['profile'] == 'mcp-installed-synthetic-runtime-proof/v1' and proof['pass'] is True and
                 type(proof['cases']) is list and len(proof['cases']) == 8 and
                 all(row['status'] == 'PASS' for row in proof['cases']))
            verify_materialized(workspace, members)
            need(verify_runtime_files(workspace, result['target'], profile) == payload_count)
        need(verify(raw, root)[0] == result)
        capture.check()
    return {**result, 'installed_payloads_verified': payload_count, 'configuration_verified': True,
            'runtime_target_verified': True, 'runtime': proof, 'release_authorized': False}
