#!/usr/bin/env python3
"""Run only synthetic PostgreSQL community tests under an isolated Linux wrapper."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools.backup_retention import prepare_account
from protocol.reports import write_report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run-as',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    try:
        namespace=prepare_account(a.run_as)
        spec=importlib.util.spec_from_file_location('community_pg_lab',ROOT/'scripts/verify-community-postgres.py')
        lab=importlib.util.module_from_spec(spec);spec.loader.exec_module(lab)
        proof=lab.verify(namespace);write_report(a.output,proof);print(json.dumps({'pass':proof['pass'],'controls':len(proof['controls']),'failure_stage':proof['failure_stage']}));return 0 if proof['pass'] else 1
    except Exception:
        print('{"state":"Unavailable","synthetic_only":true,"public_service_enabled":false}',file=sys.stderr);return 2


if __name__=='__main__':raise SystemExit(main())
