#!/usr/bin/env python3
"""Prepare explicit decisions or privately join them to advisory PS predictions."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import ps_review_join as join

class Parser(argparse.ArgumentParser):
    def error(self, _):
        self.exit(2, 'PS advisory join unavailable. Use the documented private packet workflow.\n')

def main(argv=None):
    parser = Parser(description=__doc__)
    parser.add_argument('operation', choices=['prepare', 'run'])
    parser.add_argument('--packet', type=Path, required=True)
    parser.add_argument('--adjudication', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.operation == 'prepare':
            join.need(args.adjudication is None)
            raw = join.capture(args.packet); before = join.sources()
            value = join.template(args.packet)
            def stable():
                join.need(raw == join.capture(args.packet) and before == join.sources())
            join.publish(args.output, {'adjudication.json': join.encoded(value) + b'\n'}, stable)
            count = len(value['decisions'])
        else:
            join.need(args.adjudication is not None)
            files, stable = join.join(args.packet, args.adjudication)
            join.publish(args.output, files, stable)
            count = json.loads(files['report.json'])['advisory']['item_count']
        print(json.dumps({'operation': args.operation, 'item_count': count,
            'advisory_only': True, 'independence_verified': False, 'release_assessed': False}))
        return 0
    except join.ExportUncertain:
        print('PS advisory export uncertain. Private output may remain; do not use it as accepted evidence.', file=sys.stderr)
        return 1
    except (OSError, ValueError, TypeError, KeyError, RuntimeError, RecursionError, subprocess.SubprocessError):
        print('PS advisory join unavailable. No result accepted; check private inputs and current sources.', file=sys.stderr)
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
