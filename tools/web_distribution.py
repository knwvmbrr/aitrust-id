"""Deliver exact selected website npm notices; never grant whole-project clearance."""
import base64
from datetime import datetime, timezone
import gzip
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import tarfile
import tempfile
from urllib.parse import urlsplit

from tools.dependency_policy import read

ROOT = Path(__file__).resolve().parents[1]
PROFILE = 'website-npm-notice-delivery/v1'
DESTINATION = 'site/public/web-licenses'
OUTPUTS = ('THIRD-PARTY-NOTICES.txt', 'packages.json', 'web-runtime.spdx.json')
SOURCES = ('site/package.json', 'site/package-lock.json', 'sbom/notices/manifest.json',
           'tools/web_distribution.py', 'scripts/web-distribution.py', 'tools/dependency_policy.py', 'LICENSE', 'NOTICE',
           'sbom/reviews/web-js/react-remove-scroll-bar-2.3.8.json',
           'sbom/reviews/web-js/sources/a79aae0c0f21990d9d963bb3c5a79cdcea9a46f8523ba55c58d7fe776b6ebc84.txt')
SHA = re.compile(r'[a-f0-9]{64}')
NAME = re.compile(r'(?:@[a-z0-9_.-]+/)?[a-z0-9_.-]+')
MAX_JSON = 2_000_000
MAX_NOTICE = 2_000_000
MAX_BUNDLE = 16_000_000
MAX_COMPRESSED = 16_000_000
MAX_EXPANDED = 32_000_000
MAX_ARCHIVE_TOTAL = 128_000_000


class NoticeError(ValueError):
    """Only fixed public diagnostics cross the command boundary."""


def require(value):
    if not value:
        raise NoticeError('Website notice check refused')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, allow_nan=False,
                      separators=(',', ':')).encode()


def unique(rows):
    result = {}
    for key, value in rows:
        require(key not in result)
        result[key] = value
    return result


def load(raw):
    require(len(raw) <= MAX_JSON)
    value = json.loads(raw.decode('utf-8'), object_pairs_hook=unique,
                       parse_constant=lambda _: require(False))
    count = 0

    def walk(item, depth=0):
        nonlocal count
        count += 1
        require(depth <= 40 and count <= 100_000)
        if isinstance(item, dict):
            for key, child in item.items():
                key.encode('utf-8', errors='strict')
                walk(child, depth + 1)
        elif isinstance(item, list):
            for child in item:
                walk(child, depth + 1)
        elif isinstance(item, str):
            item.encode('utf-8', errors='strict')
    walk(value)
    return value


def supplemental(row, raw):
    """One explicit unresolved exact-release gap, never a generic MIT fallback."""
    require(row['package_path'] == 'node_modules/react-remove-scroll-bar' and row['version'] == '2.3.8' and
            row['artifact_sha256'] == 'ccc872d7a2dc007cbf9d755f30d56b8d80eabdbe22c44c95a709129bfdc46f01' and
            row['license_declared'] == 'MIT' and row['notices'] == [])
    meta = load(raw[SOURCES[-2]])
    require(type(meta) is dict and meta.get('profile') == 'selected-npm-supplemental-project-license/v1' and
            meta.get('package') == 'react-remove-scroll-bar' and meta.get('version') == '2.3.8' and
            meta.get('archive_sha256') == row['artifact_sha256'] and
            meta.get('claims') == {'exact_release_source_relationship_verified':False,
                'exact_release_license_correspondence_verified':False, 'archive_carried_license':False,
                'legal_clearance':False, 'release_approved':False} and
            all(type(v) is bool for v in meta['claims'].values()))
    registry = meta.get('registry_metadata'); source = meta.get('upstream_project_license')
    require(type(registry) is dict and registry.get('integrity') == row['integrity'] and
            registry.get('gitHead') == 'b3b1287aad81def2e2ae707274b74531b61ddbaf' and
            registry.get('declared_license') == 'MIT' and registry.get('signature_verified') is False and
            registry.get('url') == 'https://registry.npmjs.org/react-remove-scroll-bar/2.3.8' and
            type(source) is dict and source.get('commit') == '8ca9ba5ea52de03308fe8ced94f7b159a44d28ff' and
            source.get('path') == SOURCES[-1] and type(source.get('bytes')) is int and source['bytes'] == 1093 and
            source.get('url') == 'https://raw.githubusercontent.com/theKashey/react-remove-scroll-bar/8ca9ba5ea52de03308fe8ced94f7b159a44d28ff/LICENSE' and
            source.get('sha256') == 'a79aae0c0f21990d9d963bb3c5a79cdcea9a46f8523ba55c58d7fe776b6ebc84')
    require(meta.get('exact_gitHead_source_request') == {
                'url':'https://raw.githubusercontent.com/theKashey/react-remove-scroll-bar/b3b1287aad81def2e2ae707274b74531b61ddbaf/LICENSE',
                'observed_http_status':404, 'correspondence_established':False} and
            type(meta.get('upstream_package')) is dict and meta['upstream_package'].get('observed_version') == '2.3.7')
    value = raw[SOURCES[-1]]
    require(len(value) == source['bytes'] and digest(value) == source['sha256'] and
            hashlib.sha1(b'blob '+str(len(value)).encode()+b'\0'+value).hexdigest() == source.get('git_blob_sha1'))
    return {'source_path':'upstream-project/LICENSE', 'sha256':source['sha256'], 'bytes':len(value),
            'notice':source['path'], 'text':value, 'origin':'supplemental_upstream_project_notice',
            'source_url':source['url']}


