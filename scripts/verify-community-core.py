#!/usr/bin/env python3
"""Exercise the real private synthetic CLI, then remove its temporary store."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import uuid
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from protocol.reports import write_report
from tools import community_core as core

SOURCES=('tools/community_core.py','tools/community_store.py','tools/blind_review_io.py','scripts/community-workbench.py',
         'scripts/verify-community-core.py','protocol/reports.py','tests/test_community_core.py','tests/test_community_store.py','tests/test_community_cli.py')


def main():
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output');a=p.parse_args()
    before={s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in SOURCES};controls=[];calls=0
    with tempfile.TemporaryDirectory(prefix='aitrust-community-') as directory:
        home=Path(directory).resolve();home.chmod(0o700);store=home/'workbench'
        def call(operation,*args,actor=None,data=None,good=True):
            nonlocal calls
            argv=[sys.executable,str(ROOT/'scripts/community-workbench.py'),operation,'--root',str(store),*map(str,args)]
            if actor:argv+=['--actor',actor]
            raw=core.encode({'format':core.REQUEST,'synthetic_only':True,'request_id':str(uuid.uuid4()),'operation':'submit','data':data}) if data is not None else None
            r=subprocess.run(argv,input=raw,capture_output=True,timeout=6);calls+=1
            assert r.returncode==(0 if good else 2) and (not r.stderr if good else not r.stdout)
            assert b'QUEUED_PRIVATE_CANARY' not in r.stderr and b'Traceback' not in r.stderr
            return json.loads(r.stdout) if good else None
        call('init','--synthetic-only');controls.append('actual_private_store_initialization')
        post=call('apply',actor='user-one',data={'body':'QUEUED_PRIVATE_CANARY','consent_public':True})
        assert call('public')['items']==[] and call('replay')['events']==[]
        controls.append('unapproved_text_never_public')
        # Non-submit operations use the real fixed request contract directly.
        def apply(actor,op,data):
            nonlocal calls
            raw=core.encode({'format':core.REQUEST,'synthetic_only':True,'request_id':str(uuid.uuid4()),'operation':op,'data':data})
            r=subprocess.run([sys.executable,str(ROOT/'scripts/community-workbench.py'),'apply','--root',str(store),'--actor',actor],input=raw,capture_output=True,timeout=6);calls+=1
            assert r.returncode==0 and not r.stderr;return json.loads(r.stdout)
        post=apply('mod-one','approve',{'post_id':post['id'],'version':1})
        reply=apply('official-one','reply',{'post_id':post['id'],'version':post['version'],'body':'Invented official reply','consent_public':True})
        apply('mod-two','approve',{'post_id':reply['id'],'version':1});assert len(call('public')['items'])==2
        controls.append('official_reply_reviewed_independently')
        post=apply('mod-one','retract',{'post_id':post['id'],'version':post['version'],'reason':'privacy'})
        for value in (call('public'),call('replay')):assert 'QUEUED_PRIVATE_CANARY' not in json.dumps(value)
        out=home/'view.html';call('export','--output',out,'--html');assert 'QUEUED_PRIVATE_CANARY' not in out.read_text()
        controls.append('current_replay_and_export_scrub_removed_body')
        appeal=apply('user-one','appeal',{'post_id':post['id'],'version':post['version']})
        apply('mod-two','resolve_appeal',{'appeal_id':appeal['id'],'decision':'reconsider'})
        assert call('public')['items'][0]['body'] is None;controls.append('independent_appeal_never_republishes_scrubbed_text')
        call('export','--output',out,good=False);controls.append('existing_export_not_overwritten')
        call('remove','--confirm-synthetic-removal');assert not store.exists() and out.exists()
        controls.append('owned_store_removed_saved_copy_limit_explicit')
    assert all(hashlib.sha256((ROOT/s).read_bytes()).hexdigest()==v for s,v in before.items())
    row={'captured_at':datetime.now(timezone.utc).isoformat(),'pass':True,'sources':before,'source_unchanged':True,
         'actual_cli_calls':calls,'controls':controls,'temporary_store_removed':True,'synthetic_only':True,
         'new_endpoints':0,'public_service_enabled':False,'real_user_data_collected':False,'independent_accuracy_evidence':False,'full_requirements_closed':0}
    if a.output:write_report(a.output,row)
    print(json.dumps(row,indent=2))


if __name__=='__main__':main()
