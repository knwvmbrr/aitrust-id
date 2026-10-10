"""Offline versioned signal lookup; never runs submitted content or shell commands."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from protocol.signals import lookup,registry
from protocol.reports import write_report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--signal');p.add_argument('--check',action='store_true');p.add_argument('--output');a=p.parse_args()
    try:
        if a.signal:
            result=lookup(a.signal);passed=result['status']!='unsupported'
        else:
            data=registry();result={'pass':True,'signals':len(data['signals']),
                 'active_development':sum(s['status']=='active_development' for s in data['signals']),
                 'procedural':sum(s['status']=='procedural' for s in data['signals']),
                 'full_assertion_reproducibility':False,'independent_accuracy_evidence':False};passed=True
    except (ValueError,KeyError,TypeError,OSError):result={'pass':False,'reason':'signal_catalogue_invalid'};passed=False
    result['captured_at']=datetime.now(timezone.utc).isoformat()
    if a.output:write_report(a.output,result)
    print(json.dumps(result));raise SystemExit(0 if passed else 1)
