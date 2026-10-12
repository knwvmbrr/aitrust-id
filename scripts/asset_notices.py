"""Bounded asset/notice consistency. Never license clearance or tag validation."""
from datetime import datetime, timezone
import base64
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import tarfile

ROOT = Path(__file__).resolve().parents[1]
SHA = re.compile(r'[a-f0-9]{64}')
PROFILE = 'selected-asset-notices/v1'
MANIFEST = 'sbom/assets/notices.json'
UNICODE = 'eval/vectors/unicode/LICENSE.txt'
UNICODE_COPY = 'site/public/device-licenses/unicode-license.txt'
NORMALIZATION = ('protocol/unicode15-data.json', 'protocol/normalization.py',
                 'protocol/normalization-core.js', 'protocol/normalization.mjs', 'protocol/normalization.cjs')
RUNTIME_NOTICES = ('site/public/device-licenses/pyodide-MPL-2.0.txt',
                   'site/public/device-licenses/python-license.txt', 'site/public/device-licenses/source.txt')
MODEL_CARD = 'research/nli/notices/4aeb5585a9eeb71b2d572249f9faa22ef3378c6abee3eeaffaae8c961068a2c6.txt'
RUNTIME_FILES = ('pyodide.mjs', 'pyodide.asm.mjs', 'pyodide.asm.wasm', 'python_stdlib.zip', 'pyodide-lock.json')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read(root, relative, limit=2_097_152):
    require(isinstance(relative, str) and relative and '\\' not in relative and
            not PurePosixPath(relative).is_absolute() and '..' not in PurePosixPath(relative).parts,
            'Unsafe asset path')
    file = root / relative
    require(not any(p.is_symlink() for p in [file, *file.parents]), 'Asset link refused')
    # Use the project's bounded descriptor reader. No network, extraction or execution.
    from protocol.corpus import read_regular
    return read_regular(file, limit)


def load(root, relative):
    from protocol.evidence import unique, reject, finite
    value = json.loads(read(root, relative).decode('utf-8'), object_pairs_hook=unique, parse_constant=reject)
    finite(value)
    require(isinstance(value, dict), 'Asset metadata must be an object')
    return value


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def selected(root):
    fonts = load(root, 'site/public/fonts/provenance.json')
    require(set(fonts) == {'family', 'license', 'distribution_version', 'css_source', 'browser_font_requests', 'assets'}
            and fonts['family'] == 'Nunito Sans' and fonts['license'] == 'SIL Open Font License 1.1'
            and fonts['browser_font_requests'] == 'self-hosted only'
            and fonts['distribution_version'] == 'Google Fonts v19'
            and isinstance(fonts['css_source'], str) and fonts['css_source'].startswith('https://fonts.googleapis.com/css2?family=Nunito+Sans:'), 'Unreviewed font profile')
    require(isinstance(fonts['assets'], list) and len(fonts['assets']) == 6, 'Font inventory count changed')
    require(all(isinstance(row, dict) for row in fonts['assets']), 'Font row type')
    names = set(); rows = []
    for row in fonts['assets']:
        require(set(row) == {'file', 'source', 'sha256', 'bytes'} and isinstance(row['file'], str), 'Font identity fields')
        name = row['file']; require(name not in names and (name == 'OFL.txt' or re.fullmatch(r'nunito-sans-[a-z-]+\.woff2', name)), 'Font filename changed')
        permitted_source = ('https://raw.githubusercontent.com/google/fonts/8b0a1d0f5983c89bc2b93f1b5fb55f9e252744b5/ofl/nunitosans/OFL.txt' if name == 'OFL.txt' else 'https://fonts.gstatic.com/s/nunitosans/v19/')
        require(isinstance(row['source'], str) and row['source'].startswith(permitted_source)
                and isinstance(row['sha256'], str) and SHA.fullmatch(row['sha256']) and type(row['bytes']) is int
                and 0 < row['bytes'] <= 524288, 'Font identity unsupported')
        names.add(name); raw = read(root, 'site/public/fonts/' + name, 524288)
        require(digest(raw) == row['sha256'] and len(raw) == row['bytes'], 'Font bytes differ from observation')
        rows.append(('font_or_notice', 'site/public/fonts/' + name, ['site/public/fonts/OFL.txt']))
    require(sum(n.endswith('.woff2') for n in names) == 5 and 'OFL.txt' in names, 'Font families changed')
    rows.append(('font_css', 'site/public/fonts/nunito-sans.css', ['site/public/fonts/OFL.txt']))
    rows += [('unicode_consumer', name, [UNICODE, UNICODE_COPY]) for name in NORMALIZATION]
    require(read(root, UNICODE) == read(root, UNICODE_COPY), 'Bundled Unicode notice differs or is absent')
    rows += [('runtime_notice', name, [name]) for name in RUNTIME_NOTICES]
    model = load(root, 'research/nli/assets.json')
    require(set(model) == {'profile', 'revision', 'files', 'independently_audited'}
            and model['profile'] == 'pinned-nli-assets/1.0.0' and model['independently_audited'] is False
            and model['revision'] == 'a150876415327c80daeff35ca6f68f5ed8cf5c24', 'Unreviewed model profile')
    require(isinstance(model['files'], list) and len(model['files']) == 4, 'Model artifact count changed')
    require(all(isinstance(row, dict) for row in model['files']), 'Model row type')
    card = next((x for x in model['files'] if x.get('name') == 'README.md'), None)
    require(card is not None and card['sha256'] == digest(read(root, MODEL_CARD)) and card['bytes'] == len(read(root, MODEL_CARD)), 'Model-card identity changed')
    require(read(root, MODEL_CARD).startswith(b'---\n') and b'\nlicense: apache-2.0\n' in read(root, MODEL_CARD).split(b'\n---', 1)[0], 'Model declaration changed')
    for row in model['files']:
        require(set(row) == {'name', 'bytes', 'sha256', 'url'} and row['name'] in {'model.onnx', 'tokenizer.json', 'config.json', 'README.md'}
                and type(row['bytes']) is int and 0 < row['bytes'] <= 300_000_000 and isinstance(row['sha256'], str)
                and SHA.fullmatch(row['sha256']) and isinstance(row['url'], str)
                and row['url'].startswith('https://huggingface.co/cross-encoder/nli-deberta-v3-xsmall/resolve/' + model['revision'] + '/'), 'Model identity unsupported')
    require(len({row['name'] for row in model['files']}) == 4, 'Duplicate model artifact')
    rows.append(('optional_model_card_only', MODEL_CARD, [MODEL_CARD]))
    return sorted(rows), model


