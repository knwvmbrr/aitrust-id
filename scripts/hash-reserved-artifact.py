#!/usr/bin/env python3
"""Hash a bounded explicitly prepared artifact from stdin; encoded files unsupported."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from protocol.reserved_subjects import subject,MAX_REQUEST_BYTES
def unique_pairs(pairs):
    obj={}
    for key,value in pairs:
        if key in obj:raise ValueError('Duplicate field')
        obj[key]=value
    return obj
def main():
    try:
        raw=sys.stdin.buffer.read(MAX_REQUEST_BYTES+1)
        if len(raw)>MAX_REQUEST_BYTES:raise ValueError('Oversized artifact envelope')
        value=json.loads(raw,object_pairs_hook=unique_pairs,parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite value')))
        print(json.dumps(subject(value),ensure_ascii=True));return 0
    except (ValueError,UnicodeError,TypeError,RecursionError):
        print('Invalid or unsupported prepared artifact; no subject issued.',file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
