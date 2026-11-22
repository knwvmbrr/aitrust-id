#!/usr/bin/env python3
"""Explicit private offline assertion conversion; default output contains no record."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
class Parser(argparse.ArgumentParser):
 def error(self,_):raise ValueError('Invalid migration arguments.')
def main(argv=None):
 capture=None;summary=None
 try:
  p=Parser(description=__doc__,allow_abbrev=False);p.add_argument('input',help='Private0600 assertion file, or - for bounded stdin');p.add_argument('--to',required=True);p.add_argument('--output',help='New private output in an owned0700 directory; never overwritten');a=p.parse_args(argv)
  from protocol.migration import LIMIT,transform,Refusal
  from protocol.migration_io import Capture,OutputCommitUncertain
  with Capture()as capture:
   raw=sys.stdin.buffer.read(LIMIT+1)if a.input=='-'else capture.read(a.input,LIMIT)
   value,summary=transform(raw,a.to);capture.check()
   if a.output:capture.save(a.output,value,LIMIT)
   summary.update(record_exported=bool(a.output),export_contains_correlation_metadata=bool(a.output))
  print(json.dumps(summary,separators=(',',':')));return 0
 except Exception as error:
  status,reason='unavailable','input_or_output_unavailable'
  if error.__class__.__module__=='protocol.migration' and error.__class__.__name__=='Refusal':status,reason=error.status,error.reason
  elif type(error)is ValueError:status,reason='invalid','invalid_request'
  may=bool(getattr(error,'output_may_exist',False)or(capture is not None and capture.output_may_exist))
  print(json.dumps({'format':'assertion-migration/v1','status':status,'reason':reason,'record_exported':False,'output_may_exist':may,'signature_verified':False,'identity_authenticated':False,'detector_rerun':False,'independent_accuracy_evidence':False},separators=(',',':')))
  return {'invalid':1,'unsupported':2,'unavailable':3}[status]
if __name__=='__main__':raise SystemExit(main())
