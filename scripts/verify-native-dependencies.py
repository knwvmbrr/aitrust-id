#!/usr/bin/env python3
"""Inspect native candidates and declarations; never grant license permission."""
import argparse
import json
from pathlib import Path
import sys
import tarfile
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.native_inventory import collect, verify


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive-dir', type=Path, help='Previously downloaded exact locked archives; no downloads occur.')
    parser.add_argument('--collect', action='store_true', help='Create a NEW sbom/native directory; existing output is never overwritten.')
    parser.add_argument('--observer', help='Explicit operator attribution for a new collection; not an authenticated identity.')
    args = parser.parse_args()
    if args.observer is not None and not args.collect:
        parser.error('--observer is only valid with --collect')
    try:
        if args.collect:
            if args.archive_dir is None or args.observer is None:
                raise ValueError('Archive cache required')
            target = ROOT/'sbom/native'
            if target.exists() or target.is_symlink():
                raise ValueError('Existing inventory must be reviewed separately')
            value, blobs = collect(args.archive_dir, observer=args.observer)
            encoded = json.dumps(value, indent=2)+'\n'
            if len(encoded.encode()) > 8_000_000:
                raise ValueError('Inventory output limit')
            target.mkdir(mode=0o755)
            (target/'sources').mkdir(mode=0o755)
            for digest, raw in sorted(blobs.items()):
                with (target/'sources'/(digest+'.txt')).open('xb') as output:
                    output.write(raw)
            # A partial collection never acquires a completed manifest.
            with (target/'manifest.json').open('x') as output:
                output.write(encoded)
        result = verify(archive_dir=None if args.collect else args.archive_dir)
        print(json.dumps(result))
        return 0
    except (OSError, ValueError, TypeError, KeyError, RecursionError, EOFError, tarfile.TarError, zlib.error):
        print(json.dumps({'pass': False, 'reason': 'native_inventory_refused', 'permission_cleared': False}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
