#!/usr/bin/env python3
"""Run actual disposable OIDC/PostgreSQL acceptance in an isolated Linux namespace."""
import argparse,json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from protocol.reports import write_report
from tools.backup_retention import prepare_account

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run-as',required=True);p.add_argument('--keycloak',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if sys.platform!='linux' or os.geteuid()!=0:raise SystemExit('Isolated Linux wrapper required')
    if os.stat('/proc/self/ns/net').st_ino==os.stat('/proc/1/ns/net').st_ino:raise SystemExit('Fresh isolated network namespace required')
    subprocess.run(['/usr/sbin/ip','link','set','lo','up'],check=True,capture_output=True)
    namespace=prepare_account(a.run_as)
    from tools.organization_directory_lab import verify
    row=verify(a.keycloak,namespace);write_report(a.output,row);print(json.dumps(row));return 0 if row.get('pass') is True else 1
if __name__=='__main__':raise SystemExit(main())
