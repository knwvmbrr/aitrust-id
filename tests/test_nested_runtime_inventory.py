"""Bounded archive and actionable notice bindings; no runtime execution."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import stat
import struct
import warnings
import zipfile

import pytest
from tools import nested_runtime_inventory as n


def zipped(entries, compression=zipfile.ZIP_DEFLATED):
    output = io.BytesIO()
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', UserWarning)
        with zipfile.ZipFile(output, 'w', compression=compression) as z:
            for name, data, mode in entries:
                info = zipfile.ZipInfo(name)
                info.create_system = 3
                info.external_attr = mode << 16
                info.compress_type = compression if data else zipfile.ZIP_STORED
                z.writestr(info, data)
    return output.getvalue()


REG = stat.S_IFREG | 0o644
DIR = stat.S_IFDIR | 0o755


def test_source_header_and_all_member_bytes_are_inspected():
    body = b'# SPDX-License-Identifier: MIT\n# Copyright (c) 2021 Taneli Hukkinen\nvalue=1\n'
    raw = zipped([('pkg/', b'', DIR), ('pkg/code.py', body, REG), ('pkg/py.typed', b'', REG)])
    value = n.inspect_zip(raw)
    row = next(x for x in value['members'] if x['member'] == 'pkg/code.py')
    assert row['kind'] == 'python_source' and row['sha256'] == hashlib.sha256(body).hexdigest()
    assert row['header']['spdx'] == ['MIT'] and row['header']['text'] == body.decode()
    assert value['expanded_bytes'] == len(body) and len(value['members']) == 3


@pytest.mark.parametrize('name', ['../escape', '/absolute', 'a/../b', 'a//b', 'a/./b', 'a\\b', 'a/\nname'])
def test_unsafe_paths_are_refused(name):
    with pytest.raises(ValueError):
        n.inspect_zip(zipped([(name, b'text', REG)]))


@pytest.mark.parametrize('entries', [
    [('a.py', b'x', REG), ('a.py', b'y', REG)],
    [('a', b'x', REG), ('a/', b'', DIR)],
    [('a', b'x', REG), ('a/b.py', b'y', REG)],
    [('link', b'/private-canary', stat.S_IFLNK|0o777)],
    [('special', b'', stat.S_IFIFO|0o644)],
    [('setuid', b'text', stat.S_IFREG|0o4644)],
    [('nested.zip', b'opaque', REG)],
    [('hidden.py', b'PK\x03\x04opaque', REG)],
    [('binary.py', b'\x7fELFopaque', REG)],
    [('binary.txt', b'contains\x00NUL', REG)],
    [('unsupported.py', b'\xff', REG)],
])
def test_unsafe_structure_or_unreviewed_payload_refused(entries):
    with pytest.raises((ValueError, zipfile.BadZipFile)):
        n.inspect_zip(zipped(entries))


def test_crc_failure_is_not_an_observed_source():
    raw = bytearray(zipped([('file.py', b'value=1', REG)], zipfile.ZIP_STORED))
    raw[30+len('file.py')] ^= 1
    with pytest.raises(zipfile.BadZipFile):
        n.inspect_zip(bytes(raw))


def test_count_limit_is_checked_before_zipfile_allocation(monkeypatch):
    raw = zipped([('a.py', b'a', REG), ('b.py', b'b', REG)])
    monkeypatch.setattr(n, 'MAX_MEMBERS', 1)
    monkeypatch.setattr(n.zipfile, 'ZipFile', lambda *a, **k: pytest.fail('Allocated an oversized ZIP inventory'))
    with pytest.raises(ValueError): n.inspect_zip(raw)


@pytest.mark.parametrize('limit', ['MAX_TOTAL', 'MAX_MEMBER'])
def test_expanded_limits_are_enforced_before_member_read(monkeypatch, limit):
    raw = zipped([('a.py', b'x'*100, REG)])
    monkeypatch.setattr(n, limit, 50)
    monkeypatch.setattr(n.zipfile.ZipFile, 'open', lambda *a, **k: pytest.fail('Read beyond declared budget'))
    with pytest.raises(ValueError): n.inspect_zip(raw)


@pytest.mark.parametrize('mutation', ['prefix', 'trailing', 'comment', 'encryption', 'extra', 'overlap', 'zip64'])
def test_ambiguous_zip_metadata_refused(mutation):
    raw = bytearray(zipped([('a.py', b'a', REG), ('b.py', b'b', REG)]))
    central = raw.find(b'PK\x01\x02')
    if mutation == 'prefix': raw = b'prefix'+raw
    elif mutation == 'trailing': raw += b'trailing'
    elif mutation == 'comment': raw[-2:] = struct.pack('<H', 1); raw += b'x'
    elif mutation == 'encryption':
        raw[6:8] = struct.pack('<H', 1); raw[central+8:central+10] = struct.pack('<H', 1)
    elif mutation == 'extra': raw[central+30:central+32] = struct.pack('<H', 1)
    elif mutation == 'overlap':
        second = raw.find(b'PK\x01\x02', central+4)
        raw[second+42:second+46] = struct.pack('<I', 0)
    else: raw[-6:-2] = struct.pack('<I', 0xffffffff)
    with pytest.raises((ValueError, zipfile.BadZipFile)): n.inspect_zip(bytes(raw))


def test_unknown_header_license_requires_review():
    with pytest.raises(ValueError, match='Unreviewed SPDX'):
        n.inspect_zip(zipped([('new.py', b'# SPDX-License-Identifier: Proprietary\n', REG)]))


@pytest.fixture
def observed_root(tmp_path, monkeypatch):
    root = tmp_path.resolve()/'copy'
    for name in {*n.SOURCES, n.BASE+'manifest.json', n.BASE+'obligations.json', n.BUNDLE}:
        target = root/name; target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((n.ROOT/name).read_bytes())
    row, inner, asset = n.context()
    monkeypatch.setattr(n, 'context', lambda root: (row, inner, asset))
    return root


def reseal(root, value):
    value['sources'] = n.source_hashes(root)
    (root/(n.BASE+'manifest.json')).write_text(json.dumps(value))


def test_committed_obligations_cover_every_source_without_clearance():
    result = n.verify()
    assert result['entries'] == 614 and result['files'] == 567 and result['python_modules'] == 559
    assert result['explicit_spdx_modules'] == 7 and result['vendored_source_hash_matches'] == 4
    assert not result['archive_bytes_replayed'] and not result['permission_cleared']
    assert not result['full_corresponding_source_established'] and result['prepared_runtime_members_checked'] == 0
    bound = json.loads((n.ROOT/(n.BASE+'obligations.json')).read_text())
    assert all(r['source_form_shipped'] and r['notice_paths'] and r['classification']
               and r['per_file_permission_cleared'] is False for r in bound['module_obligations'])
    assert bound['upstream_vendored_source_declaration']['license_conclusion'] == 'NOASSERTION'
    assert not bound['upstream_vendored_source_declaration']['source_archive_replayed']


@pytest.mark.parametrize('change', ['exact', 'missing', 'extra', 'checksum', 'symlink'])
def test_prepared_runtime_is_byte_bound_before_notice_can_ship(observed_root, tmp_path, monkeypatch, change):
    root = observed_root
    row, inner, asset = n.context(root)
    runtime = tmp_path/'runtime'
    runtime.mkdir()
    data = b'synthetic-versioned-member'
    name = 'python_stdlib.zip'
    asset = {**asset, 'runtime_members': [{'name': name, 'sha256': n.sha(data), 'bytes': len(data)}]}
    monkeypatch.setattr(n, 'context', lambda root: (row, inner, asset))
    if change != 'missing':
        (runtime/name).write_bytes(data if change != 'checksum' else b'!'*len(data))
    if change == 'extra':
        (runtime/'extra').write_bytes(data)
    if change == 'symlink':
        (runtime/name).rename(tmp_path/'original')
        (runtime/name).symlink_to(tmp_path/'original')
    if change == 'exact':
        result, notice = n.notice_bundle(root, prepared_runtime=runtime)
        assert result['prepared_runtime_members_checked'] == 1
        assert result['notice_bundle_sha256'] == n.sha(notice)
    else:
        with pytest.raises((ValueError, OSError)):
            n.notice_bundle(root, prepared_runtime=runtime)


@pytest.mark.parametrize('field', ['permission_cleared', 'complete_transitive_coverage',
                                  'full_corresponding_source_established', 'observation_authenticated'])
def test_no_permission_or_source_completeness_promotion(observed_root, field):
    p = observed_root/(n.BASE+'manifest.json'); value = json.loads(p.read_text()); value[field] = True
    p.write_text(json.dumps(value))
    with pytest.raises(ValueError, match='promotion'): n.verify(observed_root)


def test_missing_module_or_notice_is_not_full_obligation_coverage(observed_root):
    p = observed_root/(n.BASE+'obligations.json'); value = json.loads(p.read_text())
    value['module_obligations'].pop(); p.write_text(json.dumps(value))
    with pytest.raises(ValueError, match='obligations drift'): n.verify(observed_root)


def test_changed_distribution_notice_bundle_is_refused(observed_root):
    p = observed_root/n.BUNDLE; p.write_bytes(p.read_bytes().replace(b'MagicStack', b'OtherParty'))
    with pytest.raises(ValueError, match='notice bundle drift'): n.verify(observed_root)


@pytest.mark.parametrize('change', ['source_version', 'notice_grant', 'upstream_acknowledgement', 'header', 'vendor',
                                  'vendored_license', 'vendored_relationship'])
def test_semantic_obligation_drift_refuses_even_resealed_hashes(observed_root, change):
    root = observed_root; manifest = json.loads((root/(n.BASE+'manifest.json')).read_text())
    if change == 'source_version':
        p = root/'site/public/device-licenses/source.txt'; p.write_text(p.read_text().replace('3.14.2', '3.14.1'))
    elif change == 'notice_grant':
        p = root/n.TANELI; p.write_text(p.read_text().replace('Permission is hereby granted', 'No permission granted'))
    elif change == 'upstream_acknowledgement':
        p = root/(n.BASE+'cpython-v3.14.2-license.rst'); p.write_text('Copyright without the required grant')
        o = root/(n.BASE+'upstream-license-origin.json'); origin = json.loads(o.read_text())
        origin.update(sha256=n.sha(p.read_bytes()), bytes=p.stat().st_size); o.write_text(json.dumps(origin))
    elif change == 'header':
        row = next(r for r in manifest['members'] if r['member'] == 'tomllib/__init__.py')
        row['header'].update(text='# SPDX-License-Identifier: MIT\n# Another holder\n')
        row['header']['sha256'] = n.sha(row['header']['text'].encode())
    elif change == 'vendor':
        row = next(r for r in manifest['members'] if r['member'] == 'ctypes/macholib/dyld.py')
        row['sha256'] = '0'*64
    else:
        p = root/(n.BASE+'cpython-v3.14.2-sbom.spdx.json'); sbom = json.loads(p.read_text())
        package_id = 'SPDXRef-PACKAGE-macholib'
        if change == 'vendored_license':
            next(r for r in sbom['packages'] if r['SPDXID'] == package_id)['licenseConcluded'] = 'MIT'
        else:
            record = next(r for r in sbom['relationships'] if r['spdxElementId'] == package_id)
            record['relationshipType'] = 'DEPENDS_ON'
        p.write_text(json.dumps(sbom))
        o = root/(n.BASE+'upstream-license-origin.json'); origin = json.loads(o.read_text())
        origin['additional_documents'][0].update(sha256=n.sha(p.read_bytes()), bytes=p.stat().st_size)
        o.write_text(json.dumps(origin))
    reseal(root, manifest)
    with pytest.raises(ValueError): n.verify(root)


def test_notice_bundle_contains_complete_terms_and_exact_retained_headers():
    _, data = n.notice_bundle()
    assert b'2015-2021 MagicStack Inc.' in data and b'2021 Taneli Hukkinen' in data
    assert b'Apache License' in data and b'Mozilla Public License Version 2.0' in data
    assert b'version 1.0, SVN revision 789' in data
    assert b'=== Retained header: sqlite3/__init__.py ===' in data
    assert b'This notice may not be removed or altered' in data


def test_cli_export_is_private_no_overwrite_and_does_not_echo_output_path(tmp_path, capsys):
    tmp_path.chmod(0o700)
    spec = importlib.util.spec_from_file_location('nested_cli', n.ROOT/'scripts/verify-nested-runtime.py')
    cli = importlib.util.module_from_spec(spec); spec.loader.exec_module(cli)
    output = tmp_path/'PRIVATE_EXPORT_CANARY'
    assert cli.main(['--export-notices', str(output)]) == 0
    first = capsys.readouterr().out
    p = output/'PYTHON-STDLIB-NOTICES.txt'; saved = p.read_bytes()
    assert not p.stat().st_mode & 0o077 and not output.stat().st_mode & 0o077
    assert cli.main(['--export-notices', str(output)]) == 1
    last = capsys.readouterr().out
    assert p.read_bytes() == saved and 'PRIVATE_EXPORT_CANARY' not in first+last
