#!/usr/bin/env python3
"""Check bounded source/notice evidence offline; never execute platform binaries."""
import argparse
import json
from pathlib import Path
import sys
import tarfile
import zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.dont_write_bytecode=True
from tools.esbuild_cohort import verify

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive-dir',type=Path);p.add_argument('--source-dir',type=Path);a=p.parse_args()
    try:print(json.dumps(verify(archive_dir=a.archive_dir,source_dir=a.source_dir)));return 0
    except (ValueError,KeyError,TypeError,OSError,EOFError,tarfile.TarError,zipfile.BadZipFile):
        print('esbuild cohort evidence unavailable.',file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
