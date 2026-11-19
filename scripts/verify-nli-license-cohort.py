#!/usr/bin/env python3
"""Check retained NLI obligations offline; optional replay reads existing wheels only."""
import argparse
import json
from pathlib import Path
import sys
import zipfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools.nli_license_cohort import collect, verify
from protocol.reports import write_report


class Parser(argparse.ArgumentParser):
    def error(self,message):self.exit(2,'NLI license cohort refused; use --help.\n')


def main():
    parser = Parser(description=__doc__)
    parser.add_argument('--wheel-mac',type=Path);parser.add_argument('--wheel-linux',type=Path)
    parser.add_argument('--collect',action='store_true');parser.add_argument('--source-cache',type=Path)
    parser.add_argument('--require-distribution-ready',action='store_true');parser.add_argument('--output',type=Path)
    args = parser.parse_args()
    if bool(args.wheel_mac)!=bool(args.wheel_linux) or args.collect and not (args.wheel_mac and args.source_cache) or args.source_cache and not args.collect:
        parser.error('Use both wheel directories for replay; collection also requires the source cache.')
    try:
        directories = {'mac':args.wheel_mac,'linux':args.wheel_linux} if args.wheel_mac else None
        result = collect(ROOT,directories,args.source_cache) if args.collect else verify(ROOT,wheel_dirs=directories)
        result['distribution_gate_pass'] = result['distribution_ready'] is True
        if args.output:write_report(args.output,result)
        print(json.dumps(result,sort_keys=True))
        return 1 if args.require_distribution_ready and not result['distribution_ready'] else 0
    except (OSError,ValueError,TypeError,KeyError,RuntimeError,zipfile.BadZipFile,OverflowError,RecursionError,StopIteration):
        print('NLI license cohort refused; source and prior observations preserved.',file=sys.stderr);return 2


if __name__=='__main__':raise SystemExit(main())
