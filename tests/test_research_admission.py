"""Selected synthetic request boundary; actual database behavior runs on Linux."""
import base64
import copy
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path
import subprocess
import sys

import pytest
from tools.research_admission import AdmissionError, CHOICES, FIXED, PROFILE, digest_token, parse, statement

ROOT=Path(__file__).resolve().parents[1]


def token(number):return base64.urlsafe_b64encode(number.to_bytes(32,'big')).decode().rstrip('=')


def request():
    return {'format':PROFILE,'synthetic':True,'operation':'submit',
        'invitation_token':token(1),'withdrawal_token':token(2),
        'feedback':{**FIXED,**{k:v[0] for k,v in CHOICES.items()}}}


def encoded(value):return json.dumps(value).encode()


def cli():
    spec=importlib.util.spec_from_file_location('admission_cli',ROOT/'scripts/research-admission.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


@pytest.mark.parametrize('values',list(itertools.product(*CHOICES.values())))
def test_every_fixed_answer_combination_is_accepted_without_content(values):
    value=request();value['feedback'].update(dict(zip(CHOICES,values)))
    translated=parse(encoded(value))
    assert translated['envelope']['feedback']==value['feedback']
    query=statement(encoded(value))
    assert value['invitation_token'] not in query and value['withdrawal_token'] not in query
    assert digest_token(value['invitation_token']) in query


@pytest.mark.parametrize('field',['prompt','example','text','email','ip','timestamp','subject_hash','role','endpoint'])
def test_extra_top_level_and_nested_fields_are_refused(field):
    for nested in [False,True]:
        value=request();(value['feedback'] if nested else value)[field]='PRIVATE_ADMISSION_CANARY'
        with pytest.raises(AdmissionError,match='^Synthetic admission refused$'):statement(encoded(value))


@pytest.mark.parametrize('field,value',[('schema_version',True),('schema_version',1.0),('tag','MT'),
    ('method_version','context-v7'),('sharing','automatic_upload'),('feedback','free text'),
    ('reported_result','validated'),('failure_category',None),('purpose','train_everything')])
def test_private_feedback_schema_is_closed(field,value):
    original=request();original['feedback'][field]=value
    with pytest.raises(AdmissionError):parse(encoded(original))


@pytest.mark.parametrize('raw',[b'',b'{',b'null',b'[]',b'\xff',b'{"format":1,"format":2}',
    b'{"x":NaN}',b' '*4097,b'['*1200+b']'*1200])
def test_malformed_duplicate_nonfinite_and_oversized_requests_refuse(raw):
    with pytest.raises(AdmissionError):parse(raw)


@pytest.mark.parametrize('value',[None,True,1,'','a'*42,'a'*44,'='*43,'/'*43,'+'*43,'A'*42+'B'])
def test_tokens_require_exact_canonical_32_byte_representation(value):
    with pytest.raises(AdmissionError):digest_token(value)


def test_digest_matches_the_raw_token_bytes_and_plaintext_is_not_retained():
    value=request();translated=parse(encoded(value))
    assert translated['withdrawal_digest']==hashlib.sha256((2).to_bytes(32,'big')).hexdigest()
    assert not any('token' in k for k in translated)
    value['withdrawal_token']=value['invitation_token']
    with pytest.raises(AdmissionError):parse(encoded(value))


def test_withdrawal_has_only_its_capability_and_no_metadata():
    value={'format':PROFILE,'synthetic':True,'operation':'withdraw','withdrawal_token':token(3)}
    translated=parse(encoded(value));assert set(translated)=={'operation','withdrawal_digest'}
    assert 'record_invited' not in statement(encoded(value))
    value['feedback']=request()['feedback']
    with pytest.raises(AdmissionError):parse(encoded(value))


@pytest.mark.parametrize('field,value',[('synthetic',False),('synthetic',1),('operation','issue'),
    ('format','metadata-admission-live/v1'),('invitation_token',token(2))])
def test_live_and_unsupported_operations_are_refused(field,value):
    original=request();original[field]=value
    with pytest.raises(AdmissionError):parse(encoded(original))


@pytest.mark.parametrize('path',['/','/tmp','/var/lib/postgresql/18/main','relative'])
def test_outside_sandbox_refuses_before_process(path,monkeypatch):
    m=cli();monkeypatch.setattr(m.sys,'platform','linux');monkeypatch.setattr(m.os,'geteuid',lambda:501)
    monkeypatch.setattr(m.subprocess,'run',lambda *a,**k:pytest.fail('No process before directory admission'))
    with pytest.raises((AdmissionError,ValueError,OSError)):m.execute(path,encoded(request()))


def test_root_and_nonlinux_refuse_before_process(monkeypatch):
    m=cli();monkeypatch.setattr(m.subprocess,'run',lambda *a,**k:pytest.fail('No process before platform admission'))
    monkeypatch.setattr(m.sys,'platform','darwin')
    with pytest.raises(AdmissionError):m.execute('/tmp/unused',encoded(request()))
    monkeypatch.setattr(m.sys,'platform','linux');monkeypatch.setattr(m.os,'geteuid',lambda:0)
    with pytest.raises(AdmissionError):m.execute('/tmp/unused',encoded(request()))


def test_cli_fixed_diagnostics_do_not_reflect_private_argument():
    result=subprocess.run([sys.executable,str(ROOT/'scripts/research-admission.py'),
        '--unknown-private-option','PRIVATE_ADMISSION_CANARY'],capture_output=True,timeout=8)
    assert result.returncode==2 and b'PRIVATE_ADMISSION_CANARY' not in result.stdout+result.stderr
    assert b'Traceback' not in result.stdout+result.stderr


def test_actual_verifier_command_refuses_unowned_fixture_without_traceback():
    result=subprocess.run([sys.executable,str(ROOT/'scripts/verify-research-admission.py'),
        '--sandbox-dir','/tmp/aitrust-admission-unavailable-fixture'],capture_output=True,timeout=8)
    assert result.returncode==1
    assert json.loads(result.stdout)=={'pass':False,'completed_cases':[]}
    assert result.stderr==b'Synthetic admission controls failed; no production acceptance.\n'


@pytest.mark.parametrize('identity',[None,True,1,[],{},'not-a-uuid'])
def test_invalid_database_identity_is_a_bounded_contract_refusal(tmp_path,monkeypatch,identity):
    m=cli();monkeypatch.setattr(m.sys,'platform','linux');monkeypatch.setattr(m.os,'geteuid',lambda:501)
    monkeypatch.setattr(m.base,'sandbox',lambda _:tmp_path)
    monkeypatch.setattr(m.pwd,'getpwuid',lambda _:type('User',(),{'pw_name':'synthetic'})())
    responses=iter([{'data':str(tmp_path/'data'),'socket':str(tmp_path/'socket'),
        'cluster':'aitrust-metadata-synthetic','listen':'','version':'180000','tcp':None},
        {'operation':'submit','feedback_id':identity}])
    monkeypatch.setattr(m.subprocess,'run',lambda *a,**k:subprocess.CompletedProcess(a,0,json.dumps(next(responses)).encode(),b''))
    with pytest.raises(AdmissionError):m.execute(tmp_path,encoded(request()))


def test_python_choices_match_the_actual_website_export_choices():
    result=subprocess.run(['node','--input-type=module','-e',
        "import {choices,feedbackRecord} from './site/src/research-feedback.js'; console.log(JSON.stringify({choices,record:feedbackRecord(Object.fromEntries(Object.entries(choices).map(([k,v])=>[k,v[0]])))}));"],
        cwd=ROOT,capture_output=True,text=True,timeout=10,check=True)
    value=json.loads(result.stdout)
    assert value['choices']=={k:list(v) for k,v in CHOICES.items()}
    assert value['record']==request()['feedback']


@pytest.mark.parametrize('field,value',[('listen','*'),('tcp','127.0.0.1'),('cluster','production'),
    ('version','170000'),('data','/var/lib/postgresql/18/main'),('socket','/tmp/elsewhere')])
def test_actual_cluster_identity_mismatch_refuses_before_mutation(tmp_path,monkeypatch,field,value):
    m=cli();monkeypatch.setattr(m.sys,'platform','linux');monkeypatch.setattr(m.os,'geteuid',lambda:501)
    monkeypatch.setattr(m.base,'sandbox',lambda _:tmp_path);monkeypatch.setattr(m.pwd,'getpwuid',lambda _:type('User',(),{'pw_name':'synthetic'})())
    observed={'data':str(tmp_path/'data'),'socket':str(tmp_path/'socket'),'cluster':'aitrust-metadata-synthetic','listen':'','version':'180000','tcp':None};observed[field]=value;calls=[]
    def process(*args,**kwargs):
        calls.append(kwargs['input']);return subprocess.CompletedProcess(args,0,json.dumps(observed).encode(),b'')
    monkeypatch.setattr(m.subprocess,'run',process)
    with pytest.raises(AdmissionError):m.execute(tmp_path,encoded(request()))
    assert len(calls)==1 and b'record_invited' not in calls[0]
