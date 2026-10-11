"""Verify observed notice bytes and dependency bindings, never grant legal permission."""
import base64
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import tarfile
from urllib.parse import urlsplit
from protocol.corpus import read_regular
from protocol.evidence import read_evidence

ROOT = Path(__file__).resolve().parents[1]
SHA = re.compile(r'[a-f0-9]{64}')
COVERAGE = {'reviewed_runtime_license_obligations', 'reviewed_client_build_license_obligations',
            'all_native_transitive_components', 'all_model_font_runtime_data_assets',
            'all_declared_architectures', 'source_offer_obligations'}
NOTICE_NAME = re.compile(r'(?:licen[sc]e|copying|copyright|notice)(?:[._-].*)?', re.I)
MANIFEST = 'sbom/notices/manifest.json'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def file_bytes(root, relative, limit=2_000_000):
    require(isinstance(relative, str) and not PurePosixPath(relative).is_absolute() and
            '..' not in PurePosixPath(relative).parts and '\\' not in relative,
            'Unsafe repository notice path')
    path = root / relative
    require(not any(p.is_symlink() for p in [path, *path.parents]), 'Notice source symlink refused')
    return read_regular(path, limit)


def refs(rows, manifest, root, origin, prefix='package/'):
    require(isinstance(rows, list) and len(rows) <= 2048, 'Invalid notice reference inventory')
    seen = set()
    for row in rows:
        require(isinstance(row, dict) and set(row) == {'source_path', 'sha256', 'bytes', 'notice'}, 'Invalid notice reference')
        source = row['source_path']
        require(isinstance(source, str) and len(source) <= 512 and '\\' not in source and
                '..' not in PurePosixPath(source).parts and source not in seen, 'Invalid duplicate notice member')
        if origin == 'npm':
            require(source.startswith(prefix) and not PurePosixPath(source).is_absolute(), 'Unsafe npm notice member')
        else:
            require(source.startswith(('/usr/share/doc/', '/usr/local/lib/python3.12/')), 'Unreviewed installed notice root')
        seen.add(source)
        digest = row['sha256']
        require(isinstance(digest, str) and SHA.fullmatch(digest) and digest in manifest['notices'], 'Unregistered notice digest')
        require(row['notice'] == 'sbom/notices/' + digest + '.txt', 'Notice digest/path mismatch')
        require(type(row['bytes']) is int and row['bytes'] == manifest['notices'][digest], 'Notice byte count mismatch')
        raw = file_bytes(root, row['notice'])
        require(len(raw) == row['bytes'] and hashlib.sha256(raw).hexdigest() == digest, 'Notice bytes changed')
        raw.decode('utf-8', errors='strict')
    return seen


def npm_prefix(row):
    # The locked DefinitelyTyped artifact uses its actual upstream archive root.
    return 'emscripten/' if row['package_path'] == 'node_modules/@types/emscripten' else 'package/'


def archive_notices(archive, row):
    raw = read_regular(archive, 52_428_800)
    algorithm, encoded = row['integrity'].split('-', 1)
    expected = base64.b64decode(encoded, validate=True)
    require(hashlib.new(algorithm, raw).digest() == expected and hashlib.sha256(raw).hexdigest() == row['artifact_sha256'], 'npm archive differs from lock or observation')
    result = {}
    count, total, unpacked = 0, 0, 0
    # No extraction to disk and no package code execution.
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r|gz') as tar:
        for member in tar:
            count += 1
            require(count <= 100_000, 'Archive member limit')
            unpacked += member.size
            require(0 <= member.size and unpacked <= 536_870_912, 'Archive unpacked byte limit')
            if not NOTICE_NAME.fullmatch(PurePosixPath(member.name).name) or not member.isfile():
                continue
            require(member.name.startswith(npm_prefix(row)) and '..' not in PurePosixPath(member.name).parts and '\\' not in member.name, 'Unsafe archive notice path')
            require(0 < member.size <= 2_097_152, 'Archive notice size limit')
            total += member.size
            require(total <= 33_554_432 and member.name not in result, 'Archive notice inventory limit or duplicate')
            data = tar.extractfile(member).read()
            require(len(data) == member.size, 'Archive notice truncated')
            try:
                data.decode('utf-8', errors='strict')
            except UnicodeError:
                continue
            result[member.name] = (hashlib.sha256(data).hexdigest(), len(data))
    expected_notices = {n['source_path']: (n['sha256'], n['bytes']) for n in row['notices']}
    require(result == expected_notices, 'Notice extraction differs from supplied archive')


