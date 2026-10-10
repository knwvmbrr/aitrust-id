#!/usr/bin/env python3
import argparse
import json
import os
from changelog_core import ROOT, select_change_base, verify, verify_staged
p=argparse.ArgumentParser(description='Require a fresh scoped event for actual Git changes, not merely a nonempty changelog.')
p.add_argument('--base',default=os.environ.get('AITRUST_CHANGELOG_BASE'))
p.add_argument('--head',default=os.environ.get('AITRUST_CHANGELOG_HEAD','HEAD'))
p.add_argument('--default-ref',default=os.environ.get('AITRUST_CHANGELOG_DEFAULT_REF'))
p.add_argument('--event-ref',default=os.environ.get('GITHUB_REF'))
p.add_argument('--staged',action='store_true',help='Check exactly the Git index, including evidence and event content')
a=p.parse_args()
if os.environ.get('CI') and not a.base:
    p.error('CI requires an explicit --base / AITRUST_CHANGELOG_BASE; clean checkout must not skip changed files')
try:
    a.base=select_change_base(ROOT,a.base,a.head,a.default_ref,a.event_ref)
except ValueError as error:
    p.error(str(error))
r=verify_staged() if a.staged else verify(base=a.base,head=a.head)
print(json.dumps(r,indent=2))
raise SystemExit(0 if r['pass'] else 1)
