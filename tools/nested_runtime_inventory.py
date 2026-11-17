"""Bounded source/notice observations inside the pinned runtime; never execute it."""
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import stat
import struct
import tarfile
import zipfile

from tools import native_inventory as native
from scripts import asset_notices
from scripts.source_snapshot import read_file

ROOT = Path(__file__).resolve().parents[1]
BASE = 'sbom/nested-runtime/'
PROFILE = 'pinned-runtime-source-notice-observation/v1'
BUNDLE = BASE+'PYTHON-STDLIB-NOTICES.txt'
MAX_ZIP = 4_194_304
MAX_MEMBERS = 4096
MAX_MEMBER = 1_048_576
MAX_TOTAL = 33_554_432
TANELI = 'sbom/notices/b80816b0d530b8accb4c2211783790984a6e3b61922c2b5ee92f3372ab2742fe.txt'
NOTICES = (*asset_notices.RUNTIME_NOTICES, BASE+'cpython-v3.14.2-license.rst', TANELI, 'LICENSE')
SOURCES = (*native.SOURCES, 'sbom/native/manifest.json', 'sbom/assets/notices.json',
           'scripts/asset_notices.py', 'tools/nested_runtime_inventory.py',
           'scripts/verify-nested-runtime.py', 'tests/test_nested_runtime_inventory.py',
           BASE+'upstream-license-origin.json', BASE+'cpython-v3.14.2-sbom.spdx.json',
           'tools/blind_review_io.py', *NOTICES)
SPDX = re.compile(r'^# SPDX-License-Identifier: ([A-Za-z0-9.() -]+)$', re.M)
MARKER = re.compile(r'copyright|licen[cs]e|SPDX|permission.*granted|redistribut|notice.*(?:retain|remov)', re.I)


def require(ok, reason='Nested runtime evidence refused'):
    if not ok:
        raise ValueError(reason)


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(',', ':'), allow_nan=False).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def source_hashes(root=ROOT):
    return {name: sha(read_file(root/name, 8_000_000)) for name in sorted(set(SOURCES))}


def central_directory(raw):
    """Bound central records before zipfile allocates one object per member."""
    require(type(raw) is bytes and 22 <= len(raw) <= MAX_ZIP, 'ZIP byte limit')
    signature, disk, start_disk, disk_count, count, size, offset, comment = struct.unpack('<4s4H2IH', raw[-22:])
    require(signature == b'PK\x05\x06' and disk == start_disk == comment == 0
            and disk_count == count and 1 <= count <= MAX_MEMBERS
            and offset + size == len(raw)-22, 'ZIP footer/profile refused')
    cursor = offset
    for _ in range(count):
        require(cursor+46 <= offset+size and raw[cursor:cursor+4] == b'PK\x01\x02', 'ZIP directory truncated')
        fields = struct.unpack('<4s6H3I5H2I', raw[cursor:cursor+46])
        name, extra, note, member_disk = fields[10:14]
        require(0 < name <= 1024 and extra == note == member_disk == 0
                and fields[8] != 0xffffffff and fields[9] != 0xffffffff
                and fields[16] != 0xffffffff, 'ZIP64/extra/comment profile refused')
        cursor += 46+name
        require(cursor <= offset+size, 'ZIP directory overflow')
    require(cursor == offset+size, 'ZIP directory count mismatch')
    return count, offset


def source_header(data):
    text = data.decode('utf-8', 'strict')
    require('\x00' not in text, 'NUL in source/text profile')
    lines = text.splitlines(keepends=True)
    head = lines[:128]
    marked = [i for i, line in enumerate(head) if MARKER.search(line)]
    retained = ''.join(head[:min(128, max(marked)+16)]) if marked else ''
    declarations = SPDX.findall(text)
    require(declarations == SPDX.findall(''.join(head)), 'SPDX outside supported header')
    require(all(x in ('MIT', 'PSF-2.0 AND (MIT OR Apache-2.0)') for x in declarations), 'Unreviewed SPDX declaration')
    return {'text': retained, 'sha256': sha(retained.encode()), 'spdx': declarations}


