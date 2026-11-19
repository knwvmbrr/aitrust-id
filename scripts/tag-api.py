#!/usr/bin/env python3
"""One JSON tag-check request on stdin, one bounded summary on stdout."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import tag_api


def unique(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError('Duplicate input field')
        out[key] = value
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--list-tags', action='store_true', help='Return the implemented-check catalogue without reading text.')
    args = parser.parse_args()
    try:
        if args.list_tags:
            row = tag_api.list_tags()
        else:
            raw = sys.stdin.buffer.read(256_001)
            if len(raw) > 256_000:
                raise ValueError('Request too large')
            request = json.loads(raw.decode('utf-8', 'strict'), object_pairs_hook=unique,
                                 parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Invalid constant')))
            text, tags = tag_api.validate_request(request)
            row = tag_api.check_text(text, tags)
        print(json.dumps(row, ensure_ascii=True, allow_nan=False))
        return {'UNAVAILABLE': 1, 'PARTIAL': 3}.get(row.get('state'), 0)
    except Exception:
        print(json.dumps({'state': 'UNAVAILABLE', 'reason': 'request_refused', 'text_included': False,
                          'research_submitted': False, 'safety_clearance': False}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
