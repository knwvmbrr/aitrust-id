#!/usr/bin/env python3
"""Run public synthetic conformance cases against a trusted local checker command."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.conformance_vectors import run


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--profile', choices=('all', 'schema', 'extension'), default='all')
    p.add_argument('--implementation', nargs=argparse.REMAINDER,
                   help='Trusted executable and arguments; receives --profile and JSON stdin. No shell.')
    args = p.parse_args()
    try:
        result = run(args.implementation, ('schema', 'extension') if args.profile == 'all' else (args.profile,))
    except (OSError, ValueError, TypeError, RecursionError):
        print(json.dumps({'pass': False, 'state': 'Unavailable', 'reason': 'vector_or_tooling_refused'}))
        return 2
    print(json.dumps(result, separators=(',', ':')))
    return 0 if result['pass'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
