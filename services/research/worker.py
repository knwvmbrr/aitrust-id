#!/usr/bin/env python3
"""One bounded stdin request; existing synthetic socket-only admission only."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.research_admission import MAX_BYTES


class Parser(argparse.ArgumentParser):
    def error(self, _message):
        self.exit(2, 'Synthetic worker arguments refused.\n')


def main():
    parser = Parser(add_help=False)
    parser.add_argument('--sandbox-dir', required=True)
    try:
        args = parser.parse_args()
        raw = sys.stdin.buffer.read(MAX_BYTES + 1)
        spec = importlib.util.spec_from_file_location('synthetic_admission', ROOT/'scripts/research-admission.py')
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        value = module.execute(args.sandbox_dir, raw)
        print(json.dumps(value, separators=(',', ':'), allow_nan=False))
        return 0
    except Exception:
        # No exception text, input, capability, SQL or path is returned or logged.
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
