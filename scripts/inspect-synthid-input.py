#!/usr/bin/env python3
"""Inspect explicitly selected SynthID research token evidence; never issue a tag."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import synthid_input as vendor


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('file', nargs='?')
    parser.add_argument('--runtime', type=Path)
    parser.add_argument('--json', action='store_true', help='Explicit linkable token/configuration identity export; no raw token IDs')
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        if args.worker:
            if args.file or args.runtime or args.json:
                raise ValueError('Invalid worker mode')
            import resource
            resource.setrlimit(resource.RLIMIT_CPU, (10, 10))
            packet = vendor.parse(sys.stdin.buffer.read(vendor.MAX_INPUT + 1))
            result = vendor.score(packet)
            print(json.dumps(result, separators=(',', ':'), allow_nan=False))
            return 0
        if not args.file or not args.runtime:
            raise ValueError('Select packet and trusted runtime')
        try:
            packet = vendor.read_packet(args.file)
            result = vendor.inspect(packet, args.runtime)
        except (OSError, ValueError, TypeError):
            result = vendor.empty('UNSUPPORTED', 'invalid_or_unsupported_packet')
        print(json.dumps(result, indent=2, allow_nan=False) if args.json else vendor.brief(result))
        return 0 if result['state'] == 'OBSERVED' else 2 if result['state'] == 'INSUFFICIENT' else 1
    except Exception:
        print('UNAVAILABLE: no valid vendor observation; no tag issued.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
