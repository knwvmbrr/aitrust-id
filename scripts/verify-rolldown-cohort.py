#!/usr/bin/env python3
"""Verify bounded Rolldown source/notice evidence offline, without loading addons."""
import argparse
import json
from pathlib import Path
import sys
import tarfile
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.dont_write_bytecode = True
from tools.rolldown_cohort import verify

class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError('invalid verifier arguments')

def main():
    try:
        parser = Parser(description=__doc__)
        parser.add_argument('--archive-dir', type=Path)
        parser.add_argument('--source-dir', type=Path)
        args = parser.parse_args()
        print(json.dumps(verify(archive_dir=args.archive_dir, source_dir=args.source_dir)))
        return 0
    except (ValueError, KeyError, TypeError, OSError, EOFError, tarfile.TarError):
        print('Rolldown cohort evidence unavailable.', file=sys.stderr)
        return 2
if __name__ == '__main__':
    raise SystemExit(main())
