#!/usr/bin/env python3
"""Count supported numeric details and same-sentence source markers locally."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from protocol.corpus import CorpusError
from tools import quantitative_observations as tool


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--language',required=True,help='Declared language; only en is supported')
    parser.add_argument('--private-report',help='New 0600 details file in an existing private 0700 directory outside source')
    args=parser.parse_args()
    try:
        raw=sys.stdin.buffer.read(32001)
        if len(raw)>32000:raise CorpusError('Input exceeds the byte limit.')
        brief,detail=tool.observe(raw.decode('utf-8',errors='strict'),args.language)
        if args.private_report:
            tool.save_private(detail,args.private_report);brief['private_report_saved']=True
        print(json.dumps(brief,ensure_ascii=True,indent=2));return 0
    except (CorpusError,OSError,UnicodeError,ValueError,TypeError,RecursionError):
        print(json.dumps({'state':'UNAVAILABLE','reason':'invalid_or_unsupported_quantitative_observation',
                          'tags':[],'truth_established':False}));return 2


if __name__=='__main__':raise SystemExit(main())
