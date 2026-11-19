"""Selected actual quotation workflow, canonical replay and sibling fault boundaries."""
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from unittest.mock import patch

import pytest
from protocol.normalization import normalize_nfc
from tools import mt_workflow as w
from tools import mt_quotation_component as component
from tools import authority_quotation as canonical

ROOT=Path(__file__).resolve().parents[1]
CLI=[sys.executable,'-I','-S','-B',str(ROOT/'scripts/check-mt-evidence.py'),'--language','en']
TEXT='The training example says "Experts agree".'


def invoke(text,*args):
    return subprocess.run(CLI+list(args),input=text,capture_output=True,timeout=15)


@pytest.mark.parametrize('text',[TEXT,'Experts agree; the example is "https://example.invalid".',
    '"Experts agree: https://example.invalid"; studies show benefits [12].',
    'Cafe\u0301: "Experts agree". Studies show benefits.',
    '"Experts agree" and "https://example.invalid". Doctors recommend it.',
    'A plain unrelated paragraph.'])
def test_real_selected_check_preserves_complete_canonical_record_and_raw_NFC_identity(text):
    result=w.check(text,[w.QUOTATION],'en');assert result['state']=='COMPLETE'
    assert result['format']==w.CONTEXT_PROFILE
    row=result['checks'][0];assert row['original']==canonical.observe(text,'en')[1]
    assert row['raw_subject_sha256']==hashlib.sha256(text.encode()).hexdigest()==result['raw_subject_sha256']
    assert row['subject_sha256']==hashlib.sha256(normalize_nfc(text).encode()).hexdigest()
    assert row['raw_subject_characters']==len(text) and row['raw_subject_bytes']==len(text.encode())
    assert row['sources']==w.identity(w.QUOTATION) and row['limitations']==w.LIMITS
    assert row['subject_text_included'] is False and text not in json.dumps(result)
    assert result['tag_asserted'] is result['intent_established'] is result['independent_corroboration'] is False


def test_legacy_authority_and_profile_are_not_silently_changed_or_selected():
    legacy=w.check(TEXT,['authority'],'en');new=w.check(TEXT,[w.QUOTATION],'en')
    assert legacy['format']==w.PROFILE and 'raw_subject_sha256' not in legacy
    assert legacy['checks'][0]['state']=='OBSERVATIONS' and len(legacy['checks'][0]['observations'])==1
    assert new['checks'][0]['state']=='NO_SUPPORTED_PATTERN' and new['checks'][0]['counts']['quoted_phrase_count']==1
    with patch.object(w,'run_component',wraps=w.run_component) as runner:
        result=w.check('Buy now.',['urgency'],'en')
    assert [c.args[0] for c in runner.call_args_list]==['urgency'] and result['format']==w.PROFILE


@pytest.mark.parametrize('text',['“Experts agree”','"Experts agree','`Experts agree`','"" '*65,'Experts agree; '*129,'[1] '*257])
def test_unsupported_quotation_context_is_partial_only_for_selected_candidate(text):
    result=w.check('Buy now. '+text,['urgency',w.QUOTATION],'en')
    assert result['state']=='PARTIAL'
    assert [r['state'] for r in result['checks']]==['OBSERVATIONS','UNAVAILABLE']
    assert invoke(('Buy now. '+text).encode(),'--check','urgency','--check',w.QUOTATION).returncode==3


