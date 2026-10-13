#!/usr/bin/env python3
"""Create an offline, deterministic temporary Firefox preview without changing Chrome."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
FILES = (
    'src/shared/contract.js', 'src/shared/transport.js',
    'src/adapters/chatgpt.js', 'src/content/badge.js', 'src/content/bridge.js',
    'src/options.js', 'src/options.html', 'src/sw/service-worker.js', 'src/firefox/permissions.js',
)
IMPORTS = b"import '../shared/contract.js';\nimport '../shared/transport.js';\n"


def regular(path, limit=2_000_000):
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('Symbolic links are not package inputs')
    flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0)
    fd = os.open(path, flags)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
            raise ValueError('Invalid package source type or size')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            data = stream.read(limit + 1)
        if len(data) > limit:
            raise ValueError('Package source exceeds limit')
        return data
    finally:
        os.close(fd)


def package(root=ROOT):
    root = Path(root).absolute()
    sources = {name: regular(root / 'extension' / name) for name in ('manifest.json', *FILES)}
    license_bytes = regular(root/'LICENSE')
    if b'Apache License' not in license_bytes or b'END OF TERMS AND CONDITIONS' not in license_bytes:
        raise ValueError('Project license requires package review')
    manifest = json.loads(sources['manifest.json'])
    # Every origin/permission change requires an explicit packager review.
    if (manifest.get('manifest_version') != 3 or manifest.get('permissions') != ['storage']
            or manifest.get('host_permissions') != ['http://127.0.0.1:8787/*']
            or manifest.get('background') != {'service_worker': 'src/sw/service-worker.js', 'type': 'module'}
            or len(manifest.get('content_scripts', [])) != 1
            or manifest['content_scripts'][0].get('matches') != ['https://chatgpt.com/*']
            or set(manifest['content_scripts'][0]) != {'matches', 'js', 'world', 'run_at'}
            or manifest['content_scripts'][0].get('world') != 'ISOLATED'
            or manifest['content_scripts'][0].get('run_at') != 'document_idle'
            or manifest['content_scripts'][0].get('js') != [
                'src/shared/contract.js', 'src/adapters/chatgpt.js',
                'src/content/badge.js', 'src/content/bridge.js']
            or manifest.get('options_page') != 'src/options.html'
            or set(manifest) != {'manifest_version', 'name', 'version', 'description',
                'minimum_chrome_version', 'permissions', 'host_permissions', 'background',
                'content_scripts', 'options_page'}):
        raise ValueError('Unreviewed extension manifest')
    worker = sources['src/sw/service-worker.js']
    if not worker.startswith(IMPORTS) or b'import ' in worker[len(IMPORTS):]:
        raise ValueError('Unreviewed background module imports')
    manifest.pop('minimum_chrome_version')
    manifest['host_permissions'] = ['https://chatgpt.com/*', 'http://127.0.0.1/*']
    manifest['background'] = {'scripts': [
        'src/shared/contract.js', 'src/shared/transport.js', 'src/sw/service-worker.js']}
    manifest['browser_specific_settings'] = {'gecko': {
        'id': 'preview@aitrustid.com', 'strict_min_version': '140.0',
        'data_collection_permissions': {'required': ['none']}}}
    manifest['description'] = 'Temporary Firefox research preview: local assistant-response checks on ChatGPT.'
    options = sources['src/options.html']
    marker = b'<script src="options.js"></script>'
    if options.count(marker) != 1:
        raise ValueError('Unreviewed options script order')
    options = options.replace(marker, b'<script src="firefox/permissions.js"></script>' + marker)
    members = {**sources, 'LICENSE': license_bytes, 'src/options.html': options, 'manifest.json': (json.dumps(manifest, indent=2) + '\n').encode(),
               'src/sw/service-worker.js': worker[len(IMPORTS):]}
    buffer = io.BytesIO()
    # Fixed metadata and uncompressed data avoid host/zlib-dependent output.
    with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_STORED) as archive:
        for name, data in sorted(members.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(info, data)
    if any(regular(root / 'extension' / name) != data for name, data in sources.items()):
        raise ValueError('Package sources changed while building')
    if regular(root/'LICENSE') != license_bytes:
        raise ValueError('License changed while building')
    archive = buffer.getvalue()
    return archive, {'profile': 'firefox-temporary-preview/v1',
        'sha256': hashlib.sha256(archive).hexdigest(), 'bytes': len(archive),
        'sources': {'extension/' + name: hashlib.sha256(data).hexdigest()
                    for name, data in sources.items()} | {'LICENSE': hashlib.sha256(license_bytes).hexdigest()},
        'members': {name: hashlib.sha256(data).hexdigest() for name, data in sorted(members.items())},
        'store_signed': False, 'live_vendor_verified': False,
        'independent_accuracy_evidence': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'output/firefox/aitrust-id-preview.zip')
    args = parser.parse_args()
    data, evidence = package()
    destination = args.output.absolute()
    if any(p.is_symlink() for p in (destination, *destination.parents)):
        raise ValueError('Output links refused')
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Never silently replace an owner's file. Identical existing output is reusable.
    try:
        with destination.open('xb') as stream:
            stream.write(data)
    except FileExistsError:
        if regular(destination) != data:
            raise ValueError('Existing output differs; choose a new destination')
    print(json.dumps(evidence, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
        print('Firefox package refused; source and existing output were preserved.', file=sys.stderr)
        raise SystemExit(1)