def inspect_zip(raw):
    count, central = central_directory(raw)
    rows, texts, names, regions = [], {}, set(), []
    total = 0
    with zipfile.ZipFile(io.BytesIO(raw)) as package:
        infos = package.infolist()
        require(len(infos) == count and not package.comment, 'ZIP inventory mismatch')
        for entry in infos:
            name = entry.filename
            native.safe_member(name)
            require(name.isascii() and name.rstrip('/') not in names, 'Duplicate/non-ASCII ZIP path')
            names.add(name.rstrip('/'))
            mode = entry.external_attr >> 16
            directory = entry.is_dir()
            require(entry.create_system == 3 and mode in ((stat.S_IFDIR|0o755,) if directory else
                    (stat.S_IFREG|0o644, stat.S_IFREG|0o755)), 'ZIP links/special/mode refused')
            require(entry.flag_bits == 0 and entry.compress_type in (0, 8)
                    and not entry.extra and not entry.comment and entry.extract_version <= 20,
                    'Encrypted/unsupported ZIP profile')
            require(0 <= entry.file_size <= MAX_MEMBER and 0 <= entry.compress_size <= MAX_ZIP,
                    'ZIP member byte limit')
            total += entry.file_size
            require(total <= MAX_TOTAL, 'ZIP expanded byte limit')
            at = entry.header_offset
            require(0 <= at and at+30 <= central, 'ZIP local header offset')
            local = struct.unpack('<4s5H3I2H', raw[at:at+30])
            require(local[0] == b'PK\x03\x04' and local[2] == entry.flag_bits
                    and local[3] == entry.compress_type and local[6:9] ==
                    (entry.CRC, entry.compress_size, entry.file_size)
                    and local[9] == len(name) and local[10] == 0
                    and raw[at+30:at+30+len(name)] == name.encode('ascii'), 'ZIP local/central mismatch')
            end = at+30+len(name)+entry.compress_size
            require(end <= central, 'ZIP local data overlaps directory')
            regions.append((at, end))
        regions.sort()
        require(regions[0][0] == 0 and regions[-1][1] == central
                and all(a[1] == b[0] for a, b in zip(regions, regions[1:])), 'ZIP overlap/gap/prefix refused')
        for entry in infos:
            name = entry.filename
            directory = entry.is_dir()
            if directory:
                require(entry.file_size == entry.compress_size == entry.CRC == 0, 'Nonempty ZIP directory')
                rows.append({'member': name, 'kind': 'directory', 'bytes': 0})
                continue
            require(not name.lower().endswith(('.zip', '.whl', '.jar', '.gz', '.tgz', '.tar', '.bz2')),
                    'Further nested container refused')
            chunks, length = [], 0
            with package.open(entry) as stream:
                while chunk := stream.read(65536):
                    length += len(chunk)
                    require(length <= entry.file_size and length <= MAX_MEMBER, 'ZIP actual byte limit')
                    chunks.append(chunk)
            data = b''.join(chunks)
            require(length == entry.file_size, 'ZIP member truncated')
            require(not data.startswith((b'PK\x03\x04', b'\x1f\x8b')), 'Hidden nested container refused')
            require(native.classify(name, data[:16]) is None, 'Native/executable candidate needs separate review')
            text = data.decode('utf-8', 'strict')
            require('\x00' not in text, 'Binary body outside source/text profile')
            kind = 'python_source' if name.endswith('.py') else 'auxiliary_text_or_script'
            row = {'member': name, 'kind': kind, 'bytes': length, 'sha256': sha(data)}
            if kind == 'python_source':
                row['header'] = source_header(data)
            rows.append(row)
            if name == 'ctypes/macholib/README.ctypes':
                texts[name] = text
    files = {r['member'] for r in rows if r['kind'] != 'directory'}
    require(all(not any(str(p) in files for p in PurePosixPath(r['member']).parents if str(p) != '.')
                for r in rows), 'ZIP file/directory path collision')
    return {'members': sorted(rows, key=lambda r: r['member']), 'expanded_bytes': total,
            'embedded_declarations': texts}