def selected(root=ROOT):
    """Select the lock's non-dev cohort, without requiring unrelated runtimes."""
    raw = {name: read(root, name, MAX_JSON) for name in SOURCES}
    lock = load(raw['site/package-lock.json'])
    package = load(raw['site/package.json'])
    manifest = load(raw['sbom/notices/manifest.json'])
    require(type(lock) is dict and type(lock.get('lockfileVersion')) is int and lock['lockfileVersion'] == 3 and
            type(lock.get('packages')) is dict and 1 < len(lock['packages']) <= 512)
    require(type(package) is dict and type(package.get('dependencies')) is dict)
    lock_root = lock['packages'].get('')
    require(type(lock_root) is dict and type(lock_root.get('dependencies')) is dict and
            lock_root['dependencies'] == package['dependencies'] and
            0 < len(lock_root['dependencies']) <= 128)
    for name, version in lock_root['dependencies'].items():
        require(type(name) is str and len(name) <= 160 and NAME.fullmatch(name) and
                type(version) is str and 0 < len(version) <= 160)
        dependency = lock['packages'].get('node_modules/' + name)
        require(type(dependency) is dict and dependency.get('dev') is not True)
    require(type(manifest) is dict and manifest.get('kind') == 'observed_notice_evidence' and
            manifest.get('license_cleared') is False and manifest.get('independent_accuracy_evidence') is False and
            type(manifest.get('sources')) is dict and
            manifest['sources'].get('site/package-lock.json') == digest(raw['site/package-lock.json']) and
            type(manifest.get('npm')) is list and len(manifest['npm']) <= 1024 and
            type(manifest.get('notices')) is dict)
    observed = {}
    for row in manifest['npm']:
        require(type(row) is dict)
        if row.get('lock') == 'site/package-lock.json':
            key = row.get('package_path')
            require(type(key) is str and key not in observed)
            observed[key] = row
    cohort = []
    for path, locked in sorted(lock['packages'].items()):
        if not path:
            continue
        require(type(path) is str and type(locked) is dict and
                ('dev' not in locked or type(locked['dev']) is bool))
        if locked.get('dev') is True:
            continue
        name = path.rsplit('node_modules/', 1)[-1]
        require(path == 'node_modules/' + name and NAME.fullmatch(name) and len(name) <= 160)
        row = observed.get(path)
        require(row is not None and set(row) == {'lock', 'package_path', 'version', 'integrity',
                'resolved', 'license_declared', 'optional', 'artifact_sha256', 'notices'})
        require(all(row[key] == locked.get(key) for key in ('version', 'integrity', 'resolved')) and
                type(row['version']) is str and 0 < len(row['version']) <= 80 and
                type(row['integrity']) is str and 1 <= len(row['integrity']) <= 256 and
                type(row['resolved']) is str and 1 <= len(row['resolved']) <= 512 and
                type(row['optional']) is bool and row['optional'] == locked.get('optional', False) and
                row['license_declared'] == locked.get('license') and
                type(row['license_declared']) is str and 0 < len(row['license_declared']) <= 160 and
                type(row['artifact_sha256']) is str and SHA.fullmatch(row['artifact_sha256']))
        url = urlsplit(row['resolved'])
        require(url.scheme == 'https' and url.netloc == 'registry.npmjs.org' and
                not (url.query or url.fragment or url.username or url.password))
        algorithm, encoded = row['integrity'].split('-', 1)
        require(algorithm in ('sha256', 'sha512') and
                len(base64.b64decode(encoded, validate=True)) == {'sha256':32, 'sha512':64}[algorithm])
        require(type(row['notices']) is list and len(row['notices']) <= 32)
        members = set(); notices = []
        for notice in row['notices']:
            require(type(notice) is dict and set(notice) == {'source_path', 'sha256', 'bytes', 'notice'})
            member = notice['source_path']; sha = notice['sha256']
            require(type(member) is str and 0 < len(member) <= 512 and member.startswith('package/') and
                    '\\' not in member and all(p not in ('', '.', '..') for p in member.split('/')) and
                    member not in members and type(sha) is str and SHA.fullmatch(sha) and
                    notice['notice'] == 'sbom/notices/' + sha + '.txt' and
                    type(notice['bytes']) is int and 0 < notice['bytes'] <= MAX_NOTICE and
                    manifest['notices'].get(sha) == notice['bytes'])
            members.add(member)
            value = read(root, notice['notice'], MAX_NOTICE)
            require(len(value) == notice['bytes'] and digest(value) == sha)
            value.decode('utf-8', errors='strict')
            raw[notice['notice']] = value
            notices.append({**notice, 'text': value, 'origin':'archive_notice'})
        archive_notices = list(notices)
        if not notices:
            notices = [supplemental(row, raw)]
        cohort.append({**row, 'name': name, 'archive_notices':archive_notices, 'notices': notices,
                       'supplemental_project_notice':not bool(archive_notices)})
    require(0 < len(cohort) <= 128)
    npm_timestamp = datetime.fromisoformat(manifest['npm_observed_at'])
    timestamp = datetime.fromisoformat(load(raw[SOURCES[-2]])['captured_at'])
    require(npm_timestamp.tzinfo is not None and timestamp.tzinfo is not None and
            npm_timestamp <= timestamp <= datetime.now(timezone.utc))
    return raw, cohort, timestamp.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def expected(root=ROOT):
    raw, cohort, observed_at = selected(root)
    source_hashes = {name: digest(value) for name, value in sorted(raw.items())}
    bundle = bytearray(b'AI TRUST ID - website JavaScript dependency notices\n\n'
        b'Retained attribution for the site lock non-development cohort.\n'
        b'Archive-carried notices and separately pinned project supplements are distinguished below.\n'
        b'This may include tree-shaken packages. It is not complete dependency, source-offer\n'
        b'or legal clearance. Archive identity is observed; no package is executed here.\n'
        b'Package bindings: packages.json; selected-cohort SPDX: web-runtime.spdx.json\n\n'
        b'First-party attribution (project license: ../reference/code-license.txt):\n')
    bundle.extend(raw['NOTICE']); bundle.extend(b'\n')
    packages = []; spdx = []
    for row in cohort:
        bundle.extend(('\n' + '=' * 72 + '\n' + row['name'] + '@' + row['version'] +
                       '\nArchive: ' + row['resolved'] + '\nDeclared license: ' +
                       row['license_declared'] + '\n').encode('utf-8'))
        if row['supplemental_project_notice']:
            bundle.extend(b'\nSUPPLEMENTAL UPSTREAM PROJECT LICENSE, NOT AN EXACT-RELEASE NOTICE MATCH.\n'
                b'The 2.3.8 archive has no matched full notice. Its registry gitHead was not retrievable.\n'
                b'Text below is pinned to a separate upstream project commit whose package is 2.3.7.\n'
                b'Exact 2.3.8 source/license correspondence remains UNVERIFIED. No clearance is implied.\n')
        notices = []
        for item in sorted(row['notices'], key=lambda item: item['source_path']):
            label = 'Upstream project file: ' if row['supplemental_project_notice'] else 'Original archive member: '
            bundle.extend(('\n' + label + item['source_path'] + '\n').encode())
            start = len(bundle); bundle.extend(item['text']); end = len(bundle); bundle.extend(b'\n')
            notices.append({key:item[key] for key in ('source_path', 'sha256', 'bytes', 'notice')} |
                           {'bundle_byte_span':[start, end], 'origin':item['origin']})
        packages.append({key:row[key] for key in ('package_path', 'name', 'version', 'integrity',
                         'resolved', 'license_declared', 'artifact_sha256')} | {'notices':notices, 'supplemental_project_notice':row['supplemental_project_notice'],
                         'exact_release_notice_relationship_complete':not row['supplemental_project_notice']})
        spdx.append({'SPDXID':'SPDXRef-Package-' + digest(row['package_path'].encode())[:20],
                     'name':row['name'], 'versionInfo':row['version'], 'downloadLocation':row['resolved'],
                     'filesAnalyzed':False, 'licenseConcluded':'NOASSERTION',
                     'licenseDeclared':row['license_declared'], 'copyrightText':'NOASSERTION',
                     'checksums':[{'algorithm':'SHA256', 'checksumValue':row['artifact_sha256']}],
                     'comment':'Exact locked archive observation; complete retained notices are mapped by packages.json. '
                               'Not proof that every module ships or that all source/native/runtime obligations are complete.' +
                               (' Supplemental upstream project text; exact 2.3.8 source/license correspondence is UNVERIFIED.'
                                if row['supplemental_project_notice'] else '')})
    require(len(bundle) <= MAX_BUNDLE)
    index = {'profile':PROFILE, 'sources_sha256':source_hashes, 'package_count':len(packages),
             'selection':'Every non-development site/package-lock.json entry; may include tree-shaken packages.',
             'packages':packages, 'archive_notice_packages':sum(bool(row['archive_notices']) for row in cohort),
             'supplemental_project_notice_packages':sum(row['supplemental_project_notice'] for row in cohort),
             'exact_release_notice_gap_packages':[row['name']+'@'+row['version'] for row in cohort if row['supplemental_project_notice']],
             'notice_bundle_sha256':digest(bundle),
             'notice_bundle_bytes':len(bundle),
             'related_files':{'notice_bundle':'THIRD-PARTY-NOTICES.txt', 'selected_cohort_spdx':'web-runtime.spdx.json',
                              'project_license':'../reference/code-license.txt'},
             'claims':{'legal_clearance':False, 'complete_bundle_graph':False,
                       'complete_source_offers':False, 'release_approved':False}}
    sbom = {'spdxVersion':'SPDX-2.3', 'dataLicense':'CC0-1.0', 'SPDXID':'SPDXRef-DOCUMENT',
            'name':'AI Trust ID selected website npm notice cohort',
            'documentNamespace':'urn:aitrustid:spdx:web-npm:' + digest(canonical(source_hashes)),
            'creationInfo':{'creators':['Tool: AITrust-ID-web-notices-1.0'], 'created':observed_at,
                            'comment':'Deterministic creation timestamp anchored to the retained source-review profile, not a new build or release.'},
            'packages':spdx, 'documentDescribes':[p['SPDXID'] for p in spdx]}
    outputs = {OUTPUTS[0]:bytes(bundle), OUTPUTS[1]:json.dumps(index, indent=2, ensure_ascii=True).encode()+b'\n',
               OUTPUTS[2]:json.dumps(sbom, indent=2, ensure_ascii=True).encode()+b'\n'}
    require(all(read(root, name, MAX_JSON) == value for name, value in raw.items()))
    return outputs, index