def inventory(root):
    rows, model = selected(root)
    result = []
    for family, name, notices in rows:
        raw = read(root, name)
        result.append({'family': family, 'path': name, 'sha256': digest(raw), 'bytes': len(raw),
                       'notices': [{'path': n, 'sha256': digest(read(root, n)), 'bytes': len(read(root, n))} for n in notices],
                       'permission_cleared': False})
    return result, model


def runtime_origin(root):
    lock = load(root, 'site/package-lock.json')['packages']['node_modules/pyodide']
    require(lock['version'] == '314.0.7' and lock['resolved'] == 'https://registry.npmjs.org/pyodide/-/pyodide-314.0.7.tgz'
            and isinstance(lock['integrity'], str) and lock['integrity'].startswith('sha512-'), 'Runtime lock identity changed')
    rows = load(root, 'sbom/notices/manifest.json')['npm']
    require(isinstance(rows, list) and all(isinstance(row, dict) for row in rows), 'Runtime notice inventory type')
    row = next((r for r in rows if r['lock'] == 'site/package-lock.json' and r['package_path'] == 'node_modules/pyodide'), None)
    require(row is not None and all(row[k] == lock[k] for k in ('version', 'resolved', 'integrity'))
            and isinstance(row['artifact_sha256'], str) and SHA.fullmatch(row['artifact_sha256']), 'Runtime notice inventory differs from lock')
    return {k: row[k] for k in ('version', 'resolved', 'integrity', 'artifact_sha256')}


def runtime_members(raw, origin):
    require(isinstance(raw, bytes) and len(raw) <= 52_428_800 and digest(raw) == origin['artifact_sha256']
            and hashlib.sha512(raw).digest() == base64.b64decode(origin['integrity'].removeprefix('sha512-'), validate=True), 'Runtime archive differs from lock/observation')
    found = {}; total = 0; count = 0
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r|gz') as package:
        for member in package:
            total += member.size; count += 1
            require(0 <= member.size and total <= 536_870_912 and count <= 100_000, 'Runtime archive bounds')
            if member.name not in {'package/' + n for n in RUNTIME_FILES}: continue
            require(member.isfile() and member.name.removeprefix('package/') not in found and member.size <= 33_554_432, 'Runtime member unsupported or duplicated')
            data = package.extractfile(member).read(); require(len(data) == member.size, 'Runtime member truncated')
            name = member.name.removeprefix('package/')
            found[name] = {'name': name, 'member': member.name, 'sha256': digest(data), 'bytes': len(data)}
    require(set(found) == set(RUNTIME_FILES), 'Runtime archive incomplete')
    return [found[name] for name in RUNTIME_FILES]


