"""Timing admission and privacy checks; authored controls do not establish tag accuracy."""
import hashlib
import importlib.util
import io
import json
import math
import os
from pathlib import Path
import copy
import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('pipeline_performance',ROOT/'scripts/measure-pipeline-performance.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


def private_token(tmp_path):
    directory=tmp_path.resolve()/'private';directory.mkdir(mode=0o700)
    path=directory/'runtime.env';path.write_text('AITRUST_TOKEN='+'synthetic_private_key_123456789'+'\n');path.chmod(0o600)
    return path


@pytest.mark.parametrize('form',module.FORMS)
@pytest.mark.parametrize('size',module.LENGTHS)
def test_synthetic_profiles_have_exact_supported_lengths(form,size):
    value=module.sample(form,size)
    assert len(value)==len(value.encode())==size and 'synthetic' in value.lower()
    assert ('curl' in value)==(form!='ordinary')
    assert ('@example.invalid' in value)==(form=='redaction_command')


def test_nearest_rank_quantiles_keep_sample_count_and_tail():
    result=module.summary(list(range(1,21)))
    assert (result['p50_ms'],result['p95_ms'],result['max_ms'],result['sample_count'])==(10,19,20,20)


@pytest.mark.parametrize('values',[[],[1]*19,[1]*21,[True]*20,[float('nan')]*20,[float('inf')]*20,[-1]*20])
def test_invalid_or_nonfinite_timings_never_produce_success(values):
    with pytest.raises(module.MeasurementError):module.summary(values)


def test_token_file_permissions_duplicate_and_symlink_are_checked(tmp_path):
    path=private_token(tmp_path);token=module.staging_token(path);assert token=='synthetic_private_key_123456789'
    path.chmod(0o644)
    with pytest.raises(module.MeasurementError):module.staging_token(path)
    path.chmod(0o600);path.write_text('AITRUST_TOKEN='+token+'\nAITRUST_TOKEN='+token+'\n')
    with pytest.raises(module.MeasurementError):module.staging_token(path)
    path.write_text('AITRUST_TOKEN='+token+'\n');link=path.parent/'link';link.symlink_to(path)
    with pytest.raises(module.MeasurementError):module.staging_token(link)
    path.parent.chmod(0o755)
    with pytest.raises(module.MeasurementError):module.staging_token(path)


class Response(io.BytesIO):
    status=200
    headers={'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}


class SyntheticOpener:
    def __init__(self,corrupt=None):self.requests=[];self.corrupt=corrupt
    def open(self,req,timeout):
        self.requests.append(req);assert timeout==20 and req.full_url.startswith('http://127.0.0.1:8787/')
        if req.data is None:return Response(b'{"ok":true,"spec_version":"0.1.0"}')
        payload=json.loads(req.data);text=payload['text'];tags=[]
        if 'curl' in text:
            tags.append({'code':'PS','state':'asserted','confidence':.97,'floor':.7,'signals':[{'id':'sig.piped_installer.v3','score':.97,'spans':[[0,10]]}]})
        if '@example.invalid' in text:
            tags.append({'code':'PII_REDACTED','state':'asserted','confidence':1,'floor':1,'signals':[{'id':'presidio.entity.v1','score':1,'spans':[[0,10]]}]})
        from protocol.replay_identity import pipeline_identity,redactor_identity
        hashes={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in module.INPUT_SOURCES}
        redactor=redactor_identity({'python':'3.12.14','platform_machine':'arm64',
            'dependency_records':{'synthetic-package':'a'*64},'dependencies':{'synthetic-package':'1.0.0'},
            'model_manifest_sha256':'b'*64,'sources':{k:hashes[p] for k,p in module.REDACTOR_SOURCE_KEYS.items()},
            'recognizer_configuration_sha256':'c'*64,'recognizer_count':1})
        identity=pipeline_identity({'gateway_source_sha256':hashes['services/gateway/app.py'],
            'normalization_source_sha256':hashes['protocol/normalization.py'],
            'normalization_data_sha256':hashes['protocol/unicode15-data.json'],'rule_floor':.7,'redactor':redactor})
        record={'assertion_id':'eadf909b-7723-4431-b200-1a4cb56c538b','spec_version':'0.1.0',
            'subject':{'sha256':hashlib.sha256(text.encode()).hexdigest(),'char_len':len(text),'origin_host':'unknown','captured_at':'2026-10-11T00:00:00Z','modality':'text'},
            'tags':tags,'abstentions':[],'evaluator':{'models':[{'name':'rules-only','sha256':hashes['services/evaluator/app.py']},
                {'name':'presidio-redaction','sha256':redactor['sha256'],'revision':redactor['version']},
                {'name':'gateway-pipeline','sha256':identity['sha256'],'revision':identity['version']}],
                'preprocessing':identity,'calibration_id':'synthetic','latency_ms':1}}
        if self.corrupt:self.corrupt(record)
        return Response(json.dumps(record).encode())


def test_actual_client_protocol_measures_all_profiles_without_private_reports(tmp_path,monkeypatch):
    path=private_token(tmp_path);opener=SyntheticOpener();monkeypatch.setattr(module.os,'geteuid',lambda:1000)
    report=module.measure(path,'aitrust-staging',opener)
    assert report['pass'] and report['profile_count']==12
    assert len(opener.requests)==253
    assert all(x['warm_round_trip']['sample_count']==20 for x in report['rows'])
    raw=json.dumps(report)
    for secret in ('synthetic_private_key_123456789','http://127.0.0.1',str(path),'synthetic-observer@example.invalid','assertion_id'):
        assert secret not in raw
    assert report['accepted_latency_budget_ms'] is None and report['first_observed_is_not_service_cold_start']
    assert report['runtime_identity_verified_on_each_response']
    assert report['runtime_identity']['configuration']['redactor']['configuration']['sources']['app']==hashlib.sha256((ROOT/'services/anonymizer/app.py').read_bytes()).hexdigest()


def test_generated_local_setup_is_measured_without_changing_source_checks(tmp_path,monkeypatch):
    monkeypatch.setattr(module.os,'geteuid',lambda:1000)
    opener=SyntheticOpener()
    result=module.measure(private_token(tmp_path),'aitrust-local-'+'a'*32,opener)
    assert result['pass'] and len(opener.requests)==253
    assert result['runtime_identity_verified_on_each_response']


@pytest.mark.parametrize('project',['aitrust-local-', 'aitrust-local-'+'A'*32,
    'aitrust-local-'+'a'*31,'aitrust-local-'+'a'*33,'aitrust-local-'+'g'*32,
    'aitrust-staging-extra'])
def test_unselected_local_project_refuses_before_http(tmp_path,monkeypatch,project):
    monkeypatch.setattr(module.os,'geteuid',lambda:1000)
    opener=SyntheticOpener()
    with pytest.raises(module.MeasurementError):
        module.measure(private_token(tmp_path),project,opener)
    assert not opener.requests


def test_cli_passes_generated_local_project_to_the_same_admission_contract(tmp_path,monkeypatch):
    project='aitrust-local-'+'a'*32
    seen=[]
    monkeypatch.setattr(module.sys,'argv',['measure','--env-file',str(tmp_path/'private.env'),
        '--project',project,'--output',str(tmp_path/'result.json')])
    def selected(env_file,selected_project):
        seen.append((env_file,selected_project))
        return {'pass':True,'profile_count':12}
    monkeypatch.setattr(module,'measure',selected)
    monkeypatch.setattr(module,'write_report',lambda *_:None)
    assert module.main()==0
    assert seen==[(tmp_path/'private.env',project)]


@pytest.mark.parametrize('corrupt',[
    lambda r:r['evaluator']['models'][0].__setitem__('sha256','b'*64),
    lambda r:r['subject'].__setitem__('sha256','b'*64),
    lambda r:r['evaluator'].__setitem__('latency_ms',float('nan')),
    lambda r:r.__setitem__('private','synthetic_private_key_123456789'),
    lambda r:r['tags'].append({'code':'HP'}),
])
def test_corrupt_upstream_fails_without_reflecting_credential_or_exception(tmp_path,monkeypatch,corrupt):
    path=private_token(tmp_path);monkeypatch.setattr(module.os,'geteuid',lambda:1000)
    report=module.measure(path,'aitrust-staging',SyntheticOpener(corrupt))
    assert report['pass'] is False and report['failed_profile']['stage']=='profile'
    assert report['completed_profiles']==[]
    assert 'synthetic_private_key_123456789' not in json.dumps(report)


def test_redirect_handler_refuses_forwarding_auth_to_another_host():
    with pytest.raises(module.MeasurementError):module.NoRedirect().redirect_request(None,None,302,'redirect',{},'https://example.invalid/')


def test_wrong_project_and_root_refuse_before_any_request(tmp_path,monkeypatch):
    path=private_token(tmp_path);opener=SyntheticOpener()
    with pytest.raises(module.MeasurementError):module.measure(path,'production',opener)
    monkeypatch.setattr(module.os,'geteuid',lambda:0)
    with pytest.raises(module.MeasurementError):module.measure(path,'aitrust-staging',opener)
    assert not opener.requests


def test_configured_url_redaction_can_coexist_with_command_observation(tmp_path,monkeypatch):
    path=private_token(tmp_path);monkeypatch.setattr(module.os,'geteuid',lambda:1000)
    def redacted_url(record):
        if {t['code'] for t in record['tags']}=={'PS'}:
            record['tags'].append({'code':'PII_REDACTED','state':'asserted','confidence':1,'floor':1,'signals':[{'id':'presidio.entity.v1','score':1,'spans':[[0,10]]}]})
            record['subject']['sha256']='b'*64
    report=module.measure(path,'aitrust-staging',SyntheticOpener(redacted_url))
    assert report['pass'] and report['command_profile_allows_configured_url_redaction']
    assert all('warm_evaluator' not in row and 'warm_reported_pipeline' in row for row in report['rows'])


@pytest.mark.parametrize('field',['gateway_source_sha256','normalization_source_sha256','normalization_data_sha256'])
def test_rehashed_stale_pipeline_sources_refused(tmp_path,monkeypatch,field):
    from protocol.replay_identity import pipeline_identity
    def stale(record):
        config=record['evaluator']['preprocessing']['configuration'];config[field]='a'*64
        record['evaluator']['preprocessing']=pipeline_identity(config)
    monkeypatch.setattr(module.os,'geteuid',lambda:1000)
    result=module.measure(private_token(tmp_path),'aitrust-staging',SyntheticOpener(stale))
    assert result['pass'] is False and result['failure_code']=='pipeline_source_changed'


@pytest.mark.parametrize('field',list(module.REDACTOR_SOURCE_KEYS))
def test_rehashed_stale_redactor_sources_refused(tmp_path,monkeypatch,field):
    from protocol.replay_identity import pipeline_identity,redactor_identity
    def stale(record):
        config=record['evaluator']['preprocessing']['configuration'];red=config['redactor']['configuration'];red['sources'][field]='a'*64
        config['redactor']=redactor_identity(red);record['evaluator']['preprocessing']=pipeline_identity(config)
    monkeypatch.setattr(module.os,'geteuid',lambda:1000)
    result=module.measure(private_token(tmp_path),'aitrust-staging',SyntheticOpener(stale))
    assert result['pass'] is False and result['failure_code']=='pipeline_source_changed'


@pytest.mark.parametrize('change',[
    lambda r:r['evaluator'].pop('preprocessing'),
    lambda r:r['evaluator']['preprocessing'].__setitem__('sha256','a'*64),
    lambda r:r['evaluator']['preprocessing']['configuration']['redactor'].__setitem__('sha256','a'*64),
])
def test_missing_or_corrupt_identity_refused(tmp_path,monkeypatch,change):
    monkeypatch.setattr(module.os,'geteuid',lambda:1000)
    result=module.measure(private_token(tmp_path),'aitrust-staging',SyntheticOpener(change))
    assert result['pass'] is False and result['failure_code']=='pipeline_identity_invalid'


@pytest.mark.parametrize('change',[
    lambda r:r['evaluator']['models'].pop(),
    lambda r:r['evaluator']['models'][1].__setitem__('sha256','a'*64),
    lambda r:r['evaluator']['models'][2].__setitem__('revision','different'),
    lambda r:r['evaluator']['models'][2].__setitem__('name','presidio-redaction'),
])
def test_model_list_must_match_validated_identities(tmp_path,monkeypatch,change):
    monkeypatch.setattr(module.os,'geteuid',lambda:1000)
    result=module.measure(private_token(tmp_path),'aitrust-staging',SyntheticOpener(change))
    assert result['pass'] is False and result['failure_code']=='pipeline_models_invalid'


def test_each_response_must_keep_same_redactor_configuration(tmp_path,monkeypatch):
    from protocol.replay_identity import pipeline_identity,redactor_identity
    calls=0
    def drift(record):
        nonlocal calls
        calls+=1
        if calls==1:return
        config=record['evaluator']['preprocessing']['configuration'];red=config['redactor']['configuration'];red['recognizer_count']=2
        config['redactor']=redactor_identity(red);identity=pipeline_identity(config);record['evaluator']['preprocessing']=identity
        record['evaluator']['models'][1].update(sha256=config['redactor']['sha256']);record['evaluator']['models'][2].update(sha256=identity['sha256'])
    monkeypatch.setattr(module.os,'geteuid',lambda:1000)
    result=module.measure(private_token(tmp_path),'aitrust-staging',SyntheticOpener(drift))
    assert result['pass'] is False and result['failure_code']=='pipeline_identity_changed'