def existing_directory(path):
    require(not path.is_symlink())
    if not path.exists():
        return None
    before = path.stat()
    require(stat.S_ISDIR(before.st_mode) and before.st_uid == os.getuid() and
            {p.name for p in path.iterdir()} == set(OUTPUTS))
    for item in path.iterdir():
        info = item.lstat()
        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_uid == os.getuid() and
                0 < info.st_size <= MAX_BUNDLE)
    return before.st_dev, before.st_ino


def prepare(root=ROOT):
    root = Path(root).absolute(); outputs, index = expected(root)
    parent = root / 'site/public'
    require(not any(p.is_symlink() for p in (parent, *parent.parents)) and parent.is_dir())
    target = root / DESTINATION
    original = existing_directory(target)
    if original and all(read(root, DESTINATION+'/'+name, MAX_BUNDLE) == value for name, value in outputs.items()):
        return report(outputs, index, 'already_current')
    private = root / 'output' / 'web-notice-preparation'
    require(not any(p.is_symlink() for p in (private, *private.parents)))
    private.mkdir(parents=True, exist_ok=True, mode=0o700)
    require(private.stat().st_uid == os.getuid() and stat.S_IMODE(private.stat().st_mode) == 0o700)
    temporary = Path(tempfile.mkdtemp(prefix='new-', dir=private)); backup = None
    try:
        for name, value in outputs.items():
            with (temporary/name).open('xb') as stream:
                stream.write(value); stream.flush(); os.fsync(stream.fileno())
        require({p.name for p in temporary.iterdir()} == set(OUTPUTS))
        require(all((temporary/name).read_bytes() == value for name, value in outputs.items()))
        require(expected(root)[0] == outputs and existing_directory(target) == original)
        if original:
            backup = Path(tempfile.mkdtemp(prefix='old-', dir=private)); backup.rmdir()
            os.rename(target, backup)
        try:
            os.rename(temporary, target)
            require(expected(root)[0] == outputs)
        except BaseException:
            if target.exists() and not temporary.exists():
                os.rename(target, temporary)
            if backup is not None:
                os.rename(backup, target); backup = None
            raise
        cleanup = True
        if backup is not None:
            try:
                shutil.rmtree(backup); backup = None
            except OSError:
                cleanup = False
        return report(outputs, index, 'prepared') | {'old_output_cleanup_complete':cleanup}
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)


