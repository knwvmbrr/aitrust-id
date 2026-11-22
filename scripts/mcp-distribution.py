#!/usr/bin/env python3
"""Build, inspect or privately install an exact development MCP wheel bundle."""
import argparse
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class Parser(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, 'MCP distribution unavailable; use --help.\n')


def main(argv=None):
    parser = Parser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True, parser_class=Parser)
    c = sub.add_parser('collect')
    c.add_argument('--wheelhouse', type=Path, required=True)
    c.add_argument('--output', type=Path, required=True)
    b = sub.add_parser('build')
    b.add_argument('--target', required=True)
    b.add_argument('--wheelhouse', type=Path, required=True)
    b.add_argument('--output', type=Path, required=True)
    v = sub.add_parser('verify')
    v.add_argument('archive', type=Path)
    i = sub.add_parser('install')
    i.add_argument('archive', type=Path)
    i.add_argument('--output', type=Path, required=True)
    i.add_argument('--python', default=sys.executable)
    i.add_argument('--pip-python', required=True)
    for name in ('verify-install', 'probe'):
        installed = sub.add_parser(name)
        installed.add_argument('archive', type=Path)
        installed.add_argument('--connection', type=Path, required=True)
        installed.add_argument('--python', default=sys.executable)
    args = parser.parse_args(argv)
    uncertain_type = ()
    capacity_type = ()
    try:
        from tools import mcp_distribution as tool
        from tools.artifact_evidence_io import Capture, OutputCommitUncertain
        uncertain_type = (OutputCommitUncertain,)
        capacity_type = (tool.InstallCapacityUnavailable,)
        if args.command == 'collect':
            record = tool.collect(ROOT, args.wheelhouse)
            with Capture() as capture:
                capture.save(args.output, record, 4_000_000)
            result = {'profile': tool.PROFILE, 'pass': True, 'wheel_count': len(record['wheels']),
                      'target_count': len(record['targets']), 'distribution_approved': False}
        elif args.command == 'build':
            result = tool.export(args.output, ROOT, target=args.target, wheelhouse=args.wheelhouse)
        elif args.command == 'verify':
            result = tool.verify_file(args.archive, ROOT)
        elif args.command == 'install':
            result = tool.install(args.archive, args.output, python=args.python,
                                  pip_python=args.pip_python, root=ROOT)
        else:
            result = tool.verify_install(args.archive, args.connection, python=args.python,
                                         root=ROOT, execute_probe=args.command == 'probe')
        print(json.dumps(result, sort_keys=True, allow_nan=False))
        return 0
    except uncertain_type:
        print('{"state":"UNAVAILABLE","reason":"output_commit_uncertain","output_may_exist":true}', file=sys.stderr)
        return 2
    except capacity_type:
        print('{"state":"UNAVAILABLE","reason":"insufficient_private_install_capacity"}', file=sys.stderr)
        return 2
    except (OSError, ValueError, TypeError, KeyError, ImportError, OverflowError, RuntimeError,
            RecursionError, UnicodeError):
        print('{"state":"UNAVAILABLE","reason":"mcp_distribution_refused"}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
