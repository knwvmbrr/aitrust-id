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
        record={'assertion_id':'eadf909b-7723-4431-b200-1a4cb56c538b','spec_version':'0.1.0',
            'subject':{'sha256':hashlib.sha256(text.encode()).hexdigest(),'char_len':len(text),'origin_host':'unknown','captured_at':'2026-10-11T00:00:00Z','modality':'text'},
            'tags':tags,'abstentions':[],'evaluator':{'models':[{'name':'rules-only','sha256':hashlib.sha256((ROOT/'services/evaluator/app.py').read_bytes()).hexdigest()}],'calibration_id':'synthetic','latency_ms':1}}
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
