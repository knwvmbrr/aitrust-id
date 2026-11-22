#!/usr/bin/env python3
"""Install/remove only an explicitly owned offline research runtime; no model."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import uuid
import venv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import synthid_input as vendor
MANIFEST = 'e6abc9476ba0e5ad94b94bc85b0095c7055fe1a6cdb67782472b41f66e363503'


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('destination', type=Path)
    p.add_argument('--wheel-cache', type=Path)
    p.add_argument('--remove', action='store_true')
    args = p.parse_args(argv)
    target = args.destination.absolute()
    try:
        if target.is_symlink() or any(parent.is_symlink() for parent in target.parents):
            raise ValueError('Invalid destination')
        marker = target / '.aitrust-synthid-owner.json'
        if args.remove:
            record = json.loads(vendor.read_source(marker, 4096))
            if (set(record) != {'format', 'destination', 'id'} or record['format'] != 'ai-trust-id-synthid-owned-runtime/v1'
                    or record['destination'] != str(target) or not isinstance(record['id'], str) or len(record['id']) != 32
                    or target.stat().st_uid != os.getuid() or target.stat().st_mode & 0o077):
                raise ValueError('Not an owned private runtime')
            shutil.rmtree(target)
            print('Removed the selected owned research runtime. Personal checks are unchanged.')
            return 0
        if (platform.system() != 'Darwin' or platform.machine() != 'arm64'
                or sys.version_info[:2] != (3, 12) or not args.wheel_cache or target.exists()
                or not target.parent.is_dir()):
            raise ValueError('Unsupported install profile')
        manifest_bytes = vendor.read_source(vendor.SDK / 'sources.json')
        if hashlib.sha256(manifest_bytes).hexdigest() != MANIFEST:
            raise ValueError('Unreviewed install profile')
        manifest = json.loads(manifest_bytes)
        lock = vendor.read_source(vendor.SDK / 'requirements-macos-arm64.lock')
        if hashlib.sha256(lock).hexdigest() != manifest['source_sha256']['integrations/synthid-reference/requirements-macos-arm64.lock']:
            raise ValueError('Unreviewed lock')
        vendor.source_identity()
        # Reserve the worst-case approved install plus2GiB; never evict other work.
        if shutil.disk_usage(target.parent).free < 2 * 1024**3 + 858993459:
            raise ValueError('Insufficient private install reserve')
        target.mkdir(mode=0o700)
        marker.write_text(json.dumps({'format': 'ai-trust-id-synthid-owned-runtime/v1',
                                     'destination': str(target), 'id': uuid.uuid4().hex}))
        os.chmod(marker, 0o600)
        venv.EnvBuilder(with_pip=True, symlinks=True).create(target)
        child = subprocess.run([str(target / 'bin/python'), '-I', '-m', 'pip', 'install', '--no-index',
                                '--no-cache-dir', '--no-compile', '--require-hashes', '--no-deps',
                                '--find-links', str(args.wheel_cache), '-r',
                                str(vendor.SDK / 'requirements-macos-arm64.lock')],
                               stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               timeout=180, check=False)
        if child.returncode or shutil.disk_usage(target.parent).free < 2 * 1024**3:
            raise ValueError('Runtime install did not complete within reserve')
        print('Installed the pinned optional research runtime. No model weights or personal checks changed.')
        return 0
    except Exception:
        # An incomplete owned target remains marked for explicit safe removal.
        print('UNAVAILABLE: research runtime operation refused or incomplete.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
