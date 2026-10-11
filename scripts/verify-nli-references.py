"""Execute invented reference-checker cases and privacy controls, not tag accuracy."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from protocol import corpus
from protocol.reports import write_report

def verify(executable,cache):
    controls=[]
    with tempfile.TemporaryDirectory(prefix='aitrust-reference-controls-') as temporary:
        base=Path(temporary).resolve();base.chmod(0o700)
        reference=base/'manual.txt'
        reference.write_text('The room is empty.\nThe sky is blue.\nThe door was closed yesterday.\n')
        manifest=base/'corpus.json';corpus.create([('manual',reference)],manifest)
        query=base/'query.txt';query.write_text('There are people in the room.');query.chmod(0o600)
        command=[str(executable),str(ROOT/'scripts/check-nli-references.py')]
        common=['--corpus',str(manifest),'--subject',str(query)]
        def run(name,args,expected):
            output=subprocess.run(command+args,capture_output=True,timeout=65,cwd=ROOT)
            assert output.returncode==expected,name
            assert str(base).encode() not in output.stdout+output.stderr,name
            assert query.read_bytes() not in output.stdout+output.stderr,name
            assert b'synthetic-private-canary' not in output.stdout+output.stderr,name
            controls.append({'case':name,'pass':True,'exit_status':expected})
            if expected:assert not output.stdout and json.loads(output.stderr)['state']=='UNAVAILABLE',name
            return output
        miss=json.loads(run('default_selection_miss_without_loading_model',common,0).stdout)
        assert miss['state']=='no_similar_passage' and not miss['model_evaluation_obtained']
        args=common+['--model-cache',str(cache),'--threshold','.4']
        details=base/'details'
        success=json.loads(run('actual_selected_reference_model_and_private_details',args+['--details',str(details)],0).stdout)
        assert success['passages_evaluated']==1 and not success['tag_asserted']
        artifact=details/'reference-observations.json';before=artifact.read_bytes();record=json.loads(before)
        row=record['observations'][0]
        assert row['reference']['source_span']==[0,18] and row['claim_span']==[0,29]
        assert row['direction']=='reference_is_premise_claim_is_hypothesis'
        assert row['top_model_labels']==['contradiction']
        assert record['model_identity']['python_runtime']['system'] in ('Darwin','Linux')
        assert not details.stat().st_mode&0o077 and not artifact.stat().st_mode&0o077
        assert 'observations' not in success and 'subject_sha256' not in success
        run('existing_details_unchanged',args+['--details',str(details)],2)
        assert artifact.read_bytes()==before
        query.write_text('The room is empty.')
        equal=base/'equal'
        run('same_passage_model_relationship',common+['--model-cache',str(cache),'--details',str(equal)],0)
        assert json.loads((equal/'reference-observations.json').read_bytes())['observations'][0]['top_model_labels']==['entailment']
        query.write_text('The sky is blue. There are five books on the shelf.')
        # This input is one claim unit. The separate retained self-pair error is
        # not transformed into a reference falsehood or an independent benchmark.
        run('mixed_claim_stays_research_observation',common+['--model-cache',str(cache),'--threshold','.4'],0)
        query.write_text('synthetic-private-canary '+('x '*1000))
        run('subject_character_limit',common,2)
        query.write_bytes(b'synthetic-private-canary\xff')
        run('strict_utf8_subject',common,2)
        query.write_text('synthetic-private-canary é')
        run('unsupported_lexical_subject',common,2)
        query.write_text('The room is empty.');query.chmod(0o644)
        run('public_subject_refused',common,2);query.chmod(0o600)
        link=base/'query-link';link.symlink_to(query)
        run('subject_symlink_refused',['--corpus',str(manifest),'--subject',str(link)],2)
        hard=base/'query-hard';hard.hardlink_to(query)
        run('subject_hardlink_refused',common,2);hard.unlink()
        manifest.chmod(0o644);run('public_corpus_refused',common,2);manifest.chmod(0o600)
        run('selected_passage_requires_model_cache',common,2)
        run('selected_passage_changed_model_refuses',common+['--model-cache',str(base)],2)
        original=manifest.read_bytes();manifest.write_text('{"private":"synthetic-private-canary"}')
        run('corrupt_corpus_identity_refused',common,2);manifest.write_bytes(original)
        run('invalid_candidate_bound',common+['--maximum','6'],2)
        run('invalid_threshold',common+['--threshold','nan'],2)
    return {'captured_at':datetime.now(timezone.utc).isoformat(),'pass':True,
        'actual_model_inference':True,'synthetic_only':True,'controls':controls,
        'retained_default_retrieval_miss':True,'independent_accuracy_evidence':False,
        'tag_asserted':False,'release_approved':False,'private_test_directory_removed':True}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--python',type=Path,required=True)
    parser.add_argument('--model-cache',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    report=verify(args.python.absolute(),args.model_cache.absolute())
    write_report(args.output,report)
    print(json.dumps({'pass':True,'actual_synthetic_controls':len(report['controls']),
        'independent_accuracy':False,'tag_asserted':False}))