def verify(root=ROOT, archive_dir=None):
    root = Path(root).absolute()
    proof_files = [MANIFEST, '.gitattributes', 'scripts/license_notices.py', 'scripts/verify-redistribution-notices.py',
                   'scripts/collect-runtime-notices.py', 'protocol/evidence.py', 'protocol/corpus.py']
    before = {name: hashlib.sha256(file_bytes(root, name)).hexdigest() for name in proof_files}
    value = read_evidence(root / MANIFEST)
    require(set(value) == {'schema_version', 'captured_at', 'runtime_observed_at', 'npm_observed_at', 'kind', 'collected_by', 'sources', 'runtime_collector_sha256', 'runtime', 'npm', 'notices', 'coverage', 'license_cleared', 'independent_accuracy_evidence'}, 'Unexpected notice manifest fields')
    require(type(value['schema_version']) is int and value['schema_version'] == 1 and value['kind'] == 'observed_notice_evidence', 'Unsupported notice evidence profile')
    stamp = datetime.fromisoformat(value['captured_at'])
    require(stamp.tzinfo is not None and stamp <= datetime.now(timezone.utc) and value['collected_by'] == 'Codex', 'Invalid observed notice attribution/time')
    for name in ('runtime_observed_at', 'npm_observed_at'):
        observed = datetime.fromisoformat(value[name])
        require(observed.tzinfo is not None and observed <= stamp, 'Notice snapshot predates observation')
    require(value['license_cleared'] is False and value['independent_accuracy_evidence'] is False, 'Notice evidence cannot promote permission or accuracy')
    require(isinstance(value['coverage'], dict) and set(value['coverage']) == COVERAGE and all(v is False for v in value['coverage'].values()), 'Unreviewed notice profile cannot promote coverage')
    require(isinstance(value['notices'], dict) and 1 <= len(value['notices']) <= 2048, 'Invalid content-addressed notice inventory')
    for digest, size in value['notices'].items():
        require(SHA.fullmatch(digest) and type(size) is int and 0 < size <= 2_000_000, 'Invalid notice inventory digest/size')
    installed = read_evidence(root / 'eval/dependencies/runtime-sbom.json')
    expected_sources = {'package-lock.json', 'site/package-lock.json', 'eval/dependencies/runtime-sbom.json', *[r['artifact'] for r in installed['images']]}
    require(isinstance(value['sources'], dict) and set(value['sources']) == expected_sources, 'Incomplete dependency source inventory')
    for path, digest in value['sources'].items():
        require(isinstance(digest, str) and SHA.fullmatch(digest) and hashlib.sha256(file_bytes(root, path, limit=8_000_000)).hexdigest() == digest, 'Dependency source drift requires recollection')
    require(hashlib.sha256(file_bytes(root, 'scripts/collect-runtime-notices.py')).hexdigest() == value['runtime_collector_sha256'], 'Runtime notice collector changed')
    require(isinstance(value['runtime'], list) and len(value['runtime']) == 3, 'Incomplete runtime notice inventory')
    expected_images = {r['role']: r['image_id'] for r in installed['images']}
    roles, runtime_count, distributions = set(), 0, 0
    for row in value['runtime']:
        require(isinstance(row, dict) and set(row) == {'role', 'image_id', 'notices', 'python_distributions'}, 'Invalid runtime notice row')
        require(row['role'] in expected_images and row['role'] not in roles and row['image_id'] == expected_images[row['role']], 'Runtime image mismatch or duplication')
        roles.add(row['role']); runtime_count += len(refs(row['notices'], value, root, 'runtime'))
        require(isinstance(row['python_distributions'], list) and len(row['python_distributions']) <= 256, 'Invalid observed Python inventory')
        names = set()
        for d in row['python_distributions']:
            require(isinstance(d, dict) and set(d) == {'name', 'version', 'license', 'license_expression'}, 'Invalid observed Python fields')
            require(all(isinstance(d[k], str) and 0 < len(d[k]) <= 200 for k in ('name', 'version')) and d['name'] not in names, 'Duplicate/invalid observed Python identity')
            require(all(d[k] is None or isinstance(d[k], str) and len(d[k]) <= 200_000 for k in ('license', 'license_expression')), 'Invalid observed license metadata')
            names.add(d['name']); distributions += 1
    expected = {}
    for lock in ('package-lock.json', 'site/package-lock.json'):
        packages = read_evidence(root / lock)['packages']
        expected.update({(lock, path): row for path, row in packages.items() if path})
    require(isinstance(value['npm'], list) and len(value['npm']) == len(expected), 'Incomplete npm artifact inventory')
    identities, missing, unknown, occurrences = set(), [], [], 0
    for row in value['npm']:
        require(isinstance(row, dict) and set(row) == {'lock', 'package_path', 'version', 'integrity', 'resolved', 'license_declared', 'optional', 'artifact_sha256', 'notices'}, 'Invalid npm observation fields')
        identity = (row['lock'], row['package_path'])
        require(identity in expected and identity not in identities, 'Unknown or duplicate npm package')
        identities.add(identity); locked = expected[identity]
        require(all(row[k] == locked.get(k) for k in ('version', 'integrity', 'resolved')) and row['license_declared'] == locked.get('license') and type(row['optional']) is bool and row['optional'] == locked.get('optional', False), 'npm observation differs from lock')
        url = urlsplit(row['resolved'])
        require(url.scheme == 'https' and url.hostname == 'registry.npmjs.org' and not (url.username or url.password or url.query or url.fragment), 'Unreviewed npm artifact origin')
        algorithm, encoded = row['integrity'].split('-', 1)
        require(algorithm in ('sha256', 'sha512') and len(base64.b64decode(encoded, validate=True)) == {'sha256':32, 'sha512':64}[algorithm] and isinstance(row['artifact_sha256'], str) and SHA.fullmatch(row['artifact_sha256']), 'Invalid npm artifact digest')
        occurrences += len(refs(row['notices'], value, root, 'npm', npm_prefix(row)))
        if not row['notices']: missing.append('/'.join(identity))
        if not row['license_declared']: unknown.append('/'.join(identity))
        if archive_dir is not None:
            key = hashlib.sha256(row['integrity'].encode()).hexdigest()
            archive = Path(archive_dir) / (key + '.tgz')
            require(not any(p.is_symlink() for p in [archive, *archive.parents]), 'Archive symlink refused')
            archive_notices(archive, row)
    referenced = {n['sha256'] for row in value['runtime'] + value['npm'] for n in row['notices']}
    require(referenced == set(value['notices']), 'Orphan or missing notice blob')
    blobs = {p.name for p in (root/'sbom/notices').iterdir() if p.name != 'manifest.json'}
    require(blobs == {digest+'.txt' for digest in referenced}, 'Unregistered notice-store entry')
    checked = {**before, **value['sources'], **{ 'sbom/notices/'+h+'.txt': h for h in referenced }}
    require(all(hashlib.sha256(file_bytes(root, name, limit=8_000_000)).hexdigest() == digest for name, digest in checked.items()), 'Notice evidence changed during execution')
    return {'captured_at': datetime.now(timezone.utc).isoformat(), 'pass': True,
            'sources': checked, 'source_unchanged_during_execution': True,
            'evidence_integrity_pass': True, 'license_release_pass': False,
            'runtime_images': len(roles), 'runtime_notice_occurrences': runtime_count,
            'observed_python_distribution_occurrences': distributions, 'npm_artifacts': len(identities),
            'npm_notice_occurrences': occurrences, 'unique_notice_blobs': len(referenced),
            'npm_packages_without_matched_notice_file': missing, 'npm_packages_without_declared_license': unknown,
            'npm_archives_rechecked': archive_dir is not None,
            'coverage_pending': sorted(COVERAGE), 'notice_presence_is_legal_permission': False,
            'tag_release_validated': False}
