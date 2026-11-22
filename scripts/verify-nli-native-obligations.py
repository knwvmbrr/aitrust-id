#!/usr/bin/env python3
"""Offline exact NLI native source/notice graph; no model or permission grant."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def main(argv=None):
    class Parser(argparse.ArgumentParser):
        def error(self, _):
            raise ValueError('NLI native evidence refused.')
    try:
        parser=Parser(description=__doc__,allow_abbrev=False)
        parser.add_argument('--source-cache',type=Path,help='Explicit existing source cache for actual archive replay; never downloads')
        parser.add_argument('--crate-cache',action='append',type=Path,default=[],help='Additional existing registry archive cache, at most2')
        args=parser.parse_args(argv)
        if len(args.crate_cache)>2:raise ValueError('NLI native evidence refused.')
        from tools.nli_native_obligations import verify
        print(json.dumps(verify(ROOT,args.source_cache,args.crate_cache),sort_keys=True))
        return 0
    except Exception:
        print('UNAVAILABLE: NLI native source evidence refused.',file=sys.stderr)
        return 1


if __name__=='__main__':
    raise SystemExit(main())