def context(root=ROOT):
    native.verify(root)
    asset_notices.verify(root)
    original = native.parse(read_file(root/'sbom/native/manifest.json', 8_000_000))
    asset = native.parse(read_file(root/'sbom/assets/notices.json', 8_000_000))
    rows = [r for r in original['artifacts'] if r['uninspected_nested_archives']]
    require(len(rows) == 1 and rows[0]['lock'] == 'site/package-lock.json'
            and rows[0]['package_path'] == 'node_modules/pyodide'
            and rows[0]['version'] == '314.0.7'
            and len(rows[0]['uninspected_nested_archives']) == 1, 'Nested inventory scope changed')
    row = rows[0]
    inner = row['uninspected_nested_archives'][0]
    require(inner['member'] == 'package/python_stdlib.zip', 'Nested member scope changed')
    require(all(row[k] == asset['runtime_origin'][k] for k in ('version', 'integrity', 'artifact_sha256')),
            'Runtime origin inventories disagree')
    return row, inner, asset


def captured_runtime(raw, row, inner, asset):
    observed, _ = native.inspect(raw, row)
    require(observed['uninspected_nested_archives'] == [inner], 'Parent nested identity mismatch')
    found = {}
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r|gz') as package:
        for member in package:
            if member.name not in (inner['member'], 'package/pyodide-lock.json'):
                continue
            require(member.isfile() and member.size <= MAX_ZIP and member.name not in found,
                    'Runtime capture refused')
            data = package.extractfile(member).read(MAX_ZIP+1)
            require(len(data) == member.size, 'Runtime capture truncated')
            found[member.name] = data
    require(set(found) == {inner['member'], 'package/pyodide-lock.json'}, 'Runtime metadata absent')
    for name, data in found.items():
        expected = next(r for r in asset['runtime_members'] if r['member'] == name)
        require(sha(data) == expected['sha256'] and len(data) == expected['bytes'], 'Runtime asset binding mismatch')
    require(sha(found[inner['member']]) == inner['sha256'], 'Nested bytes changed')
    info = native.parse(found['package/pyodide-lock.json'])['info']
    require(info == {'abi_version': '2026_0', 'arch': 'wasm32',
                     'platform': 'emscripten_5_0_3', 'python': '3.14.2'}, 'Runtime metadata changed')
    return found[inner['member']], info


def notices(root=ROOT):
    origin = native.parse(read_file(root/(BASE+'upstream-license-origin.json'), 100_000))
    acknowledgement = read_file(root/NOTICES[3], 200_000)
    require(origin['url'] == 'https://raw.githubusercontent.com/python/cpython/v3.14.2/Doc/license.rst'
            and origin['sha256'] == sha(acknowledgement) and origin['bytes'] == len(acknowledgement)
            and origin['source_version'] == '3.14.2'
            and origin['tag_signature_verified'] is False
            and origin['publisher_identity_independently_verified'] is False, 'Upstream notice origin drift')
    doc = acknowledgement.decode()
    require('Copyright (c) 2015-2021 MagicStack Inc.' in doc
            and 'Permission is hereby granted' in doc and 'uvloop 0.16' in doc, 'asyncio acknowledgement absent')
    raw = {name: read_file(root/name, 200_000) for name in NOTICES}
    require(sha(raw[TANELI]) == Path(TANELI).stem and b'Copyright (c) 2021 Taneli Hukkinen' in raw[TANELI]
            and b'Permission is hereby granted' in raw[TANELI], 'MIT notice text/holder drift')
    require(b'Apache License' in raw['LICENSE'] and b'Version 2.0' in raw['LICENSE'], 'Apache terms absent')
    source = raw[asset_notices.RUNTIME_NOTICES[2]].decode().splitlines()
    required = ['Unmodified upstream runtime: Pyodide 314.0.7, Python 3.14.2.',
        'Pyodide source and build recipes: https://github.com/pyodide/pyodide/tree/314.0.7',
        'Source archive: https://github.com/pyodide/pyodide/archive/refs/tags/314.0.7.tar.gz',
        'CPython source and bundled library acknowledgments: https://github.com/python/cpython/tree/v3.14.2']
    require(all(line in source for line in required), 'Versioned source declaration absent')
    return raw, required


