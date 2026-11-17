#!/usr/bin/env python3
"""Inspect selected framing evidence locally. This does not issue an MT tag."""
import argparse
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import mt_workflow as workflow
from tools.blind_review_io import create


class Parser(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, 'Framing check refused; use --help for supported choices.\n')


def main(argv=None):
    parser = Parser(description=__doc__)
    parser.add_argument('--check', choices=workflow.COMPONENTS, action='append', required=True,
                        help='Choose each observation explicitly; repeat for another.')
    parser.add_argument('--language', required=True, choices=['en'])
    parser.add_argument('--choice-packet', type=Path, help='Explicit private choice packet for this same text.')
    parser.add_argument('--details', type=Path, help='Save locations and fingerprints in a NEW private folder.')
    args = parser.parse_args(argv)
    try:
        raw = sys.stdin.buffer.read(workflow.MAX_BYTES + 1)
        if len(raw) > workflow.MAX_BYTES:
            raise ValueError('Input outside limit')
        result = workflow.check(raw.decode('utf-8', 'strict'), args.check, args.language, args.choice_packet)
        if args.details is not None:
            create(args.details, ROOT, {'framing-evidence.json':
                   (json.dumps(result, indent=2, allow_nan=False, ensure_ascii=True) + '\n').encode()})
        for row in result['checks']:
            print(workflow.brief(row))
        print('Research evidence only; no MT tag or combined score. Nothing is uploaded.')
        return 2 if result['state'] == 'UNAVAILABLE' else 3 if result['state'] == 'PARTIAL' else 0
    except (ValueError, OSError, TypeError, KeyError, RuntimeError, RecursionError, UnicodeError):
        print('Unavailable: check supported text, selections and private export permissions.', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
