#!/usr/bin/env python3
"""Exercise organization audit storage in a disposable, socket-only Linux development cluster."""
import argparse,json,sys
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools.backup_retention import prepare_account
from tools.organization_audit_lab import verify
from tools.blind_review_io import create
from protocol.reports import write_report

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run-as',required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--private-logs',type=Path);a=p.parse_args()
    try:
        namespace=prepare_account(a.run_as);proof,raw=verify(namespace)
        if a.private_logs:create(a.private_logs,ROOT,{'execution.log':raw})
        write_report(a.output,proof);print(json.dumps({'pass':proof['pass'],'controls':len(proof['controls']),'production_changes':False}));return 0 if proof['pass'] else 1
    except Exception:
        print('{"state":"UNAVAILABLE","reason":"isolated_audit_development_contract_refused"}',file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
