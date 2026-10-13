#!/usr/bin/env python3
"""Verify the exact approved disabled-pilot policy, without storage or network access."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools.research_policy import assess
from protocol.reports import write_report
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output');a=p.parse_args()
    try:r=assess()
    except (ValueError,TypeError,KeyError,OSError,RecursionError):
        r={'pass':False,'reason':'accepted_pilot_policy_unavailable','collection_enabled':False,'real_submissions_accepted':False}
    r['captured_at']=datetime.now(timezone.utc).isoformat()
    if a.output:write_report(a.output,r)
    print(json.dumps(r));raise SystemExit(0 if r['pass'] else 1)
