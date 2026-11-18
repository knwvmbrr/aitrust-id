#!/usr/bin/env python3
"""Inspect the selected nested runtime and enforce retained source/notice bindings."""
import argparse
import json
from pathlib import Path
import sys
import tarfile
import zipfile
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import nested_runtime_inventory as inventory
from tools.blind_review_io import create


class Parser(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, 'Nested runtime command refused; use --help.\n')


def main(argv=None):
    parser = Parser(description=__doc__)
    parser.add_argument('--runtime-archive', type=Path, help='Existing exact pinned npm tgz; no download.')
    parser.add_argument('--collect', action='store_true', help='Create new manifest/obligations; never overwrite.')
    parser.add_argument('--observer', help='Explicit collection attribution, not authenticated identity.')
    parser.add_argument('--export-notices', type=Path, help='New folder outside checkout in an owner-private parent.')
    parser.add_argument('--prepared-runtime', type=Path, help='Local folder containing the five release runtime files.')
    parser.add_argument('--print-notices', action='store_true', help='Emit checked notice bytes for a prepared runtime.')
    args = parser.parse_args(argv)
    try:
        inventory.require(args.collect or args.observer is None, 'Observer only valid with collection')
        if args.print_notices:
            inventory.require(args.prepared_runtime is not None and args.export_notices is None
                              and args.runtime_archive is None and not args.collect, 'Prepared runtime required')
            _, bundle = inventory.notice_bundle(prepared_runtime=args.prepared_runtime)
            sys.stdout.buffer.write(bundle)
            return 0
        if args.collect:
            inventory.require(args.runtime_archive is not None and args.observer is not None,
                              'Archive and observer required')
            targets = [ROOT/(inventory.BASE+name) for name in
                       ('manifest.json', 'obligations.json', 'PYTHON-STDLIB-NOTICES.txt')]
            inventory.require(all(not p.exists() and not p.is_symlink() for p in targets), 'Existing observation refused')
            value, bound = inventory.collect(args.runtime_archive, observer=args.observer)
            written = []
            try:
                for path, raw in [(targets[1], json.dumps(bound, indent=2).encode()+b'\n'),
                                  (targets[2], inventory.render_notice_bundle(value, bound)),
                                  (targets[0], json.dumps(value, indent=2).encode()+b'\n')]:
                    inventory.require(len(raw) <= 8_000_000, 'Observation output limit')
                    with path.open('xb') as stream:
                        written.append(path)
                        stream.write(raw)
            except BaseException:
                for path in written:
                    path.unlink(missing_ok=True)
                raise
        if args.export_notices is not None:
            result, bundle = inventory.notice_bundle(archive=args.runtime_archive,
                                                     prepared_runtime=args.prepared_runtime)
            create(args.export_notices, ROOT, {'PYTHON-STDLIB-NOTICES.txt': bundle,
                'verification.json': inventory.encoded(result)+b'\n'})
            result['notice_bundle_exported'] = True
        else:
            result = inventory.verify(archive=args.runtime_archive, prepared_runtime=args.prepared_runtime)
        print(json.dumps(result))
        return 0
    except (ValueError, OSError, KeyError, TypeError, RuntimeError, RecursionError, UnicodeError,
            EOFError, StopIteration, tarfile.TarError, zipfile.BadZipFile, zlib.error):
        print(json.dumps({'pass': False, 'reason': 'nested_runtime_evidence_refused',
            'permission_cleared': False, 'complete_transitive_coverage': False}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
