"""Offline SPDX schema and selected inventory consistency; no release clearance."""
from datetime import datetime, timezone
import hashlib
import re

from jsonschema import Draft201909Validator
from protocol.evidence import read_evidence

VENDOR = 'spec/vendor/spdx-2.3.1'
COMMIT = '6f2cb47d13db19b12c23885573b22ef32ec1ada5'
HASHES = {
    'schema.json': '4126dc29f15e92feec92e9622f4939131ad58b125d6f578aa93e980a6e6f3212',
    'LICENSE': '017e38491cccbd2bdb6da0a32a33db9ec245b5dab30fdcd09f2c742c975e5b35',
}
SOURCE = {
    'schema_version': 1, 'title': 'SPDX Specification 2.3.1 JSON schema',
    'publisher': 'SPDX contributors', 'upstream_commit': COMMIT,
    'source': f'https://github.com/spdx/spdx-spec/tree/{COMMIT}',
    'schema_source': f'https://raw.githubusercontent.com/spdx/spdx-spec/{COMMIT}/schemas/spdx-schema.json',
    'license': 'CC-BY-3.0', 'license_url': 'https://creativecommons.org/licenses/by/3.0/',
    'modified': False, 'files': HASHES,
}


def pinned_validator(root):
    """Validate the pinned, unmodified schema and its redistribution notice."""
    vendor = root / VENDOR
    if read_evidence(vendor / 'source.json') != SOURCE:
        raise ValueError('SPDX attribution or source identity changed')
    for name, expected in HASHES.items():
        path = vendor / name
        if path.is_symlink() or any(p.is_symlink() for p in path.parents):
            raise ValueError('SPDX trust input symlink refused')
        with path.open('rb') as stream:
            raw = stream.read(100_001)
        if len(raw) > 100_000 or hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError('Pinned SPDX schema or license identity changed')
    schema = read_evidence(vendor / 'schema.json', limit=100_000)

    def local_refs(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if key == '$ref' and (not isinstance(item, str) or not item.startswith('#/')):
                    raise ValueError('External schema resolution refused')
                local_refs(item)
        elif isinstance(value, list):
            for item in value:
                local_refs(item)

    local_refs(schema)
    Draft201909Validator.check_schema(schema)
    return Draft201909Validator(schema)


def document_profile(document, validator, *, now=None):
    """Check the current image profile without treating metadata as permission."""
    if next(validator.iter_errors(document), None) is not None:
        raise ValueError('SPDX schema validation failed')
    if document['spdxVersion'] != 'SPDX-2.3' or document['dataLicense'] != 'CC0-1.0':
        raise ValueError('Unsupported selected SPDX profile')
    if document.get('externalDocumentRefs') or document.get('snippets'):
        raise ValueError('External documents and snippets require a separate profile')
    try:
        created = datetime.fromisoformat(document['creationInfo']['created'])
    except ValueError:
        raise ValueError('Invalid creation date') from None
    now = datetime.now(timezone.utc) if now is None else now
    if now.tzinfo is None or created.tzinfo is None or created > now:
        raise ValueError('Invalid creation date')
    elements = [document, *document.get('packages', []), *document.get('files', [])]
    ids = [item['SPDXID'] for item in elements]
    if len(set(ids)) != len(ids) or any(not re.fullmatch(r'SPDXRef-[A-Za-z0-9.-]+', value) for value in ids):
        raise ValueError('Duplicate or invalid element identity')
    known = set(ids)
    files = {item['SPDXID']: item for item in document.get('files', [])}
    packages = {item['SPDXID']: item for item in document.get('packages', [])}
    contains = {}
    for relationship in document.get('relationships', []):
        source, target = relationship['spdxElementId'], relationship['relatedSpdxElement']
        if source not in known or target not in known | {'NONE', 'NOASSERTION'}:
            raise ValueError('Dangling element relationship')
        kind = relationship['relationshipType']
        if kind == 'CONTAINED_BY':
            source, target = target, source
        if kind in ('CONTAINS', 'CONTAINED_BY') and source in packages and target in files:
            contains.setdefault(source, set()).add(target)
    if any(value not in packages for value in document.get('documentDescribes', [])):
        raise ValueError('Unknown described package')
    checksum_count = 0
    for element in elements:
        seen = set()
        for checksum in element.get('checksums', []):
            algorithm = checksum['algorithm']
            length = {'SHA1': 40, 'SHA256': 64}.get(algorithm)
            if (length is None or algorithm in seen
                    or not re.fullmatch('[0-9a-f]{' + str(length) + '}', checksum['checksumValue'])):
                raise ValueError('Invalid or unsupported selected checksum')
            seen.add(algorithm)
            checksum_count += 1
    verified = 0
    for pid, package in packages.items():
        code = package.get('packageVerificationCode')
        if not package.get('filesAnalyzed', True):
            if code is not None or contains.get(pid):
                raise ValueError('Metadata-only package has analyzed files or verification code')
            continue
        if code is None:
            continue  # Optional under SPDX 2.3.1 clause 7.9; do not invent a requirement.
        if not re.fullmatch('[0-9a-f]{40}', code['packageVerificationCodeValue']):
            raise ValueError('Invalid package verification code')
        exclusions = set(code.get('packageVerificationCodeExcludedFiles', []))
        hashes = []
        for fid in contains.get(pid, set()):
            file = files[fid]
            if file['fileName'] in exclusions:
                continue
            checks = [row['checksumValue'] for row in file['checksums'] if row['algorithm'] == 'SHA1']
            if len(checks) != 1:
                raise ValueError('Package verification needs exactly one file SHA1')
            hashes.extend(checks)
        expected = hashlib.sha1(''.join(sorted(hashes)).encode('ascii')).hexdigest()
        if expected != code['packageVerificationCodeValue']:
            raise ValueError('Package verification code disagrees with contained file checksums')
        verified += 1
    return {
        'schema_validated': True, 'elements_checked': len(ids),
        'checksums_checked': checksum_count, 'package_verification_codes_recomputed': verified,
        'license_expressions_reviewed': False, 'license_cleared': False,
        'release_signed': False, 'source_files_authenticated': False,
    }
