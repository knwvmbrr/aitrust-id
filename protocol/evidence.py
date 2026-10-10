"""Bounded, unique-key JSON input for locally supplied evidence files."""
import json
import math
from pathlib import Path

def unique(pairs):
    value={}
    for key,item in pairs:
        if key in value:raise ValueError('Duplicate evidence key')
        value[key]=item
    return value

def reject(_):raise ValueError('Non-finite evidence value')

def finite(value,depth=0):
    if depth>64:raise ValueError('Evidence nesting limit')
    if isinstance(value,float) and not math.isfinite(value):raise ValueError('Non-finite evidence value')
    if isinstance(value,str) and any(0xD800<=ord(c)<=0xDFFF for c in value):raise ValueError('Non-scalar evidence text')
    for child in value.values() if isinstance(value,dict) else value if isinstance(value,list) else []:
        finite(child,depth+1)

def read_evidence(path,limit=2_000_000):
    path=Path(path)
    if path.is_symlink() or any(p.is_symlink() for p in path.parents) or not path.is_file():raise ValueError('Invalid evidence file')
    with path.open('rb') as stream:raw=stream.read(limit+1)
    if len(raw)>limit:raise ValueError('Evidence input limit')
    value=json.loads(raw.decode('utf-8',errors='strict'),object_pairs_hook=unique,parse_constant=reject)
    finite(value)
    if not isinstance(value,dict):raise ValueError('Evidence must be an object')
    return value
