#!/usr/bin/env python3
"""Inspect delivery; --check-session requires the strict open target and all minima."""
import argparse
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    import json
    from tools.session_delivery import inspect_project
    from protocol.reports import write_report
    class Parser(argparse.ArgumentParser):
        def error(self, message):
            raise ValueError('Invalid delivery arguments.')
    try:
        parser = Parser(description=__doc__, allow_abbrev=False)
        parser.add_argument('--board', default='docs/session-delivery.json')
        parser.add_argument('--check-session', action='store_true')
        parser.add_argument('--output')
        args = parser.parse_args()
        result = inspect_project(board_name=args.board)
        if args.output:
            write_report(args.output, result)
        print(json.dumps(result, sort_keys=True))
        return 1 if args.check_session and not result['session_success'] else 0
    except (ValueError, TypeError, KeyError, OSError, RecursionError,
            subprocess.SubprocessError):
        print('{"pass":false,"kind":"session_delivery_accounting","reason":"invalid_or_unavailable_delivery_record","scope_approval_granted":false}')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
