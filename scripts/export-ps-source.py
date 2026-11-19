#!/usr/bin/env python3
"""Export or inspect the exact approved PS source-only ZIP; no user text input."""
import argparse
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.ps_source_distribution import export, verify_file


class Parser(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, 'PS source distribution refused; use --help.\n')


def main(argv=None):
    parser = Parser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True, parser_class=Parser)
    builder = commands.add_parser('build')
    builder.add_argument('--output', required=True, type=Path)
    verifier = commands.add_parser('verify')
    verifier.add_argument('archive', type=Path)
    args = parser.parse_args(argv)
    try:
        result = export(args.output) if args.command == 'build' else verify_file(args.archive)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError, KeyError, ImportError, OverflowError):
        print('PS source distribution refused; source and existing output were preserved.', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