def obligations(observation, root=ROOT):
    raw_notices, source_lines = notices(root)
    upstream_raw = read_file(root/(BASE+'cpython-v3.14.2-sbom.spdx.json'), 400_000)
    origin = native.parse(read_file(root/(BASE+'upstream-license-origin.json'), 100_000))
    source = origin['additional_documents'][0]
    require(source['url'] == 'https://raw.githubusercontent.com/python/cpython/v3.14.2/Misc/sbom.spdx.json'
            and source['sha256'] == sha(upstream_raw) and source['bytes'] == len(upstream_raw), 'Upstream SPDX drift')
    upstream = native.parse(upstream_raw)
    package_id = 'SPDXRef-PACKAGE-macholib'
    packages = [r for r in upstream['packages'] if r['SPDXID'] == package_id]
    require(len(packages) == 1, 'Vendored package identity changed')
    package = packages[0]
    source_hashes_declared = [r['checksumValue'] for r in package['checksums'] if r['algorithm'] == 'SHA256']
    require(package['name'] == 'macholib' and package['versionInfo'] == '1.0'
            and package['primaryPackagePurpose'] == 'SOURCE' and package['licenseConcluded'] == 'NOASSERTION'
            and re.fullmatch(r'https://files\.pythonhosted\.org/packages/[a-f0-9]{2}/[a-f0-9]{2}/'
                r'[a-f0-9]{60}/macholib-1\.0\.tar\.gz', package['downloadLocation'])
            and len(source_hashes_declared) == 1 and native.SHA.fullmatch(source_hashes_declared[0]),
            'Vendored source declaration changed')
    vendored_files = [r for r in upstream['files'] if r['fileName'].startswith('Lib/ctypes/macholib/')]
    contained = [r['relatedSpdxElement'] for r in upstream['relationships']
                 if r['spdxElementId'] == package_id and r['relationshipType'] == 'CONTAINS']
    expected = {r['fileName'].removeprefix('Lib/'): next(c['checksumValue'] for c in r['checksums']
        if c['algorithm'] == 'SHA256') for r in vendored_files}
    require(len(expected) == len(vendored_files) == len(contained) == 4
            and set(contained) == {r['SPDXID'] for r in vendored_files}, 'Vendored source coverage changed')
    vendor = observation['embedded_declarations'].get('ctypes/macholib/README.ctypes')
    require(type(vendor) is str and 'MIT or PSF' in vendor and 'version 1.0' in vendor, 'Vendored declaration absent')
    modules, spdx_members = [], []
    for row in observation['members']:
        if row['kind'] != 'python_source':
            continue
        header = row['header']
        require(type(header) is dict and set(header) == {'text', 'sha256', 'spdx'}
                and type(header['text']) is str and len(header['text']) <= 100_000
                and type(header['spdx']) is list and sha(header['text'].encode()) == header['sha256']
                and SPDX.findall(header['text']) == header['spdx'], 'Retained header changed')
        refs = list(NOTICES[:4])
        if header['spdx']:
            spdx_members.append(row['member'])
            if header['spdx'] == ['MIT']:
                require(row['member'].startswith('tomllib/') and '2021 Taneli Hukkinen' in header['text'],
                        'Unmapped MIT declaration')
                refs.append(TANELI)
            else:
                require(header['spdx'] == ['PSF-2.0 AND (MIT OR Apache-2.0)']
                        and row['member'].startswith('asyncio/') and '2015-2021 MagicStack' in header['text'],
                        'Unmapped compound declaration')
                refs.append('LICENSE')
        if 'Apache License, Version 2.0' in header['text'] or 'Apache License, 2.0' in header['text']:
            refs.append('LICENSE')
        vendored = row['member'] in expected
        if vendored:
            require(row['sha256'] == expected[row['member']], 'Vendored module differs from upstream SPDX')
        modules.append({'member': row['member'], 'source_sha256': row['sha256'],
            'source_form_shipped': True, 'retained_header_sha256': header['sha256'],
            'declared_spdx': header['spdx'], 'notice_paths': sorted(set(refs)),
            'classification': 'explicit_spdx_and_distribution_notices' if header['spdx'] else
                'retained_header_and_distribution_notices' if header['text'] else 'distribution_notice_context_only',
            'upstream_vendored_hash_matched': vendored,
            'vendored_readme_retained': vendored, 'per_file_permission_cleared': False})
    require(len(modules) == 559 and len(spdx_members) == 7
            and sum(r['upstream_vendored_hash_matched'] for r in modules) == 4, 'Module/declaration coverage changed')
    return {'profile': 'runtime-notice-retention-bindings/v1',
        'notices': [{'path': p, 'sha256': sha(v), 'bytes': len(v)} for p, v in sorted(raw_notices.items())],
        'declared_source_lines': source_lines, 'source_urls_fetched_or_module_matched': False,
        'module_obligations': modules, 'vendored_readme': vendor,
        'mit_notice_origin_limit': 'Existing setuptools-vendored tomli notice; matching MIT grant/holder text, not proof of module/package version equivalence.',
        'upstream_vendored_source_declaration': {
            'name': package['name'], 'version': package['versionInfo'],
            'url': package['downloadLocation'], 'sha256': source_hashes_declared[0],
            'license_conclusion': package['licenseConcluded'], 'source_archive_replayed': False},
        'full_corresponding_source_established': False, 'permission_cleared': False}


