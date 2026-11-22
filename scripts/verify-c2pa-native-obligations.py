#!/usr/bin/env python3
"""Check/collect selected published C2PA Cargo source observations; no code execution."""
import argparse
import json
import os
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools import c2pa_native_obligations as source


def main(argv=None):
    class Parser(argparse.ArgumentParser):
        def error(self,message):raise ValueError('C2PA native evidence refused.')
    p=Parser(description=__doc__)
    p.add_argument('--cache-dir',type=Path)
    p.add_argument('--native-cache-dir',type=Path,help='Existing selected wheel cache for actual embedded-label replay; no native execution')
    p.add_argument('--collect',action='store_true',help='Explicit official source retrieval to an owned private cache; no package installation')
    args=p.parse_args(argv)
    try:
        if args.collect:
            source.need(args.cache_dir is not None and not (ROOT/source.MANIFEST).exists())
            if not args.cache_dir.exists():args.cache_dir.mkdir(mode=0o700)
            source.need(not args.cache_dir.is_symlink() and args.cache_dir.stat().st_uid==os.getuid() and not args.cache_dir.stat().st_mode&0o077)
            data,blobs=source.assemble(args.cache_dir,download=True)
            for path,raw in blobs.items():
                target=ROOT/path;target.parent.mkdir(parents=True,exist_ok=True)
                with target.open('xb') as f:f.write(raw)
            with (ROOT/source.MANIFEST).open('x') as f:f.write(json.dumps(data,indent=2)+'\n')
        print(json.dumps(source.verify(ROOT,args.cache_dir,args.native_cache_dir),sort_keys=True))
        return 0
    except Exception:
        print('UNAVAILABLE: C2PA native source evidence refused.',file=sys.stderr);return 1


if __name__=='__main__':
    try:raise SystemExit(main())
    except (ValueError,OSError):
        print('UNAVAILABLE: C2PA native source evidence refused.',file=sys.stderr);raise SystemExit(1)
