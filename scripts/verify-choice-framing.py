"""Execute invented private choice-frame commands; never claim MT accuracy."""
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
from tools.language_observations import digest

def verify(executable):
    controls=[]
    with tempfile.TemporaryDirectory(prefix='aitrust-choice-controls-') as directory:
        base=Path(directory).resolve();base.chmod(0o700)
        ref=base/'reference.txt';ref.write_text('You can remain undecided.')
        manifest=base/'corpus.json';corpus.create([('reference',ref)],manifest)
        record=corpus.load(manifest)
        text='Either agree or oppose.'
        private_subjects=[text]
        query=base/'subject.txt';query.write_text(text);query.chmod(0o600)
        context={'format':'choice-frame-context/v1','language':'en',
            'subject_sha256':digest(text),'manifest_sha256':record['manifest_sha256'],
            'frames':[{'span':[0,len(text)],'choices':[[7,12],[16,22]],
                'additional_reference':{'document_id':'reference','document_sha256':record['documents'][0]['sha256'],
                    'source_span':[0,len(ref.read_text())]}}]}
        annotation=base/'context.json';annotation.write_text(json.dumps(context));annotation.chmod(0o600)
        args=['--subject',str(query),'--corpus',str(manifest),'--context',str(annotation)]
        command=[str(executable),str(ROOT/'scripts/check-choice-framing.py')]
        def run(name,extra,expected):
            result=subprocess.run(command+extra,cwd=ROOT,capture_output=True,timeout=15)
            assert result.returncode==expected,name
            assert str(base).encode() not in result.stdout+result.stderr,name
            assert all(value.encode() not in result.stdout+result.stderr for value in private_subjects),name
            assert b'synthetic-private-canary' not in result.stdout+result.stderr,name
            controls.append({'case':name,'pass':True,'exit_status':expected})
            if expected:assert not result.stdout,name
            return result
        summary=json.loads(run('private_summary_no_raw_values',args,0).stdout)
        assert summary['supported_binary_patterns']==1 and not summary['tag_asserted']
        assert 'subject_sha256' not in summary and 'observations' not in summary
        target=base/'details';run('explicit_private_details',args+['--details',str(target)],0)
        artifact=target/'choice-observations.json';before=artifact.read_bytes();result=json.loads(before)
        assert result['observations'][0]['choice_spans']==[[7,12],[16,22]]
        assert not result['observations'][0]['additional_option_verified']
        assert artifact.stat().st_mode&0o077==0 and target.stat().st_mode&0o077==0
        run('existing_details_unchanged',args+['--details',str(target)],2);assert artifact.read_bytes()==before
        query.chmod(0o644);run('public_subject_refused',args,2);query.chmod(0o600)
        annotation.chmod(0o644);run('public_annotations_refused',args,2);annotation.chmod(0o600)
        manifest.chmod(0o644);run('public_corpus_refused',args,2);manifest.chmod(0o600)
        link=base/'link';link.symlink_to(query)
        run('subject_symlink_refused',['--subject',str(link),*args[2:]],2)
        hard=base/'hard';hard.hardlink_to(annotation);run('context_hardlink_refused',args,2);hard.unlink()
        query.write_bytes(b'synthetic-private-canary\xff');run('malformed_utf8_refused',args,2)
        query.write_text('x'*8001);run('subject_character_limit',args,2);query.write_text(text)
        annotation.write_text('{"a":1,"a":2}');run('duplicate_context_json_refused',args,2)
        annotation.write_text(json.dumps({**context,'subject_sha256':'0'*64}));run('stale_subject_binding_refused',args,2)
        annotation.write_text(json.dumps({**context,'manifest_sha256':'0'*64}));run('stale_corpus_binding_refused',args,2)
        annotation.write_text(json.dumps(context))
        new='I could agree and oppose.';query.write_text(new)
        context['subject_sha256']=digest(new);context['frames'][0].update(span=[0,len(new)],choices=[[8,13],[18,24]])
        annotation.write_text(json.dumps(context))
        missed=json.loads(run('no_supported_pattern_is_not_safety_clearance',args,0).stdout)
        assert missed['state']=='NO_SUPPORTED_PATTERN' and not missed['manipulation_established']
        for name,wording,construction,negated in [
            ('exclusive_only_markers','Only agree or oppose.','only_or',False),
            ('paired_negation_markers','Neither agree nor oppose.','neither_nor',True),
            ('not_only_has_no_signal_candidate','Not only agree or oppose.','only_or',True),
            ('mismatched_neither_or_is_unmatched','Neither agree or oppose.',None,False),
        ]:
            private_subjects.append(wording);query.write_text(wording)
            context['subject_sha256']=digest(wording)
            context['frames'][0].update(span=[0,len(wording)],choices=[
                [wording.index(word),wording.index(word)+len(word)] for word in ('agree','oppose')])
            annotation.write_text(json.dumps(context))
            detail=base/name
            parsed=json.loads(run(name,args+['--details',str(detail)],0).stdout)
            actual=json.loads((detail/'choice-observations.json').read_text())
            assert not parsed['tag_asserted'] and not parsed['manipulation_established']
            if construction is None:
                assert actual['state']=='NO_SUPPORTED_PATTERN' and actual['observations']==[]
            else:
                row=actual['observations'][0]
                assert row['construction']==construction and not row['negation_scope_resolved']
                assert bool(row['negation_marker_spans'])==negated
                assert row['proposed_signal']==(None if negated else 'sig.false_dilemma.v1')
                assert not row['additional_option_verified'] and not row['manipulation_established']
        run('arguments_do_not_echo_private_values',['--synthetic-private-canary'],2)
        demo=base/'practice'
        prepared=subprocess.run([str(executable),str(ROOT/'scripts/prepare-choice-demo.py'),
            '--output',str(demo)],capture_output=True,timeout=15,cwd=ROOT)
        assert prepared.returncode==0 and json.loads(prepared.stdout)['synthetic_only']
        assert str(base).encode() not in prepared.stdout+prepared.stderr
        controls.append({'case':'actual_demo_prepared_privately','pass':True,'exit_status':0})
        run('actual_demo_packet_command',['--packet',str(demo)],0)
        run('mixed_input_modes_refused',['--packet',str(demo),'--subject',str(query)],2)
        again=subprocess.run([str(executable),str(ROOT/'scripts/prepare-choice-demo.py'),
            '--output',str(demo)],capture_output=True,timeout=15,cwd=ROOT)
        assert again.returncode==2 and str(base).encode() not in again.stdout+again.stderr
        controls.append({'case':'demo_never_overwrites','pass':True,'exit_status':2})
    return {'captured_at':datetime.now(timezone.utc).isoformat(),'pass':True,
        'implemented_by':'Codex','actual_synthetic_cli_controls':controls,
        'private_test_directory_removed':True,'caller_alternative_verified':False,
        'independent_accuracy_evidence':False,'tag_asserted':False,'release_approved':False}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--python',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    report=verify(args.python.absolute());write_report(args.output,report)
    print(json.dumps({'pass':True,'actual_synthetic_controls':len(report['actual_synthetic_cli_controls']),
        'independent_accuracy':False,'tag_asserted':False}))