def collect(archive, root=ROOT, observer='Codex'):
    require(type(observer) is str and re.fullmatch(r'[A-Za-z][A-Za-z0-9 ._-]{0,79}', observer), 'Observer required')
    before = source_hashes(root)
    row, inner, asset = context(root)
    zipped, info = captured_runtime(read_file(Path(archive), native.MAX_ARCHIVE), row, inner, asset)
    observed = inspect_zip(zipped)
    bound = obligations(observed, root)
    require(before == source_hashes(root), 'Sources changed during inspection')
    return {'profile': PROFILE, 'captured_at': datetime.now(timezone.utc).isoformat(),
        'observed_by': observer, 'sources': before, 'parent': {k: row[k] for k in
            ('lock', 'package_path', 'version', 'integrity', 'artifact_sha256')},
        'nested': inner, 'runtime_metadata': info, **observed, 'obligations_sha256': sha(encoded(bound)),
        'observation_authenticated': False, 'permission_cleared': False,
        'complete_transitive_coverage': False, 'full_corresponding_source_established': False}, bound


def verify_prepared_runtime(directory, asset):
    members = asset['runtime_members']
    require({p.name for p in directory.iterdir()} == {m['name'] for m in members},
            'Prepared runtime member set changed')
    for member in members:
        data = read_file(directory/member['name'], member['bytes'])
        require(len(data) == member['bytes'] and sha(data) == member['sha256'],
                'Prepared runtime member bytes changed')


