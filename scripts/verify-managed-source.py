#!/usr/bin/env python3
"""Authenticate separately selected source evidence and exercise only fixed PS source."""
from pathlib import Path
import argparse
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools.source_snapshot_managed import verify_managed,ManagedSourceUnavailable,ManagedSourceUncertain

class Parser(argparse.ArgumentParser):
    def error(self,message):raise ManagedSourceUnavailable()

def main(argv=None):
    parser=Parser(description=__doc__)
    for name in ('artifact','packet','spdx','bundle','trusted-root','source-commit','output'):
        parser.add_argument('--'+name,required=True)
    parser.add_argument('--trusted-git-root',default=str(ROOT))
    try:
        a=parser.parse_args(argv)
        verify_managed(a.artifact,a.packet,a.spdx,a.bundle,a.trusted_root,a.output,source_commit=a.source_commit,root=Path(a.trusted_git_root))
        print('Managed source verified; three finite PS source probes completed.')
        print('Private staging retained. Not an accuracy, legal or fourteen-route completion claim.')
        return 0
    except ManagedSourceUncertain:
        print('Managed source publication UNCERTAIN. Summary/private bytes may remain; inspect before retry.',file=sys.stderr);return 3
    except ManagedSourceUnavailable:
        print('Managed source UNAVAILABLE. Private bytes may remain; no accepted summary was published.',file=sys.stderr);return 2

if __name__=='__main__':raise SystemExit(main())