def test_closed_shape_and_exact_canonical_replay_reject_omission_or_evidence_tampering():
    text='"Experts agree". Studies show benefits.'
    sources=w.identity(w.QUOTATION);good=w.run_component(w.QUOTATION,text);assert good['state']=='OBSERVATIONS'
    mutations=[
      lambda r:r['original'].update(raw_input='SYNTHETIC_PRIVATE_CANARY'),
      lambda r:r['original']['parameters'].update(extra='SYNTHETIC_PRIVATE_CANARY'),
      lambda r:r['original']['source_sha256'].update({'tools/authority_quotation.py':'0'*64}),
      lambda r:r.update(raw_subject_sha256='0'*64),
      lambda r:r['original']['quoted_phrases'][0].update(phrase_span=[0,9999]),
      lambda r:r['original'].update(quote_endorsement_interpreted=0),
    ]
    for mutate in mutations:
        bad=copy.deepcopy(good);mutate(bad)
        with pytest.raises(ValueError):w.validate(bad,w.QUOTATION,text,sources)
    # This omission is internally coherent and shape-valid. Only canonical replay
    # reveals that an actual outside phrase was suppressed.
    omitted=copy.deepcopy(good);omitted['original']['outside_markerless_phrases']=[]
    omitted['original']['outside_supported_quotes_without_marker']=omitted['counts']['outside_supported_quotes_without_marker']=0
    omitted['original']['state']=omitted['state']='NO_SUPPORTED_PATTERN'
    component.validate_shape(omitted,text,sources,w.LIMITS)
    with pytest.raises(ValueError):w.validate(omitted,w.QUOTATION,text,sources)
    # A different in-bounds quote/unit placement is not canonical evidence either.
    moved=copy.deepcopy(good);moved['original']['quoted_phrases'][0]['unit_span']=[0,len(text)]
    component.validate_shape(moved,text,sources,w.LIMITS)
    with pytest.raises(ValueError):w.validate(moved,w.QUOTATION,text,sources)


def test_wrong_raw_identity_even_when_normalized_text_matches_is_refused():
    first='Café: "Experts agree".';second='Cafe\u0301: "Experts agree".'
    row=w.run_component(w.QUOTATION,first)
    with pytest.raises(ValueError):w.validate(row,w.QUOTATION,second,w.identity(w.QUOTATION))


@pytest.mark.parametrize('replay',[False,True])
def test_real_timeout_flood_crash_or_malformed_worker_contained_to_candidate(replay):
    supervisor=w.SUPERVISE
    for program,timeout in [('import time;time.sleep(2)',.1),('import sys;sys.stdout.write("x"*1000001)',1),
                            ('raise RuntimeError("SYNTHETIC_PRIVATE_CANARY")',1),('print("{}")',1)]:
        def faulty(argv,*,input,timeout,output_limit):
            req=json.loads(input)
            selected=req['component']==w.QUOTATION and bool(req['packet']) is replay
            if selected:return supervisor([sys.executable,'-I','-S','-B','-c',program],input=input,timeout=min(timeout,.1),output_limit=output_limit)
            return supervisor(argv,input=input,timeout=timeout,output_limit=output_limit)
        with patch.object(w,'SUPERVISE',side_effect=faulty):result=w.check('Buy now. '+TEXT,[w.QUOTATION,'urgency'],'en')
        assert result['state']=='PARTIAL' and result['checks'][0]['state']=='UNAVAILABLE' and result['checks'][1]['state']=='OBSERVATIONS'
        assert 'SYNTHETIC_PRIVATE_CANARY' not in json.dumps(result)
    assert w.check(TEXT,[w.QUOTATION],'en')['state']=='COMPLETE'


def test_two_children_share_one_wall_budget_and_invalid_deadlines_refuse():
    supervisor=w.SUPERVISE;budgets=[]
    def delayed(argv,*,input,timeout,output_limit):
        req=json.loads(input);budgets.append(timeout)
        if req['packet'] is None:time.sleep(.2)
        else:return supervisor([sys.executable,'-I','-S','-B','-c','import time;time.sleep(2)'],input=input,timeout=timeout,output_limit=output_limit)
        return supervisor(argv,input=input,timeout=timeout,output_limit=output_limit)
    started=time.monotonic()
    with patch.object(w,'SUPERVISE',side_effect=delayed):row=w.run_component(w.QUOTATION,TEXT,deadline=.5)
    assert row['state']=='UNAVAILABLE' and len(budgets)==2 and 0<budgets[1]<budgets[0]-.15
    assert time.monotonic()-started<1.5
    for deadline in [True,0,float('nan'),float('inf')]:assert w.run_component(w.QUOTATION,TEXT,deadline=deadline)['state']=='UNAVAILABLE'