def verify(root=ROOT, archive=None, prepared_runtime=None):
    before = source_hashes(root)
    manifest_raw = read_file(root/(BASE+'manifest.json'), 8_000_000)
    binding_raw = read_file(root/(BASE+'obligations.json'), 8_000_000)
    value, bound = native.parse(manifest_raw), native.parse(binding_raw)
    require(set(value) == {'profile', 'captured_at', 'observed_by', 'sources', 'parent', 'nested',
            'runtime_metadata', 'members', 'expanded_bytes', 'embedded_declarations', 'obligations_sha256',
            'observation_authenticated', 'permission_cleared', 'complete_transitive_coverage',
            'full_corresponding_source_established'} and value['profile'] == PROFILE
            and value['sources'] == before, 'Nested inventory source/profile drift')
    require(all(value[k] is False for k in ('observation_authenticated', 'permission_cleared',
            'complete_transitive_coverage', 'full_corresponding_source_established')), 'Clearance promotion refused')
    stamp = datetime.fromisoformat(value['captured_at'])
    require(stamp.tzinfo is not None and stamp <= datetime.now(timezone.utc), 'Observation time refused')
    require(type(value['observed_by']) is str and re.fullmatch(r'[A-Za-z][A-Za-z0-9 ._-]{0,79}', value['observed_by']), 'Observer refused')
    row, inner, asset = context(root)
    require(value['parent'] == {k: row[k] for k in
            ('lock', 'package_path', 'version', 'integrity', 'artifact_sha256')}
            and value['nested'] == inner,
            'Nested/parent identity drift')
    require(value['runtime_metadata'] == {'abi_version': '2026_0', 'arch': 'wasm32',
            'platform': 'emscripten_5_0_3', 'python': '3.14.2'}, 'Runtime metadata drift')
    rows = value['members']
    require(type(rows) is list and 1 <= len(rows) <= MAX_MEMBERS, 'Member count refused')
    names, total = [], 0
    for member in rows:
        require(type(member) is dict and member['kind'] in ('directory', 'python_source', 'auxiliary_text_or_script'), 'Member kind refused')
        native.safe_member(member['member']); names.append(member['member'])
        keys = {'member', 'kind', 'bytes'} | (set() if member['kind'] == 'directory' else {'sha256'})
        if member['kind'] == 'python_source': keys.add('header')
        require(set(member) == keys and type(member['bytes']) is int and 0 <= member['bytes'] <= MAX_MEMBER, 'Member fields/size refused')
        if member['kind'] != 'directory':
            require(type(member['sha256']) is str and native.SHA.fullmatch(member['sha256']), 'Member digest refused')
        else: require(member['bytes'] == 0, 'Directory size refused')
        total += member['bytes']
    require(names == sorted(set(names)) and total == value['expanded_bytes'] and total <= MAX_TOTAL, 'Member coverage/size drift')
    expected = obligations(value, root)
    require(encoded(bound) == encoded(expected) and sha(encoded(bound)) == value['obligations_sha256'], 'Notice obligations drift')
    bundle_raw = read_file(root/BUNDLE, 4_000_000)
    require(bundle_raw == render_notice_bundle(value, bound, root), 'Derived notice bundle drift')
    if archive is not None:
        actual, actual_bound = collect(archive, root, observer=value['observed_by'])
        require(all(actual[k] == value[k] for k in value if k != 'captured_at')
                and encoded(actual_bound) == encoded(bound), 'Archive observation does not reproduce')
    if prepared_runtime is not None:
        verify_prepared_runtime(Path(prepared_runtime), asset)
    require(before == source_hashes(root) and manifest_raw == read_file(root/(BASE+'manifest.json'), 8_000_000)
            and binding_raw == read_file(root/(BASE+'obligations.json'), 8_000_000)
            and bundle_raw == read_file(root/BUNDLE, 4_000_000), 'Evidence changed during verification')
    return {'captured_at': datetime.now(timezone.utc).isoformat(), 'pass': True, 'profile': PROFILE,
        'sources': before, 'archive_bytes_replayed': archive is not None, 'entries': len(rows),
        'files': sum(r['kind'] != 'directory' for r in rows), 'python_modules': len(bound['module_obligations']),
        'explicit_spdx_modules': sum(bool(r['declared_spdx']) for r in bound['module_obligations']),
        'vendored_source_hash_matches': sum(r['upstream_vendored_hash_matched'] for r in bound['module_obligations']),
        'expanded_bytes': total, 'notice_bindings_checked': len(bound['notices']),
        'prepared_runtime_members_checked': len(asset['runtime_members']) if prepared_runtime is not None else 0,
        'notice_bundle_sha256': sha(bundle_raw), 'notice_bundle_bytes': len(bundle_raw),
        'permission_cleared': False, 'complete_transitive_coverage': False,
        'full_corresponding_source_established': False, 'independent_accuracy_evidence': False}


def notice_bundle(root=ROOT, *, archive=None, prepared_runtime=None):
    result = verify(root, archive, prepared_runtime)
    bundle = read_file(root/BUNDLE, 4_000_000)
    require(len(bundle) == result['notice_bundle_bytes'] and sha(bundle) == result['notice_bundle_sha256'],
            'Verified notice bundle changed before use')
    return result, bundle


def render_notice_bundle(value, bound, root=ROOT):
    chunks = [b'Pinned runtime source/notice retention evidence. Not license clearance.\n']
    for notice in bound['notices']:
        chunks.extend([('\n=== '+notice['path']+' ===\n').encode(), read_file(root/notice['path'], 200_000), b'\n'])
    chunks.extend([b'\n=== Vendored macholib declaration ===\n', bound['vendored_readme'].encode()])
    source = bound['upstream_vendored_source_declaration']
    chunks.extend([b'\n=== CPython SPDX macholib source declaration ===\n',
        (source['url']+'\nSHA256: '+source['sha256']+'\nLicense conclusion: '+source['license_conclusion']+'\n').encode()])
    for member in value['members']:
        if member['kind'] == 'python_source' and member['header']['text']:
            chunks.extend([('\n=== Retained header: '+member['member']+' ===\n').encode(), member['header']['text'].encode()])
    result = b''.join(chunks)
    require(len(result) <= 4_000_000, 'Notice bundle limit')
    return result
