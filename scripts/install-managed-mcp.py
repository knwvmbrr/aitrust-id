#!/usr/bin/env python3
"""Verify a protected MCP artifact, install offline, then publish a private connection."""
import argparse
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class Parser(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, 'Managed MCP unavailable; use --help.\n')


def main(argv=None):
    parser = Parser(description=__doc__)
    for name in ('artifact', 'packet', 'spdx', 'bundle', 'trusted-root', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--source-commit', required=True)
    parser.add_argument('--python', default=sys.executable)
    parser.add_argument('--pip-python', required=True)
    args = parser.parse_args(argv)
    uncertain = ()
    unavailable = ()
    try:
        from tools.mcp_managed_release import (
            install_managed, ManagedReleaseUncertain, ManagedReleaseUnavailable,
        )
        uncertain = (ManagedReleaseUncertain,)
        unavailable = (ManagedReleaseUnavailable,)
        result = install_managed(args.artifact, args.packet, args.spdx, args.bundle,
            args.trusted_root, args.output, source_commit=args.source_commit,
            python=args.python, pip_python=args.pip_python, root=ROOT)
        print(json.dumps(result, sort_keys=True, allow_nan=False))
        return 0
    except uncertain:
        print('{"state":"UNAVAILABLE","reason":"output_commit_uncertain",'
              '"output_may_exist":true,"private_bytes_may_remain":true}', file=sys.stderr)
    except unavailable:
        print('{"state":"UNAVAILABLE","reason":"managed_mcp_refused",'
              '"output_may_exist":false,"private_bytes_may_remain":true}', file=sys.stderr)
    except (OSError, ValueError, TypeError, KeyError, ImportError, OverflowError,
            RuntimeError, RecursionError, UnicodeError):
        print('{"state":"UNAVAILABLE","reason":"managed_mcp_refused",'
              '"output_may_exist":false,"private_bytes_may_remain":true}', file=sys.stderr)
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
