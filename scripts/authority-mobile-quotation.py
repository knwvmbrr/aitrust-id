#!/usr/bin/env python3
"""Inspect literal straight or curly double-quote authority placement locally."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
class Parser(argparse.ArgumentParser):
    def error(self,message):self.exit(2,'Double-quote check unavailable. Use --help.\n')
def private_export(path,details):
    # Optional IO is never imported for a default recognition-only run.
    try:
        from tools.mt_quote_export import save_details,ExportRefused,ExportUncertain
    except BaseException:
        return {'state':'UNAVAILABLE','private_output_may_remain':False,
                'message':'Private export support is unavailable; no new export was attempted.'}
    try:
        raw=(json.dumps(details,ensure_ascii=True,indent=2,allow_nan=False)+'\n').encode()
        save_details(path,raw)
        return None
    except ExportUncertain:
        return {'state':'OUTPUT_UNCERTAIN','private_output_may_remain':True,
                'message':'Private output may remain; do not use it as accepted evidence.'}
    except ExportRefused:
        return {'state':'UNAVAILABLE','private_output_may_remain':False,
                'message':'Private export was refused. Use an existing owner-held 0700 parent outside Git and a new destination.'}
    except BaseException:
        return {'state':'OUTPUT_UNCERTAIN','private_output_may_remain':True,
                'message':'Private output may remain; do not use it as accepted evidence.'}

def main(argv=None):
    p=Parser(description=__doc__);p.add_argument('--language',required=True,choices=['en']);p.add_argument('--details',type=Path)
    a=p.parse_args(argv)
    try:
        from tools.authority_mobile_quotation import observe
        raw=sys.stdin.buffer.read(32001)
        if len(raw)>32000:raise ValueError('Input unavailable')
        brief,details=observe(raw.decode('utf-8','strict'),a.language)
        if a.details:
            status=private_export(a.details,details)
            brief['private_details_saved']=status is None
            if status is not None:
                brief['private_export']=status
                print(json.dumps(brief,ensure_ascii=True,allow_nan=False));return 2
        print(json.dumps(brief,ensure_ascii=True,allow_nan=False));return 0
    except (ValueError,OSError,UnicodeError,TypeError,KeyError,RecursionError,ImportError,SyntaxError):
        print('{"state":"UNAVAILABLE","reason":"unsupported_double_quote_context","tags":[]}');return 2
if __name__=='__main__':raise SystemExit(main())