def test_broken_optional_candidate_source_cannot_disable_legacy_worker(tmp_path,monkeypatch):
    names=set(w.identity(w.QUOTATION))|{'tools/choice_framing.py'}
    for name in names:
        target=tmp_path/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,target)
    (tmp_path/'tools/authority_quotation.py').write_text('this is invalid Python !')
    monkeypatch.setattr(w,'ROOT',tmp_path)
    result=w.check('Buy now. '+TEXT,[w.QUOTATION,'urgency','authority'],'en')
    assert result['state']=='PARTIAL' and [r['state'] for r in result['checks']]==['UNAVAILABLE','OBSERVATIONS','OBSERVATIONS']


def test_selected_context_does_not_depend_on_missing_choice_packet_and_private_export_is_explicit(tmp_path):
    os.chmod(tmp_path,0o700);out=tmp_path/'details'
    result=invoke((TEXT+' SYNTHETIC_PRIVATE_CANARY').encode(),'--check',w.QUOTATION,'--check','choice','--details',str(out))
    assert result.returncode==3 and b'1 quoted phrase(s)' in result.stdout and b'Choice: unavailable' in result.stdout
    raw=(out/'framing-evidence.json').read_bytes();assert b'SYNTHETIC_PRIVATE_CANARY' not in raw
    record=json.loads(raw);assert record['format']==w.CONTEXT_PROFILE and record['checks'][0]['original']['quoted_phrases']
    assert out.stat().st_mode&0o777==0o700 and (out/'framing-evidence.json').stat().st_mode&0o777==0o600
    assert not any(value in result.stdout+result.stderr for value in [str(out).encode(),record['raw_subject_sha256'].encode(),b'quote_span',b'SYNTHETIC_PRIVATE_CANARY'])
    again=invoke(b'Experts agree.','--check',w.QUOTATION,'--details',str(out))
    assert again.returncode==2 and (out/'framing-evidence.json').read_bytes()==raw


def test_complete_record_budget_refuses_without_clipping_or_disabling_peer():
    text='Buy now. '+'; '.join('Experts agree' for _ in range(128))+' '+(' [1]'*100)
    result=w.check(text,[w.QUOTATION,'urgency'],'en')
    assert result['checks'][0]['state']=='UNAVAILABLE' and result['checks'][1]['state']=='OBSERVATIONS'


def test_shape_coherent_forged_child_omission_is_unavailable_beside_real_urgency():
    text='Buy now. Experts agree.';good=w.run_component(w.QUOTATION,text)
    forged=copy.deepcopy(good);forged['original']['outside_markerless_phrases']=[]
    forged['original']['outside_supported_quotes_without_marker']=forged['counts']['outside_supported_quotes_without_marker']=0
    forged['original']['state']=forged['state']='NO_SUPPORTED_PATTERN'
    component.validate_shape(forged,text,w.identity(w.QUOTATION),w.LIMITS)
    supervisor=w.SUPERVISE;replays=[]
    def altered(argv,*,input,timeout,output_limit):
        req=json.loads(input)
        if req['component']==w.QUOTATION:
            if req['packet'] is None:return subprocess.CompletedProcess(argv,0,json.dumps(forged).encode(),b'')
            replays.append(True)
        return supervisor(argv,input=input,timeout=timeout,output_limit=output_limit)
    with patch.object(w,'SUPERVISE',side_effect=altered):result=w.check(text,[w.QUOTATION,'urgency'],'en')
    assert replays==[True] and result['state']=='PARTIAL'
    assert [row['state'] for row in result['checks']]==['UNAVAILABLE','OBSERVATIONS']


def test_maximum_raw_unicode_subject_keeps_both_actual_pipe_requests_bounded():
    prefix='"Experts agree"';text=prefix+'😀'*(8000-len(prefix));supervisor=w.SUPERVISE;lengths=[]
    def measured(argv,*,input,timeout,output_limit):
        lengths.append(len(input));return supervisor(argv,input=input,timeout=timeout,output_limit=output_limit)
    with patch.object(w,'SUPERVISE',side_effect=measured):row=w.run_component(w.QUOTATION,text)
    assert row['state']=='NO_SUPPORTED_PATTERN' and row['counts']['quoted_phrase_count']==1
    assert row['raw_subject_characters']==8000 and row['raw_subject_bytes']<=32000
    assert len(lengths)==2 and all(n<=200000 for n in lengths)
