#!/usr/bin/env python3
"""Invented complete-record native/browser controls; no accuracy measurements."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools.mt_mobile_device import inspect_mt_mobile_device
CASES=[('phone','The example says “Experts agree [1]”.'),('none','An ordinary sentence.'),
 ('outside','Experts agree [1].'),('quoted_and_outside','“Experts agree [1]”; experts agree.'),
 ('marker_outside_quote','“Experts agree” [1].'),('marker_inside_quote','Experts agree “source [1]”.'),
 ('url_boundary','“Experts agree https://example.invalid/a” experts agree.'),
 ('ascii','"Experts agree [1]".'),('adjacent_ascii','"Experts agree""Doctors recommend"'),
 ('ascii_nesting_not_inferred','"He says "Experts agree" then leaves"'),
 ('adjacent_curly','“Experts agree”“Doctors recommend”'),('combining_non_bmp','PRIVATE_MT_MOBILE_CANARY 😀 Cafe\u0301 “Experts agree [1]”.'),
 ('single_is_ordinary',"'Experts agree'"),('long_s','“ſtudies show”'),('dotted_i','“Scİentİsts agree”'),
 ('mixed','"Experts agree" “Doctors recommend”'),('mismatch','“Experts agree"'),('nested_curly','“He says “Experts agree””'),
 ('unclosed','“Experts agree'),('stray_close','Experts agree”'),('escaped_ascii','\\"Experts agree"'),('escaped_curly','\\“Experts agree”'),
 ('guillemet','«Experts agree»'),('backtick','`Experts agree`'),('nul','PRIVATE_MT_MOBILE_CANARY\0'),('oversize','x'*8001),
 ('quote_cap','“”'*65),('record_cap','Experts agree '*100+'[1] '*100)]
def cases():
 rows=[]
 for identity,text in CASES:
  try:expected=json.loads(inspect_mt_mobile_device(text))
  except (ValueError,UnicodeError,RecursionError):expected=None
  rows.append({'id':identity,'text':text,'expected':expected})
 return rows
if __name__=='__main__':print(json.dumps(cases(),ensure_ascii=True,allow_nan=False))
