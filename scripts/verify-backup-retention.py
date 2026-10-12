#!/usr/bin/env python3
"""Run an invented encrypted backup drill inside an explicitly isolated Linux process."""
import argparse,json,sys,subprocess
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools.backup_retention import prepare_account,verify
from tools.blind_review_io import create
from protocol.reports import write_report
class Parser(argparse.ArgumentParser):
    def error(self,message):self.exit(2,'Backup retention check refused; use --help for arguments.\n')
def main(argv=None):
    p=Parser(description=__doc__);p.add_argument('--run-as',required=True);p.add_argument('--output',type=Path,default=Path('output/verification/backup-retention.json'));p.add_argument('--private-logs',type=Path);a=p.parse_args(argv)
    try:
        namespace=prepare_account(a.run_as);proof,raw=verify(namespace)
        if a.private_logs:create(a.private_logs,ROOT,{'execution.log':raw})
        write_report(a.output,proof)
        print(json.dumps({'pass':proof['pass'],'actual_control_groups':len(proof['controls']),'clusters_stopped':proof['clusters_stopped'],'owned_database_directory_removed':proof['owned_database_directory_removed'],'physical_erasure_verified':False,'production_changes':False,'requirements_closed':0}))
        return 0 if proof['pass'] else 1
    except (ValueError,KeyError,OSError,UnicodeError,AssertionError,RuntimeError,subprocess.SubprocessError):
        print(json.dumps({'state':'UNAVAILABLE','reason':'isolated_synthetic_backup_contract_refused','production_changes':False}),file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