def verify(root=ROOT, prepared_runtime=False, runtime_archive=None):
    root = Path(root).resolve(); value = load(root, MANIFEST)
    require(set(value) == {'profile', 'captured_at', 'reviewed_by', 'sources', 'assets', 'optional_model_references', 'runtime_origin', 'runtime_members', 'permission_cleared', 'full_dependency_coverage'}, 'Asset manifest fields changed')
    require(value['profile'] == PROFILE and value['reviewed_by'] == 'Codex' and value['permission_cleared'] is False
            and value['full_dependency_coverage'] is False, 'Unsupported clearance or coverage claim')
    when = datetime.fromisoformat(value['captured_at']); require(when.tzinfo is not None and when <= datetime.now(timezone.utc), 'Asset review date refused')
    sources = value['sources']; require(isinstance(sources, dict) and set(sources) == {'site/public/fonts/provenance.json', 'research/nli/assets.json', 'scripts/asset_notices.py', 'site/package-lock.json', 'sbom/notices/manifest.json'}, 'Asset review source set changed')
    before = {name: digest(read(root, name)) for name in sources}
    require(before == sources, 'Asset review source changed')
    rows, model = inventory(root)
    require(value['assets'] == rows and value['optional_model_references'] == model['files'], 'Asset/notice binding changed')
    origin = runtime_origin(root); require(value['runtime_origin'] == origin, 'Runtime origin changed')
    members = value['runtime_members']; require(isinstance(members, list) and len(members) == 5, 'Runtime fingerprint count')
    for name, row in zip(RUNTIME_FILES, members):
        require(set(row) == {'name', 'member', 'sha256', 'bytes'} and row['name'] == name and row['member'] == 'package/' + name
                and isinstance(row['sha256'], str) and SHA.fullmatch(row['sha256']) and type(row['bytes']) is int
                and 0 < row['bytes'] <= 33_554_432, 'Runtime fingerprint fields')
    archive_observed = False
    if runtime_archive is not None:
        from protocol.corpus import read_regular
        require(runtime_members(read_regular(Path(runtime_archive), 52_428_800), origin) == members, 'Runtime extraction differs from retained observation')
        archive_observed = True
    runtime_count = 0
    if prepared_runtime:
        vendor = (root / 'site/node_modules/pyodide').resolve(strict=True)
        version = load(vendor, 'package.json')['version']
        require(version == '314.0.7', 'Installed runtime changed')
        for row in members:
            name = row['name']
            actual = read(root, 'site/public/device/runtime-314.0.7/' + name, 33_554_432)
            require(digest(actual) == row['sha256'] and len(actual) == row['bytes']
                    and actual == read(vendor, name, 33_554_432), 'Prepared runtime differs')
            runtime_count += 1
    require({name: digest(read(root, name)) for name in sources} == before and inventory(root) == (rows, model), 'Sources changed during asset check')
    return {'captured_at': datetime.now(timezone.utc).isoformat(), 'author': 'Codex', 'pass': True,
            'asset_bindings': len(rows), 'font_files': 5, 'font_css_files': 1, 'unicode_consumers': len(NORMALIZATION),
            'bundled_unicode_notice_matched': True, 'runtime_notices': len(RUNTIME_NOTICES),
            'prepared_runtime_files_matched': runtime_count, 'runtime_byte_comparison_requested': prepared_runtime,
            'runtime_origin_archive_reprocessed': archive_observed,
            'optional_model_card_matched': True, 'optional_model_weights_observed_by_this_check': False,
            'optional_model_artifact_references': len(model['files']), 'sources_sha256': before,
            'permission_cleared': False, 'full_dependency_coverage': False, 'license_release_pass': False,
            'independent_accuracy_evidence': False,
            'scope': 'Selected asset/notice consistency only; not all native/transitive components, model weights, architectures, source offers, legal permission or tag validation.'}
