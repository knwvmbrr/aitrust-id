#!/usr/bin/env python3
"""Inspect only the fixed iOS runtime notice/source-offer cohort."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools import ios_runtime_obligations as ios


def main():
    p=argparse.ArgumentParser(description=__doc__)
    mode=p.add_mutually_exclusive_group()
    mode.add_argument('--prepare',metavar='NEW_PRIVATE_DIRECTORY')
    mode.add_argument('--ipa',metavar='RECEIVED_IPA')
    mode.add_argument('--app',metavar='APP_RESOURCE_DIRECTORY')
    p.add_argument('--share',metavar='SHARE_RESOURCE_DIRECTORY')
    a=p.parse_args()
    if bool(a.app)!=bool(a.share): p.error('--app and --share are required together')
    try:
        if a.prepare: result=ios.prepare(a.prepare)
        elif a.ipa: result=ios.check_ipa(a.ipa)
        elif a.app: result=ios.check_directories(a.app,a.share)
        else: result=ios.projection()['report']
        print(json.dumps(result,sort_keys=True,allow_nan=False)); return 0
    except ios.OutputUncertain:
        print('Private runtime output may remain; inspect before retrying.',file=sys.stderr); return 2
    except (ios.Unavailable,OSError,ValueError):
        print('Selected iOS runtime carrying unavailable.',file=sys.stderr); return 2

if __name__=='__main__': raise SystemExit(main())
