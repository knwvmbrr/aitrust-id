#!/usr/bin/env python3
"""Drop root inside a fresh Linux namespace before disposable fleet verification."""
import argparse,os,runpy,sys
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools.backup_retention import prepare_account
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run-as',required=True);p.add_argument('--output',required=True);a=p.parse_args()
prepare_account(a.run_as)
sys.argv=[str(ROOT/'scripts/verify-fleet.py'),'--output',a.output]
runpy.run_path(str(ROOT/'scripts/verify-fleet.py'),run_name='__main__')
