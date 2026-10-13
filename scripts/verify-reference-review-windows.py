#!/usr/bin/env python3
"""Run invented private-file window controls; never independent freshness evidence."""
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from protocol import corpus
from protocol.reports import write_report
from tools.reference_revision import POLICY


def verify(executable, cache=None):
    cases=[]
    with tempfile.TemporaryDirectory(prefix='aitrust-window-controls-') as temporary:
        base=Path(temporary).resolve(); base.chmod(0o700)
        text=base/'reference.txt'; text.write_text('The room is empty.\n'); text.chmod(0o600)
        manifest=base/'corpus.json'; corpus.create([('manual', text)], manifest)
        record=corpus.load(manifest)
        query=base/'claim.txt'; query.write_text('There are people in the room.'); query.chmod(0o600)
        now=datetime.now(timezone.utc)
        def date(delta): return (now+timedelta(days=delta)).strftime('%Y-%m-%dT%H:%M:%SZ')
        policy={'profile':POLICY,'manifest_sha256':record['manifest_sha256'],'documents':[
            {'document_id':d['id'],'document_sha256':d['sha256'],'opens_at':date(-1),'expires_at':date(7)}
            for d in record['documents']]}
        prepared=base/'prepared'
        prepare=[str(executable),str(ROOT/'scripts/prepare-reference-review-windows.py'),
            '--corpus',str(manifest),'--opens-at',date(-1),'--expires-at',date(7),'--output',str(prepared)]
        built=subprocess.run(prepare,capture_output=True,timeout=10,cwd=ROOT)
        assert built.returncode==0 and json.loads(built.stdout)['documents_bound']==1
        path=prepared/'review-windows.json'
        assert json.loads(path.read_bytes())==policy and not path.stat().st_mode&0o077
        cases.append({'case':'actual_private_policy_preparation','pass':True,'exit_status':0})
        unchanged=path.read_bytes()
        built=subprocess.run(prepare,capture_output=True,timeout=10,cwd=ROOT)
        assert built.returncode==2 and path.read_bytes()==unchanged
        cases.append({'case':'policy_preparation_refuses_existing_folder','pass':True,'exit_status':2})
        command=[str(executable),str(ROOT/'scripts/check-nli-references.py')]
        common=['--corpus',str(manifest),'--subject',str(query)]
        def run(name, extra, status, reason=None):
            result=subprocess.run(command+common+extra,capture_output=True,timeout=65,cwd=ROOT)
            assert result.returncode==status, name
            assert str(base).encode() not in result.stdout+result.stderr and query.read_bytes() not in result.stdout+result.stderr, name
            data=json.loads(result.stdout if status==0 else result.stderr)
            assert data['tag_asserted'] is False, name
            if reason: assert data['reason']==reason and not result.stdout, name
            cases.append({'case':name,'pass':True,'exit_status':status,
                          'stdout_sha256':hashlib.sha256(result.stdout).hexdigest(),
                          'stderr_sha256':hashlib.sha256(result.stderr).hexdigest()})
            return data
        legacy=run('legacy_default_no_match',[],0)
        assert 'declared_review_windows' not in legacy and legacy['reference_freshness']=='unestablished'
        target=base/'details'
        active=run('active_window_no_model_and_private_details',['--review-windows',str(path),'--details',str(target)],0)
        assert active['declared_review_windows']['checked_before_and_after_comparison'] and not active['model_evaluation_obtained']
        assert active['reference_freshness']=='unestablished'
        assert sorted(p.name for p in target.iterdir())==['reference-observations.json','reference-window-check.json']
        assert not target.stat().st_mode&0o077 and all(not p.stat().st_mode&0o077 for p in target.iterdir())
        saved={p.name:p.read_bytes() for p in target.iterdir()}
        run('existing_details_refused',['--review-windows',str(path),'--details',str(target)],2,'invalid_private_input_or_method_contract')
        assert saved=={p.name:p.read_bytes() for p in target.iterdir()}
        original=path.read_bytes()
        policy['documents'][0]['expires_at']=date(-1);policy['documents'][0]['opens_at']=date(-2)
        path.write_bytes(corpus.encoded(policy))
        run('expired_policy_precedes_model_cache_access',['--threshold','.4','--review-windows',str(path)],2,'review_window_expired')
        path.write_bytes(original);policy=json.loads(original)
        policy['documents'][0]['opens_at']=date(1);path.write_bytes(corpus.encoded(policy))
        run('not_open_policy_precedes_model_cache_access',['--threshold','.4','--review-windows',str(path)],2,'review_window_not_open')
        policy=json.loads(original);policy['documents']=[];path.write_bytes(corpus.encoded(policy))
        run('missing_document_window',['--review-windows',str(path)],2,'review_window_missing')
        policy=json.loads(original);policy['manifest_sha256']='0'*64;path.write_bytes(corpus.encoded(policy))
        run('different_corpus_policy',['--review-windows',str(path)],2,'review_window_contract_refused')
        path.write_bytes(b'{"profile":"private-canary","profile":"duplicate"}')
        run('duplicate_policy_keys',['--review-windows',str(path)],2,'review_window_contract_refused')
        path.write_bytes(original);path.chmod(0o644)
        run('public_policy_permissions',['--review-windows',str(path)],2,'invalid_private_input_or_method_contract')
        path.chmod(0o600);link=base/'link';link.symlink_to(path)
        run('symlink_policy',['--review-windows',str(link)],2,'invalid_private_input_or_method_contract')
        link.unlink();hard=base/'hard';hard.hardlink_to(path)
        run('hardlinked_policy',['--review-windows',str(path)],2,'invalid_private_input_or_method_contract')
        hard.unlink()
        if cache is not None:
            model_target=base/'model-details'
            actual=run('actual_guarded_model_comparison',['--threshold','.4','--review-windows',str(path),
                '--model-cache',str(cache),'--details',str(model_target)],0)
            assert actual['model_evaluation_obtained'] and actual['passages_evaluated']==1
            result=json.loads((model_target/'reference-observations.json').read_text())
            assert result['observations'][0]['top_model_labels']==['contradiction']
            assert not actual['declared_review_windows']['source_freshness_established']
            assert not actual['truth_established'] and not actual['independent_corroboration']
    sources=['tools/reference_review_window.py','tools/reference_revision.py','protocol/corpus.py',
             'scripts/prepare-reference-review-windows.py',
             'scripts/check-nli-references.py','scripts/verify-reference-review-windows.py']
    return {'captured_at':datetime.now(timezone.utc).isoformat(),'pass':True,'cases':cases,
        'actual_model_inference':cache is not None,'invented_inputs_only':True,
        'sources':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in sources},
        'private_test_directory_removed':not base.exists(),'independent_accuracy_evidence':False,
        'source_freshness_established':False,'requirements_closed':0,'tag_asserted':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--python',type=Path,default=Path(sys.executable))
    parser.add_argument('--model-cache',type=Path)
    parser.add_argument('--output',type=Path,default=Path('output/verification/reference-windows.json'))
    args=parser.parse_args()
    result=verify(args.python,args.model_cache)
    write_report(args.output,result)
    print(json.dumps({'pass':True,'actual_cli_controls':len(result['cases']),'actual_model_inference':result['actual_model_inference']}))
