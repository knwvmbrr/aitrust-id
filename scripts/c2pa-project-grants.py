#!/usr/bin/env python3
"""Prepare/inspect three project-assembled grant notices, never C2PA SDK permission."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import c2pa_project_grants as grants


class Parser(argparse.ArgumentParser):
    def error(self, unused):
        raise grants.Unavailable()


def main(argv=None):
    try:
        parser = Parser(description=__doc__, allow_abbrev=False)
        operation = parser.add_mutually_exclusive_group(required=True)
        operation.add_argument('--prepare', type=Path, help='New ZIP under an existing private0700 parent outside Git')
        operation.add_argument('--inspect', type=Path, help='Exact received canonical four-member notice ZIP')
        args = parser.parse_args(argv)
        result = grants.prepare(args.prepare) if args.prepare else grants.inspect(args.inspect)
        print(json.dumps(result, sort_keys=True))
        return 0
    except grants.OutputUncertain:
        print('{"state":"UNAVAILABLE","output_may_exist":true,"route_admitted":false}', file=sys.stderr)
        return 2
    except grants.Unavailable:
        print('{"state":"UNAVAILABLE","route_admitted":false}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
