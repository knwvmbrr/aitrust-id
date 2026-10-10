"""Corrupted metadata must not pass an inventory-format check or gain clearance."""
import copy
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import socket
import subprocess
import sys

import pytest
from protocol.evidence import read_evidence
from scripts.spdx_inventory import VENDOR, pinned_validator, document_profile

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('spdx_standard', ROOT / 'scripts/verify-runtime-sbom-standard.py')
STANDARD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(STANDARD)
NOW = datetime(2026, 10, 10, tzinfo=timezone.utc)


@pytest.fixture(scope='module')
def validator():
    return pinned_validator(ROOT)


@pytest.fixture
def document():
    digest = hashlib.sha1(b'synthetic file').hexdigest()
    return {
        'SPDXID': 'SPDXRef-DOCUMENT', 'creationInfo': {'created': '2026-10-09T00:00:00Z', 'creators': ['Tool: test']},
        'dataLicense': 'CC0-1.0', 'name': 'synthetic inventory', 'spdxVersion': 'SPDX-2.3',
        'documentNamespace': 'https://example.invalid/synthetic-inventory',
        'packages': [{'SPDXID': 'SPDXRef-Package', 'downloadLocation': 'NOASSERTION', 'name': 'synthetic',
                      'filesAnalyzed': True, 'packageVerificationCode': {
                          'packageVerificationCodeValue': hashlib.sha1(digest.encode('ascii')).hexdigest()}}],
        'files': [{'SPDXID': 'SPDXRef-File', 'fileName': './file.txt', 'checksums': [
            {'algorithm': 'SHA1', 'checksumValue': digest}]}],
        'relationships': [{'spdxElementId': 'SPDXRef-Package', 'relatedSpdxElement': 'SPDXRef-File',
                           'relationshipType': 'CONTAINS'}],
        'documentDescribes': ['SPDXRef-Package'],
    }


def test_actual_three_bound_inventories_validate_offline(monkeypatch):
    def refuse_network(*args, **kwargs):
        raise AssertionError('Inventory verification attempted network access')
    monkeypatch.setattr(socket.socket, 'connect', refuse_network)
    monkeypatch.setattr(socket, 'create_connection', refuse_network)
    report = STANDARD.verify()
    assert report['pass'] and report['package_occurrences'] == 421
    assert len(report['images']) == 3 and report['verification_network_requests'] == 0
    assert sum(row['elements_checked'] for row in report['images']) == 9155
    assert sum(row['package_verification_codes_recomputed'] for row in report['images']) == 261
    for row in [report, *report['images']]:
        assert row['license_cleared'] is False and row['release_signed'] is False
        assert row['source_files_authenticated'] is False
    assert not report['scanner_signed_identity_verified'] and not report['tag_release_approved']


@pytest.mark.parametrize('mutation', [
    'missing_name', 'extra_field', 'duplicate_id', 'duplicate_document_id', 'invalid_id',
    'dangling_source', 'dangling_target', 'unknown_described_package', 'bad_date', 'future_date',
    'checksum_length', 'checksum_case', 'duplicate_checksum', 'unsupported_checksum',
    'wrong_code', 'changed_file_hash', 'missing_file_sha1', 'metadata_only_code', 'metadata_only_files',
    'external_document', 'snippet', 'wrong_version', 'wrong_data_license',
])
def test_invalid_or_unsupported_inventory_refused(document, validator, mutation):
    package, file = document['packages'][0], document['files'][0]
    if mutation == 'missing_name': del package['name']
    elif mutation == 'extra_field': document['approved'] = True
    elif mutation == 'duplicate_id': file['SPDXID'] = package['SPDXID']
    elif mutation == 'duplicate_document_id': package['SPDXID'] = document['SPDXID']
    elif mutation == 'invalid_id': file['SPDXID'] = 'SPDXRef-bad/identity'
    elif mutation == 'dangling_source': document['relationships'][0]['spdxElementId'] = 'SPDXRef-Missing'
    elif mutation == 'dangling_target': document['relationships'][0]['relatedSpdxElement'] = 'SPDXRef-Missing'
    elif mutation == 'unknown_described_package': document['documentDescribes'] = ['SPDXRef-File']
    elif mutation == 'bad_date': document['creationInfo']['created'] = '2026-02-30T00:00:00Z'
    elif mutation == 'future_date': document['creationInfo']['created'] = '2026-10-11T00:00:00Z'
    elif mutation == 'checksum_length': file['checksums'][0]['checksumValue'] = 'ab'
    elif mutation == 'checksum_case': file['checksums'][0]['checksumValue'] = 'A' * 40
    elif mutation == 'duplicate_checksum': file['checksums'].append(copy.deepcopy(file['checksums'][0]))
    elif mutation == 'unsupported_checksum': file['checksums'][0] = {'algorithm': 'MD5', 'checksumValue': 'a' * 32}
    elif mutation == 'wrong_code': package['packageVerificationCode']['packageVerificationCodeValue'] = '0' * 40
    elif mutation == 'changed_file_hash': file['checksums'][0]['checksumValue'] = '1' * 40
    elif mutation == 'missing_file_sha1': file['checksums'][0] = {'algorithm': 'SHA256', 'checksumValue': 'a' * 64}
    elif mutation == 'metadata_only_code': package['filesAnalyzed'] = False
    elif mutation == 'metadata_only_files':
        package['filesAnalyzed'] = False
        del package['packageVerificationCode']
    elif mutation == 'external_document': document['externalDocumentRefs'] = [{
        'externalDocumentId': 'DocumentRef-Other', 'spdxDocument': 'https://example.invalid/external',
        'checksum': {'algorithm': 'SHA1', 'checksumValue': '0' * 40}}]
    elif mutation == 'snippet': document['snippets'] = [{'SPDXID': 'SPDXRef-Snippet',
        'snippetFromFile': 'SPDXRef-File', 'ranges': [{'startPointer': {'reference': 'SPDXRef-File', 'offset': 0},
                                                  'endPointer': {'reference': 'SPDXRef-File', 'offset': 1}}]}]
    elif mutation == 'wrong_version': document['spdxVersion'] = 'SPDX-2.2'
    else: document['dataLicense'] = 'NOASSERTION'
    with pytest.raises(ValueError): document_profile(document, validator, now=NOW)


