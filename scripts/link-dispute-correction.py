#!/usr/bin/env python3
"""Link an existing synthetic workbench dispute to an existing private correction."""
import argparse
import json
import sqlite3
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import community_core, community_store, dispute_correction_link


class Parser(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, 'Dispute correction link refused. Use --help.\n')


def main(argv=None):
    parser = Parser(description=__doc__)
    parser.add_argument('operation', choices=('prepare', 'link'))
    parser.add_argument('--workbench', required=True, type=Path)
    parser.add_argument('--registry', required=True, type=Path, help='Existing private directory for plans and committed links.')
    parser.add_argument('--report', required=True, help='Synthetic wrong-result workbench report UUID.')
    parser.add_argument('--moderator', required=True, choices=[name for name, role in community_core.ACTORS.items() if role == 'moderator'])
    parser.add_argument('--packet', required=True, type=Path, help='Existing editorial correction packet with its exact previous journal.')
    parser.add_argument('--correction', required=True, type=Path, help='Existing correction editorial-review.json with subject inclusion disabled.')
    parser.add_argument('--confirm-synthetic-link', required=True, action='store_true')
    args = parser.parse_args(argv)
    try:
        community_core.identity(args.report)
        editorial = dispute_correction_link.load_binding(args.packet, args.correction, ROOT)
        operation = dispute_correction_link.prepare if args.operation == 'prepare' else dispute_correction_link.link
        result = operation(community_store.Store(args.workbench), args.registry, args.report, args.moderator, editorial, root=ROOT)
        print(json.dumps(result))
        return 0
    except (ValueError, OSError, TypeError, KeyError, RuntimeError, OverflowError, AttributeError, sqlite3.Error):
        print('{"state":"Unavailable","synthetic_only":true}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
