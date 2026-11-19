#!/usr/bin/env python3
"""Inspect supported ASCII quotation context around authority phrases locally."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class Parser(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, 'Authority quotation check unavailable. Use --help.\n')


def main(argv=None):
    parser = Parser(description=__doc__)
    parser.add_argument('--language', required=True, choices=['en'])
    parser.add_argument('--details', type=Path, help='New output folder in an existing owner-private parent.')
    args = parser.parse_args(argv)
    try:
        from tools import authority_quotation
        from tools.blind_review_io import create
        raw = sys.stdin.buffer.read(32001)
        if len(raw) > 32000:
            raise ValueError('Oversized input')
        brief, details = authority_quotation.observe(raw.decode('utf-8', 'strict'), args.language)
        if args.details:
            create(args.details, ROOT, {'authority-quotation.json':
                   (json.dumps(details, ensure_ascii=True, indent=2, allow_nan=False) + '\n').encode()})
            brief['private_details_saved'] = True
        print(json.dumps(brief, ensure_ascii=True, indent=2, allow_nan=False))
        return 0
    except (ValueError, OSError, UnicodeError, TypeError, KeyError, RecursionError, ImportError, SyntaxError):
        print('{"state":"UNAVAILABLE","reason":"unsupported_authority_quotation_context","tags":[]}', file=sys.stdout)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
