#!/usr/bin/env python3
"""Inspect literal straight or curly double-quote authority placement locally."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
class Parser(argparse.ArgumentParser):
    def error(self,message):self.exit(2,'Double-quote check unavailable. Use --help.\n')
def main(argv=None):
    p=Parser(description=__doc__);p.add_argument('--language',required=True,choices=['en']);p.add_argument('--details',type=Path)
    a=p.parse_args(argv)
    try:
        from tools.authority_mobile_quotation import observe
        from tools.blind_review_io import create
        raw=sys.stdin.buffer.read(32001)
        if len(raw)>32000:raise ValueError('Input unavailable')
        brief,details=observe(raw.decode('utf-8','strict'),a.language)
        if a.details:
            create(a.details,ROOT,{'mobile-authority-quotation.json':(json.dumps(details,ensure_ascii=True,indent=2,allow_nan=False)+'\n').encode()});brief['private_details_saved']=True
        print(json.dumps(brief,ensure_ascii=True,allow_nan=False));return 0
    except (ValueError,OSError,UnicodeError,TypeError,KeyError,RecursionError,ImportError,SyntaxError):
        print('{"state":"UNAVAILABLE","reason":"unsupported_double_quote_context","tags":[]}');return 2
if __name__=='__main__':raise SystemExit(main())
