#!/usr/bin/env python3
"""Write an attributed scoped change and evidence record together; never grant accuracy acceptance."""
import argparse
import datetime as dt
import json
import os
import shlex
import subprocess
import sys
import uuid
from changelog_core import ROOT, EVENT_DIR, changes, digest, entry, git, safe_path, validate_record

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for flag in ('changed','proves','limits','author','slug'):
        p.add_argument('--'+flag,required=True)
    p.add_argument('--records',nargs='+',required=True)
    p.add_argument('--files',nargs='+',help='Explicit repository-relative files; otherwise current changes')
    p.add_argument('--evidence',nargs='*',default=[],help='Existing public evidence files to hash')
    p.add_argument('--gate',help='Check command parsed into argv, no shell expansion; do not pass secrets')
    p.add_argument('--historical-source',help='Retrospective record of a previously committed change')
    p.add_argument('--dry-run',action='store_true')
    a=p.parse_args()
    import re
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',a.slug):p.error('slug must be kebab-case')
    moment=dt.datetime.now(dt.timezone.utc)
    rid=moment.strftime('%Y-%m-%d-%H%M%S')+'-'+a.slug+'-'+uuid.uuid4().hex[:8]
    files=a.files if a.files is not None else ([] if a.historical_source else changes(ROOT))
    r={'schema_version':1,'id':rid,'recorded_at':moment.isoformat(),'author':a.author,'kind':'retrospective' if a.historical_source else 'change','claim_level':'engineering_only','independent_release_validated':False,'source_base':git(ROOT,'rev-parse','HEAD').strip(),'changed':a.changed,'proves':a.proves,'limits':a.limits,'scope_ids':a.records,'files':{f:digest(ROOT,f) for f in files},'evidence':[],'checks':[]}
    if a.historical_source:r['historical_source_commit']=git(ROOT,'rev-parse',a.historical_source+'^{commit}').strip()
    for f in a.evidence:
        h=digest(ROOT,f)
        if h is None:p.error('Missing evidence '+f)
        r['evidence'].append({'path':f,'sha256':h})
    if a.gate:
        argv=shlex.split(a.gate)
        if not argv:p.error('Empty check command')
        # Do not store stdout/stderr: check output may contain private operational information.
        completed=subprocess.run(argv,cwd=ROOT,timeout=600)
        if completed.returncode:
            print('Check failed; no changelog entry or event written.',file=sys.stderr);return 1
        r['checks'].append({'argv':argv,'exit_status':completed.returncode,'pass':True,'finished_at':dt.datetime.now(dt.timezone.utc).isoformat()})
    name=EVENT_DIR+'/'+rid+'.json'
    problems=validate_record(ROOT,r,name,current=True)
    if problems:
        print('\n'.join(problems),file=sys.stderr);return 1
    if a.dry_run:
        print(json.dumps(r,indent=2));return 0
    target=safe_path(ROOT,name);target.parent.mkdir(parents=True,exist_ok=True)
    lock=target.parent/'.writer.lock'
    # Exclusive writer lock prevents two assistants from losing each other's entries.
    try:fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    except FileExistsError:
        print('Another writer holds the changelog lock; retry after it finishes.',file=sys.stderr);return 1
    os.close(fd)
    old=(ROOT/'CHANGELOG.md').read_text()
    try:
        heading='## Unreleased — '+moment.date().isoformat()
        text=old
        if heading not in text:
            at=text.find('\n## ')
            if at<0:at=len(text)
            text=text[:at]+'\n'+heading+'\n\n'+text[at:].lstrip('\n')
        at=text.index(heading)+len(heading)
        text=text[:at]+'\n\n'+entry(r,name)+text[at:]
        with target.open('x') as f:f.write(json.dumps(r,indent=2)+'\n')
        temp=ROOT/'CHANGELOG.md.tmp'
        temp.write_text(text)
        temp.replace(ROOT/'CHANGELOG.md')
    except Exception:
        target.unlink(missing_ok=True)
        raise
    finally:
        lock.unlink(missing_ok=True)
    print('Recorded '+name+' with contributor '+a.author+'. No completion percentage changed.')
    return 0
if __name__=='__main__':
    try:raise SystemExit(main())
    except (ValueError,OSError,subprocess.SubprocessError) as exc:
        print(str(exc),file=sys.stderr);raise SystemExit(1)
