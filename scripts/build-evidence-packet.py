#!/usr/bin/env python3
"""Print a source-bound index of the repository's selected execution receipts."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.evidence_packet import build


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--require-current', action='store_true',
                        help='Exit 1 if any selected engineering receipt is stale, failed or unavailable.')
    args = parser.parse_args()
    try:
        result = build()
    except (OSError, ValueError, TypeError, KeyError, RecursionError):
        print(json.dumps({'packet_valid': False, 'state': 'Unavailable',
                          'reason': 'evidence_packet_refused'}))
        return 2
    print(json.dumps(result, separators=(',', ':')))
    return 0 if result['packet_valid'] and (not args.require_current or result['engineering_checks_current']) else 1


if __name__ == '__main__':
    raise SystemExit(main())
