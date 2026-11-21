"""Finite additive wording, not exclusive-choice or manipulation classification."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

import pytest
from protocol import corpus
from protocol.normalization import normalize_nfc
from tools.language_observations import digest
from tools import choice_framing,mt_workflow

ROOT=Path(__file__).resolve().parents[1]

def packet(text,words=('tea','coffee')):
    normalized=normalize_nfc(text);reference='Water is also listed.'
    doc={'id':'reference','text':reference,'sha256':corpus.sha(reference.encode())}
    content={'format':corpus.VERSION,'documents':[doc]};record={**content,'manifest_sha256':corpus.sha(corpus.encoded(content))}
    frame={'span':[0,len(normalized)],'choices':[[normalized.index(w),normalized.index(w)+len(w)]for w in words],
        'additional_reference':{'document_id':'reference','document_sha256':doc['sha256'],'source_span':[0,len(reference)]}}
    return record,{'format':'choice-frame-context/v1','language':'en','subject_sha256':digest(normalized),'manifest_sha256':record['manifest_sha256'],'frames':[frame]}

def save_packet(folder,text,words=('tea','coffee')):
    folder.mkdir(mode=0o700);record,context=packet(text,words)
    for name,value in [('subject.txt',text),('corpus.json',json.dumps(record)),('context.json',json.dumps(context))]:
        p=folder/name;p.write_text(value);p.chmod(0o600)
    return folder

@pytest.mark.parametrize('text,words',[
    ('Not only tea but also coffee.',('tea','coffee')),
    ('NOT\tONLY tea, BUT\tALSO coffee.',('tea','coffee')),
    ('A lesson quotes: "not only tea but also coffee".',('tea','coffee')),
    ('Safety advice: not only evacuate but also call.',('evacuate','call')),
    ('😀 Not only cafe\u0301 but also tea.',('café','tea')),
])
def test_additive_exact_spans_never_binary_or_signal(text,words):
    record,context=packet(text,words);out=choice_framing.observe(text,record,context);row=out['observations'][0];n=normalize_nfc(text)
    assert out['profile']=='caller-bound-choice-framing-observation/1.3.0'
    assert row['construction']=='not_only_but_also' and row['binary_marker_spans']==[]
    assert [' '.join(n[a:b].lower().split())for a,b in row['additive_marker_spans']]==['not only','but also']
    assert [n[a:b]for a,b in row['choice_spans']]==list(words)
    assert [n[a:b].lower()for a,b in row['negation_marker_spans']]==['not']
    assert row['proposed_signal'] is None and 'not_exclusive_alternatives'in row['meaning']
    assert all(row[k]is False for k in ['negation_scope_resolved','additional_option_verified','exhaustiveness_established','quoted_or_recommended_resolved','manipulation_established'])
    assert not out['tag_asserted'] and not out['release_approved'] and text not in json.dumps(out)

@pytest.mark.parametrize('text',[
    'Not only tea but coffee.','Only tea but also coffee.',
    'Not only tea but also perhaps coffee.','Notonly tea but also coffee.',
    '_not only tea but also coffee.','énot only tea but also coffee.',
    'Not onlytea but also coffee.','Not only tea but alsocoffee.',
    'Not only teabut also coffee.','Not only tea but alſo coffee.',
    'Not only tea but ALSOcoffee.','Not only tea or also coffee.',
])
def test_incomplete_embedded_or_confusable_additive_is_unmatched(text):
    record,context=packet(text);out=choice_framing.observe(text,record,context)
    assert out['state']=='NO_SUPPORTED_PATTERN' and out['observations']==[]
    assert out['unmatched_selected_frames']==[[0,len(text)]] and not out['tag_asserted']

@pytest.mark.parametrize('text,kind,signal',[
    ('Either tea or coffee.','either_or','sig.false_dilemma.v1'),
    ('Only tea or coffee.','only_or','sig.false_dilemma.v1'),
    ('Neither tea nor coffee.','neither_nor',None),
    ('Between tea and coffee.','between_and',None),
    ('Not only tea or coffee.','only_or',None),
])
def test_legacy_shapes_and_candidate_meanings_preserved(text,kind,signal):
    r,c=packet(text);row=choice_framing.observe(text,r,c)['observations'][0]
    assert row['construction']==kind and row['proposed_signal']==signal
    assert len(row['binary_marker_spans'])==2 and 'additive_marker_spans'not in row
    assert row['meaning']=='caller_selected_two_mentioned_choices_with_caller_nominated_additional_passage'

@pytest.mark.parametrize('bad',['subject','reference','boolean','extra','overlap'])
def test_additive_does_not_bypass_packet_binding_or_all_frames_validation(bad):
    text='Not only tea but also coffee.';r,c=packet(text)
    if bad=='subject':c['subject_sha256']='0'*64
    if bad=='reference':c['frames'][0]['additional_reference']['document_sha256']='0'*64
    if bad=='boolean':c['frames'][0]['choices'][0][0]=True
    if bad=='extra':c['frames'][0]['private-extra']='PRIVATE_CANARY'
    if bad=='overlap':c['frames'].append(copy.deepcopy(c['frames'][0]))
    with pytest.raises(ValueError):choice_framing.observe(text,r,c)

def test_real_private_cli_additive_zero_binary_no_echo_and_no_overwrite(tmp_path):
    tmp_path.chmod(0o700);text='Not only tea but also coffee.';folder=save_packet(tmp_path/'packet',text);details=tmp_path/'details'
    command=[sys.executable,'-I','-S','-B',str(ROOT/'scripts/check-choice-framing.py'),'--packet',str(folder),'--details',str(details)]
    child=subprocess.run(command,capture_output=True,timeout=15);assert child.returncode==0
    brief=json.loads(child.stdout);raw=(details/'choice-observations.json').read_bytes()
    assert brief['supported_additive_patterns']==1 and brief['supported_binary_patterns']==0
    assert 'not exclusive alternatives'in brief['result'] and not brief['tag_asserted']
    assert text.encode()not in child.stdout+child.stderr and str(tmp_path).encode()not in child.stdout+child.stderr
    assert details.stat().st_mode&0o777==0o700 and(details/'choice-observations.json').stat().st_mode&0o777==0o600
    again=subprocess.run(command,capture_output=True,timeout=15);assert again.returncode==2
    assert raw==(details/'choice-observations.json').read_bytes()

def test_current_independent_consumer_and_failure_recovery(tmp_path):
    tmp_path.chmod(0o700);text='Not only tea but also coffee.';folder=save_packet(tmp_path/'packet',text)
    out=mt_workflow.check(text,['choice','authority'],'en',folder);assert out['state']=='COMPLETE'
    row=out['checks'][0];assert row['method']=='caller-bound-choice-framing-observation/1.3.0'
    assert row['observations'][0]['construction']=='not_only_but_also' and len(row['observations'][0]['subject_spans'])==4
    assert 'not exclusive alternatives'in mt_workflow.brief(row)
    assert not out['tag_asserted'] and not out['intent_established']
    real=mt_workflow.SUPERVISE
    def faulty(argv,**kw):
        if json.loads(kw['input'])['component']=='choice':return subprocess.CompletedProcess(argv,2,b'',b'PRIVATE_CANARY')
        return real(argv,**kw)
    with patch.object(mt_workflow,'SUPERVISE',side_effect=faulty):
        failed=mt_workflow.check(text,['choice','authority'],'en',folder)
    assert failed['state']=='PARTIAL' and failed['checks'][0]['state']=='UNAVAILABLE'
    assert failed['checks'][1]['state']=='NO_SUPPORTED_PATTERN' and 'PRIVATE_CANARY'not in json.dumps(failed)
    assert mt_workflow.check(text,['choice'],'en',folder)['state']=='COMPLETE'


def test_mixed_additive_and_legacy_counts_and_brief_stay_separate(tmp_path):
    import importlib.util
    spec=importlib.util.spec_from_file_location('additive_choice_cli',ROOT/'scripts/check-choice-framing.py')
    cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)
    text='Not only tea but also coffee. Either walk or cycle.';r,c=packet(text)
    first_end=text.index('.')+1;c['frames'][0]['span']=[0,first_end]
    second=copy.deepcopy(c['frames'][0]);second['span']=[first_end+1,len(text)]
    second['choices']=[[text.index(w),text.index(w)+len(w)]for w in ('walk','cycle')];c['frames'].append(second)
    out=choice_framing.observe(text,r,c);brief=cli.summary(out,False)
    assert brief['selected_frames_checked']==2 and brief['supported_binary_patterns']==brief['supported_additive_patterns']==1
    assert 'includes additive mentions and two-choice markers'in brief['result']
    assert [x['construction']for x in out['observations']]==['not_only_but_also','either_or']
    assert out['observations'][0]['proposed_signal']is None
    row={'component':'choice','state':'OBSERVATIONS','observations':[{'construction':x['construction']}for x in out['observations']]}
    assert 'include additive mentions'in mt_workflow.brief(row)

@pytest.mark.parametrize('example',['binary','additive'])
def test_actual_preparer_fixed_examples_are_complete_private_and_usable(tmp_path,example):
    tmp_path.chmod(0o700);folder=tmp_path/'demo';prepare=[sys.executable,'-I','-S','-B',str(ROOT/'scripts/prepare-choice-demo.py'),'--example',example,'--output',str(folder)]
    made=subprocess.run(prepare,capture_output=True,timeout=15);assert made.returncode==0
    assert json.loads(made.stdout)['synthetic_only'] and not json.loads(made.stdout)['user_example_read']
    checked=subprocess.run([sys.executable,'-I','-S','-B',str(ROOT/'scripts/check-choice-framing.py'),'--packet',str(folder)],capture_output=True,timeout=15)
    assert checked.returncode==0;brief=json.loads(checked.stdout)
    assert brief['supported_additive_patterns']==int(example=='additive') and brief['supported_binary_patterns']==int(example=='binary')
    out=mt_workflow.check((folder/'subject.txt').read_text(),['choice'],'en',folder)
    assert out['state']=='COMPLETE' and out['checks'][0]['observations'][0]['construction']==('not_only_but_also'if example=='additive'else'either_or')
    before={p.name:p.read_bytes()for p in folder.iterdir()}
    assert subprocess.run(prepare,capture_output=True,timeout=15).returncode==2
    assert before=={p.name:p.read_bytes()for p in folder.iterdir()}

def test_preparer_unknown_example_uses_fixed_private_error(tmp_path):
    child=subprocess.run([sys.executable,'-I','-S','-B',str(ROOT/'scripts/prepare-choice-demo.py'),'--example','PRIVATE_CANARY','--output',str(tmp_path/'out')],capture_output=True,timeout=15)
    assert child.returncode==2 and b'PRIVATE_CANARY'not in child.stderr+child.stdout and str(tmp_path).encode()not in child.stderr+child.stdout
    assert not(tmp_path/'out').exists()
