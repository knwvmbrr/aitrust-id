#!/usr/bin/env python3
"""Compute an anonymous nominal MT agreement summary from a local rating matrix."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.reviewer_agreement import nominal_agreement
from protocol.evidence import read_evidence
from protocol.reports import write_report

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('ratings',type=Path);p.add_argument('--output');args=p.parse_args()
    try:
        result=nominal_agreement(read_evidence(args.ratings,limit=2_000_000))
    except (ValueError,TypeError,KeyError,OSError,UnicodeError,RecursionError):
        print(json.dumps({'state':'UNAVAILABLE','reason':'invalid_or_unavailable_local_ratings','independence_verified':False,'release_approved':False}));return 2
    if args.output:
        try:write_report(args.output,result)
        except (ValueError,TypeError,OSError):
            print(json.dumps({'state':'UNAVAILABLE','reason':'aggregate_report_not_saved','independence_verified':False,'release_approved':False}));return 2
    print(json.dumps(result,allow_nan=False));return 0 if result['state']=='AVAILABLE' else 2
if __name__=='__main__':raise SystemExit(main())
