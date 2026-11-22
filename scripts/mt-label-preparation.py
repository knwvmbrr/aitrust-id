#!/usr/bin/env python3
"""Private offline candidate MT annotation preparation; no detector or upload."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools import mt_label_preparation as mt
from tools.mt_label_io import Refused,OutputUncertain


class Parser(argparse.ArgumentParser):
    def error(self,message):raise Refused()


def main():
    try:
        parser=Parser(description=__doc__);commands=parser.add_subparsers(dest='command',required=True)
        for command in ('prepare','validate','compare'):
            child=commands.add_parser(command);child.add_argument('--items',required=True)
            if command!='prepare':child.add_argument('--packet',required=True)
            if command!='validate':child.add_argument('--out',required=True)
            if command=='validate':
                child.add_argument('--response',required=True);child.add_argument('--slot',choices=['A','B'],required=True)
            if command=='compare':child.add_argument('--a',required=True);child.add_argument('--b',required=True)
        args=parser.parse_args()
        if args.command=='prepare':result=mt.freeze(args.items,args.out)
        elif args.command=='validate':result=mt.validate(args.items,args.packet,args.response,args.slot)
        else:result=mt.compare(args.items,args.packet,args.a,args.b,args.out)
        print(json.dumps(result,ensure_ascii=True,allow_nan=False,sort_keys=True));return 0
    except OutputUncertain:
        print(json.dumps({'state':'OUTPUT_UNCERTAIN','output_may_exist':True,
              'message':'Private output may remain; do not use it as accepted evidence.',**mt.FLAGS}));return 2
    except (Refused,OSError,ValueError,TypeError,KeyError,RuntimeError,UnicodeError,RecursionError):
        print(json.dumps({'state':'UNAVAILABLE','reason':'private_input_or_workflow_refused',**mt.FLAGS}));return 2


if __name__=='__main__':raise SystemExit(main())
