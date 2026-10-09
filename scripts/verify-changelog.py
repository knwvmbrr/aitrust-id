#!/usr/bin/env python3
import argparse
import json
import os
from changelog_core import ROOT, git, verify, verify_staged
p=argparse.ArgumentParser(description='Require a fresh scoped event for actual Git changes, not merely a nonempty changelog.')
p.add_argument('--base',default=os.environ.get('AITRUST_CHANGELOG_BASE'))
p.add_argument('--head',default=os.environ.get('AITRUST_CHANGELOG_HEAD','HEAD'))
p.add_argument('--staged',action='store_true',help='Check exactly the Git index, including evidence and event content')
a=p.parse_args()
if os.environ.get('CI') and not a.base:
    p.error('CI requires an explicit --base / AITRUST_CHANGELOG_BASE; clean checkout must not skip changed files')
if a.base == '0' * 40:
    # First push of a branch has no previous remote SHA; inspect its latest commit.
    try:a.base=git(ROOT,'rev-parse','HEAD^').strip()
    except Exception:a.base=git(ROOT,'hash-object','-t','tree','/dev/null').strip()
r=verify_staged() if a.staged else verify(base=a.base,head=a.head)
print(json.dumps(r,indent=2))
raise SystemExit(0 if r['pass'] else 1)
