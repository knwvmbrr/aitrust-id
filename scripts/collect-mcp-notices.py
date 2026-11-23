#!/usr/bin/env python3
"""Replay the exact finite MCP native source/notice cohort offline; no extraction."""
import argparse
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class Parser(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, 'MCP source obligations unavailable; use --help.\n')


def main(argv=None):
    parser = Parser(description=__doc__)
    parser.add_argument('--cache', type=Path, action='append', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    uncertain = ()
    try:
        from tools.mcp_runtime_obligations import collect
        from tools.artifact_evidence_io import Capture, OutputCommitUncertain
        uncertain = (OutputCommitUncertain,)
        value = collect(ROOT, args.cache)
        with Capture() as capture:
            capture.save(args.output, value, 4_000_000)
        print(json.dumps({'pass': True, 'source_packages': len(value['packages']),
                          'notice_texts': len(value['texts']), 'distribution_approved': False}, sort_keys=True))
        return 0
    except uncertain:
        print('{"state":"UNAVAILABLE","reason":"output_commit_uncertain","output_may_exist":true}', file=sys.stderr)
        return 2
    except (OSError, ValueError, TypeError, KeyError, ImportError, OverflowError, RuntimeError, RecursionError):
        print('{"state":"UNAVAILABLE","reason":"mcp_source_obligations_refused"}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
