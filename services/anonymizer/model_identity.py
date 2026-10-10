"""Verify the build-sealed English model before any model code or weights load."""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path, PurePosixPath
import stat

MODEL_NAME = 'en_core_web_sm'
MODEL_VERSION = '3.8.0'
FORMAT = 'model-assets/v1'
MAX_FILES = 10_000
MAX_BYTES = 256 * 1024 * 1024
MANIFEST = Path(__file__).with_name('model-manifest.json')


class ModelIntegrityError(RuntimeError):
    """Do not disclose source text, host paths or exception details."""


def fail():
    raise ModelIntegrityError('English model assets failed integrity verification.')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def scan(root):
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        fail()
    assets = {}
    total = 0
    for path in sorted(root.rglob('*')):
        if path.is_symlink():
            fail()
        if path.is_dir():
            continue
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, 'rb') as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_BYTES:
                fail()
            h = hashlib.sha256()
            size = 0
            while True:
                raw = stream.read(1024 * 1024)
                if not raw:
                    break
                size += len(raw)
                if size > MAX_BYTES:
                    fail()
                h.update(raw)
        total += size
        if total > MAX_BYTES or len(assets) >= MAX_FILES:
            fail()
        assets[path.relative_to(root).as_posix()] = {'sha256': h.hexdigest(), 'bytes': size}
    if not assets:
        fail()
    return assets


def installed_root():
    distribution = importlib.metadata.distribution('en-core-web-sm')
    if distribution.version != MODEL_VERSION:
        fail()
    # Reading distribution metadata locates assets without importing model code.
    return Path(distribution.locate_file(MODEL_NAME))


def seal(root, output):
    """Only the trusted image build calls this. Startup never regenerates it."""
    record = {'format': FORMAT, 'model_name': MODEL_NAME, 'model_version': MODEL_VERSION,
              'files': scan(root)}
    raw = canonical(record)
    with Path(output).open('xb') as stream:
        stream.write(raw)
    with Path(str(output)+'.sha256').open('x') as stream:
        stream.write(digest(raw)+'\n')
    return digest(raw)


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            fail()
        result[key] = value
    return result


def bounded_int(value):
    if len(value) > 10:
        fail()
    return int(value)


def read_regular(path, limit):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            fail()
        raw = stream.read(limit+1)
    if len(raw) > limit:
        fail()
    return raw


def verify(root, manifest):
    try:
        raw = read_regular(manifest, 2_000_000)
        expected = read_regular(str(manifest)+'.sha256', 65).decode('ascii').strip()
        if len(expected) != 64 or digest(raw) != expected:
            fail()
        record = json.loads(raw, object_pairs_hook=unique_pairs, parse_int=bounded_int,
                            parse_float=lambda _: fail(), parse_constant=lambda _: fail())
        if (set(record) != {'format', 'model_name', 'model_version', 'files'}
                or record['format'] != FORMAT or record['model_name'] != MODEL_NAME
                or record['model_version'] != MODEL_VERSION or not isinstance(record['files'], dict)):
            fail()
        for name in record['files']:
            relative = PurePosixPath(name)
            if relative.is_absolute() or '..' in relative.parts or '\\' in name:
                fail()
            item = record['files'][name]
            if (not isinstance(item, dict) or set(item) != {'sha256', 'bytes'}
                    or type(item['bytes']) is not int or not 0 <= item['bytes'] <= MAX_BYTES
                    or not isinstance(item['sha256'], str) or len(item['sha256']) != 64
                    or any(char not in '0123456789abcdef' for char in item['sha256'])):
                fail()
        if scan(root) != record['files']:
            fail()
        return {'model_name': MODEL_NAME, 'model_version': MODEL_VERSION,
                'manifest_sha256': expected, 'asset_files': len(record['files']),
                'verified_before_load': True}
    except (OSError, ValueError, TypeError, AttributeError, RecursionError):
        fail()


def verify_installed():
    try:
        return verify(installed_root(), MANIFEST)
    except (OSError, ValueError, importlib.metadata.PackageNotFoundError):
        fail()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seal', action='store_true', help='Trusted image build only.')
    args = parser.parse_args()
    if args.seal:
        seal(installed_root(), MANIFEST)
    else:
        print(json.dumps(verify_installed(), sort_keys=True))
