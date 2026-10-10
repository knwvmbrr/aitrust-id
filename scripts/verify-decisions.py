"""Render or verify the dated ledger; never changes decision status."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from protocol.decisions import render,verify
from protocol.reports import write_report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--render',action='store_true');p.add_argument('--output');a=p.parse_args()
    if a.render:
        data=json.loads((ROOT/'docs/decisions.json').read_text())
        (ROOT/'DECISIONS.md').write_text(render(data,(ROOT/'docs/decision-history.md').read_text()))
    try: result=verify()
    except (ValueError,KeyError,TypeError,OSError): result={'pass':False,'reason':'dated_decision_contract_failed'}
    result['captured_at']=datetime.now(timezone.utc).isoformat()
    if a.output:write_report(a.output,result)
    print(json.dumps(result));raise SystemExit(0 if result['pass'] else 1)