def test_optional_code_is_not_invented_requirement(document, validator):
    del document['packages'][0]['packageVerificationCode']
    assert document_profile(document, validator, now=NOW)['package_verification_codes_recomputed'] == 0


def test_inverse_contains_is_reproduced(document, validator):
    document['relationships'][0] = {'spdxElementId': 'SPDXRef-File', 'relatedSpdxElement': 'SPDXRef-Package',
                                    'relationshipType': 'CONTAINED_BY'}
    assert document_profile(document, validator, now=NOW)['package_verification_codes_recomputed'] == 1


def test_excluded_files_are_not_hashed(document, validator):
    document['packages'][0]['packageVerificationCode'] = {
        'packageVerificationCodeValue': hashlib.sha1(b'').hexdigest(),
        'packageVerificationCodeExcludedFiles': ['./file.txt']}
    assert document_profile(document, validator, now=NOW)['package_verification_codes_recomputed'] == 1


def test_sha256_metadata_is_supported(document, validator):
    document['files'][0]['checksums'].append({'algorithm': 'SHA256', 'checksumValue': 'a' * 64})
    assert document_profile(document, validator, now=NOW)['checksums_checked'] == 2


@pytest.mark.parametrize('mutation', ['schema_changed', 'schema_missing', 'license_changed', 'license_missing',
                                     'schema_link', 'license_link', 'source_changed', 'duplicate_source_key',
                                     'remote_schema_ref'])
def test_changed_trust_input_refused(tmp_path, mutation):
    directory = tmp_path / VENDOR
    shutil.copytree(ROOT / VENDOR, directory)
    if mutation.endswith('_missing'): (directory / ('schema.json' if mutation.startswith('schema') else 'LICENSE')).unlink()
    elif mutation.endswith('_link'):
        path = directory / ('schema.json' if mutation.startswith('schema') else 'LICENSE')
        target = tmp_path / 'outside'
        path.rename(target)
        path.symlink_to(target)
    elif mutation == 'source_changed':
        path = directory / 'source.json'; value = json.loads(path.read_text()); value['modified'] = True
        path.write_text(json.dumps(value))
    elif mutation == 'duplicate_source_key':
        path = directory / 'source.json'; path.write_text(path.read_text().replace('"schema_version": 1,', '"schema_version": 1, "schema_version": 1,'))
    elif mutation == 'remote_schema_ref':
        path = directory / 'schema.json'; value = json.loads(path.read_text()); value['$ref'] = 'https://example.invalid/private-schema'
        path.write_text(json.dumps(value))
    else:
        path = directory / ('schema.json' if mutation.startswith('schema') else 'LICENSE')
        path.write_bytes(path.read_bytes() + b'altered')
    with pytest.raises((ValueError, OSError)): pinned_validator(tmp_path)


def test_inventory_json_duplicate_keys_refused(tmp_path):
    path = tmp_path / 'inventory.json'; path.write_text('{"name":"first","name":"second"}')
    with pytest.raises(ValueError, match='Duplicate'): read_evidence(path)


@pytest.mark.parametrize('mutation', ['file_schema', 'cross_kind_id', 'file_checksum'])
def test_rehashed_corruption_still_refused(tmp_path, mutation):
    names = ['.dockerignore', 'deploy/docker-compose.yml',
             'eval/dependencies/runtime-sbom.json', 'runs/2026-10-10-runtime-license-inventory.json']
    names += [f'services/{role}/{name}' for role in ('gateway', 'evaluator', 'anonymizer')
              for name in ('Dockerfile', 'requirements.lock')]
    names += [f'sbom/runtime/{role}-linux-amd64.spdx.json' for role in ('gateway', 'evaluator', 'anonymizer')]
    for name in names:
        destination = tmp_path / name; destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, destination)
    shutil.copytree(ROOT / VENDOR, tmp_path / VENDOR)
    path = tmp_path / 'sbom/runtime/gateway-linux-amd64.spdx.json'
    value = json.loads(path.read_text())
    if mutation == 'file_schema': del value['files'][0]['fileName']
    elif mutation == 'cross_kind_id': value['files'][0]['SPDXID'] = value['packages'][0]['SPDXID']
    else: value['files'][0]['checksums'][0]['checksumValue'] = 'a'
    path.write_text(json.dumps(value))
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    # Matching regenerated hashes cannot turn structurally invalid data into valid evidence.
    for name, field in [('eval/dependencies/runtime-sbom.json', 'sha256'),
                        ('runs/2026-10-10-runtime-license-inventory.json', 'spdx_sha256')]:
        target = tmp_path / name; manifest = json.loads(target.read_text())
        manifest['images'][0][field] = digest; target.write_text(json.dumps(manifest))
    with pytest.raises(ValueError): STANDARD.verify(tmp_path)


def test_missing_locked_dependency_refuses_cli():
    result = subprocess.run([sys.executable, '-S', str(ROOT / 'scripts/verify-runtime-sbom-standard.py')],
                            cwd=ROOT, capture_output=True, text=True, timeout=30)
    assert result.returncode == 1 and 'SPDX verification refused:' in result.stderr
    assert 'Traceback' not in result.stderr and '"pass": true' not in result.stdout
