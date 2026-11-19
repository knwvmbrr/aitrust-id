#!/usr/bin/env python3
"""Verify the selected optional C2PA cohort offline, without installation."""
import argparse
import json
from pathlib import Path
import sys
import tarfile
import zipfile
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT)); sys.dont_write_bytecode = True
from tools.c2pa_cohort import verify


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cache-dir',type=Path,help='Replay exact public upstream artifacts in a private cache.')
    p.add_argument('--require-clearance',action='store_true',help='Refuse: this inventory does not grant license clearance.')
    a=p.parse_args()
    try:
        print(json.dumps(verify(cache_dir=a.cache_dir,require_clearance=a.require_clearance)))
        return 0
    except (ValueError,KeyError,TypeError,IndexError,StopIteration,RecursionError,OSError,EOFError,tarfile.TarError,zipfile.BadZipFile):
        print('C2PA cohort evidence unavailable; no permission or release granted.',file=sys.stderr)
        return 2


if __name__=='__main__':raise SystemExit(main())
