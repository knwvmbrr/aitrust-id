#!/usr/bin/env python3
"""Inspect a named distribution policy; never inspect or upload user text."""
import argparse
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.dependency_policy import ROUTES, evaluate


class Parser(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, 'Dependency policy request refused; use --help.\n')


def main():
    parser = Parser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--route')
    group.add_argument('--all', action='store_true')
    args = parser.parse_args()
    rows = [evaluate(name) for name in sorted(ROUTES)] if args.all else [evaluate(args.route)]
    print(json.dumps({'profile': 'technical-dependency-conflict-report/v1', 'routes': rows,
                      'all_selected_allowed': all(row['release_allowed'] for row in rows),
                      'legal_clearance': False, 'independent_accuracy_evidence': False}, sort_keys=True))
    return 0 if all(row['release_allowed'] for row in rows) else 2


if __name__ == '__main__':
    raise SystemExit(main())