def report(outputs, index, action):
    return {'profile':PROFILE, 'pass':True, 'action':action, 'packages':index['package_count'],
            'archive_notice_packages':index['archive_notice_packages'],
            'supplemental_project_notice_packages':index['supplemental_project_notice_packages'],
            'exact_release_notice_gap_packages':index['exact_release_notice_gap_packages'],
            'artifacts':{name:{'bytes':len(value), 'sha256':digest(value)} for name,value in outputs.items()},
            'sources_sha256':index['sources_sha256'], 'legal_clearance':False,
            'complete_bundle_graph':False, 'complete_source_offers':False,
            'release_approved':False, 'independent_accuracy_evidence':False}


def check_built(root=ROOT, artifact_dir=None):
    outputs, index = expected(root)
    artifact = Path(root) / 'site/dist' if artifact_dir is None else Path(artifact_dir)
    for name, value in outputs.items():
        require(read(artifact, 'web-licenses/'+name, MAX_BUNDLE) == value)
    require(read(artifact, 'reference/code-license.txt', MAX_JSON) == read(root, 'LICENSE', MAX_JSON))
    require(expected(root)[0] == outputs)
    return report(outputs, index, 'built_artifact_notice_bytes_verified')


def replay_archives(archive_dir, root=ROOT):
    """Offline archive replay: cap expanded bytes before tarfile parses metadata."""
    raw_sources, cohort, _ = selected(root); total = 0
    base = Path(archive_dir).absolute()
    require(not any(p.is_symlink() for p in (base, *base.parents)) and base.is_dir())
    for row in cohort:
        key = digest(row['integrity'].encode())
        archive = read(base, key + '.tgz', MAX_COMPRESSED)
        algorithm, encoded = row['integrity'].split('-', 1)
        require(digest(archive) == row['artifact_sha256'] and
                hashlib.new(algorithm, archive).digest() == base64.b64decode(encoded, validate=True))
        with gzip.GzipFile(fileobj=io.BytesIO(archive)) as compressed:
            expanded = compressed.read(MAX_EXPANDED + 1)
        total += len(expanded)
        require(0 < len(expanded) <= MAX_EXPANDED and total <= MAX_ARCHIVE_TOTAL)
        observed = {}; count = 0
        with tarfile.open(fileobj=io.BytesIO(expanded), mode='r:') as tar:
            for member in tar:
                count += 1; require(count <= 8192)
                require(member.isdir() or member.isfile())
                require(member.name.startswith('package/') and '\\' not in member.name and
                        all(part not in ('', '.', '..') for part in member.name.rstrip('/').split('/')))
                if not member.isfile() or not re.fullmatch(r'(?:licen[sc]e|copying|copyright|notice)(?:[._-].*)?', PurePosixPath(member.name).name, re.I):
                    continue
                require(member.name not in observed and 0 < member.size <= MAX_NOTICE)
                value = tar.extractfile(member).read(MAX_NOTICE + 1)
                require(len(value) == member.size)
                try:value.decode('utf-8', errors='strict')
                except UnicodeError:continue
                observed[member.name] = value
        require(observed == {n['source_path']:n['text'] for n in row['archive_notices']})
    require(all(read(root, name, MAX_JSON) == value for name,value in raw_sources.items()))
    return {'profile':PROFILE, 'pass':True, 'action':'offline_selected_archive_replay',
            'archives':len(cohort), 'expanded_bytes':total,
            'archive_notice_packages':sum(bool(row['archive_notices']) for row in cohort),
            'supplemental_project_notice_packages':sum(row['supplemental_project_notice'] for row in cohort),
            'exact_release_source_correspondence_verified':False,
            'sources_sha256':{name:digest(value) for name,value in raw_sources.items()},
            'lock_integrity_and_archive_sha256_verified':True, 'complete_notice_bytes_compared':True,
            'package_code_executed':False, 'network_used':False, 'legal_clearance':False,
            'release_approved':False}


def release_check(root=ROOT, artifact_dir=None):
    result = check_built(root, artifact_dir)
    from tools.dependency_policy import evaluate
    policy = evaluate('web-checker', root)
    return {**result, 'pass':policy['release_allowed'], 'action':'reviewed_release_gate',
            'distribution_status':policy['status'], 'release_approved':False,
            'reason':'Other website runtime, native, build and source obligations remain separately reviewed.'}
