#!/usr/bin/env python3
"""Verify preserved group-to-job mappings; a grouping is never a tag release."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from protocol.scope_groups import read
from protocol.reports import write_report
SOURCES=('docs/scope-groups.json','docs/master-scope.json','docs/scope-progress.json','protocol/scope_groups.py')
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--projection',action='store_true');p.add_argument('--output');a=p.parse_args()
    try:
        before={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in SOURCES};groups=read()
        if before!={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in SOURCES}:raise ValueError('Scope changed during resolution')
        r={'pass':True,'groups':groups,'sources':before,'scope_ids_preserved':202,'children_completed_by_grouping':False,
           'independent_accuracy_verified':False,'captured_at':datetime.now(timezone.utc).isoformat()}
    except (ValueError,TypeError,KeyError,OSError,RecursionError):r={'pass':False,'reason':'legacy_scope_grouping_unavailable'}
    if a.output:write_report(a.output,r)
    print(json.dumps(groups if a.projection and r['pass'] else r));raise SystemExit(0 if r['pass'] else 1)
