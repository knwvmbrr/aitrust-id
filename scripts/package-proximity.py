#!/usr/bin/env python3
"""Import ranked package references, or check explicitly supplied names offline."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from protocol.corpus import CorpusError
from tools import package_proximity as proximity


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest='mode', required=True)
    create = modes.add_parser('import', help='Create a private versioned ranking snapshot.')
    create.add_argument('--source', type=Path, required=True)
    create.add_argument('--output', type=Path, required=True)
    observe = modes.add_parser('check', help='Read one package name per line from stdin.')
    observe.add_argument('--snapshot', type=Path, required=True)
    observe.add_argument('--top-n', type=int)
    args = parser.parse_args(argv)
    try:
        if args.mode == 'import':
            result = proximity.create(args.source, args.output)
        else:
            result = proximity.observe(proximity.load(args.snapshot),
                                       sys.stdin.read(proximity.MAX_CHARACTERS + 1), args.top_n)
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0
    except (CorpusError, OSError, UnicodeError, RecursionError, TypeError, KeyError):
        print(json.dumps({'state': 'UNAVAILABLE', 'reason': 'invalid_or_unsupported_package_input_or_reference',
                          'tags': [], 'maliciousness_established': False}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
