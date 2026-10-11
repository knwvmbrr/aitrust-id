import copy
import hashlib
import importlib.util
from pathlib import Path
import sys
from unittest.mock import Mock

import pytest
from research.nli.backend import expected_identity
from research.nli.pairs import PairError, analyze

ROOT=Path(__file__).resolve().parents[1]
def module(name):
 spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/(name.replace('_','-')+'.py'))
 value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value
cli=module('check_nli_pairs');assets=module('fetch_nli_assets')
REQUEST={'schema_version':1,'language':'en','text':'The door is closed. The door is open.','pairs':[{'id':'one','first':[0,19],'second':[20,37]}]}
def observation():return analyze(REQUEST,lambda a,b:([1.,2.,3.],12),expected_identity())

def test_valid_observation_handoff():cli.validate_observation(REQUEST,observation())

@pytest.mark.parametrize('kind',['profile','subject','span','direction','score','label','calibration','truth','intent','tag','release','extra','identity','missing','more','fewer','bool-logit','infinite','token-limit','numeric-false'])
def test_corrupted_worker_response_refuses(kind):
 r=observation();row=r['pairs'][0]
 if kind=='profile':r['profile']='other'
 if kind=='subject':r['subject_sha256']='0'*64
 if kind=='span':row['first_span']=[1,19]
 if kind=='direction':row['pair_direction']='reverse'
 if kind=='score':row['normalized_model_scores']['neutral']=1.
 if kind=='label':row['top_model_labels']=['contradiction']
 if kind=='calibration':row['calibrated_probability']=True
 if kind=='truth':r['truth_established']=True
 if kind=='intent':r['intent_established']=True
 if kind=='tag':r['tag_asserted']=True
 if kind=='release':r['release_approved']=True
 if kind=='extra':r['extra']='claim'
 if kind=='identity':r['model_identity']['revision']='0'*40
 if kind=='missing':del row['logits']
 if kind=='more':r['pairs']*=2
 if kind=='fewer':r['pairs']=[]
 if kind=='bool-logit':row['logits'][0]=True
 if kind=='infinite':row['logits'][0]=float('inf')
 if kind=='token-limit':row['token_count']=513
 if kind=='numeric-false':r['tag_asserted']=0
 with pytest.raises((ValueError,KeyError)):cli.validate_observation(REQUEST,r)

@pytest.mark.parametrize('actual,status',[ (b'abc',200),(b'abcd',200),(b'ab',200),(b'xbc',200),(b'abc',500)])
def test_download_exact_length_hash_and_http_status(actual,status):
 response=Mock();response.status=status
 chunks=iter([actual,b'']);response.read.side_effect=lambda n:next(chunks)
 manager=Mock();manager.__enter__=lambda x:response;manager.__exit__=lambda *x:None
 row={'url':'https://example.test/public-model','bytes':3,'sha256':hashlib.sha256(b'abc').hexdigest()}
 if actual==b'abc' and status==200:assert assets.fetch(row,lambda *a,**k:manager)==b'abc'
 else:
  with pytest.raises(ValueError):assets.fetch(row,lambda *a,**k:manager)


def test_missing_model_refuses_before_library_import(tmp_path):
 from research.nli.backend import Backend
 def fail(path,limit):raise ValueError('Missing verified model')
 with pytest.raises(ValueError):Backend(tmp_path,fail)


def test_tampered_asset_refuses_before_library_import(tmp_path):
 from research.nli.backend import Backend
 with pytest.raises(PairError):Backend(tmp_path,lambda path,limit:b'corrupt')


def test_optional_profile_is_bound_without_downloading():
 profile=module('verify_nli_profile');assert profile.verify()['pass'] is True

@pytest.mark.parametrize('member',['assets.json','requirements-mac.lock','requirements-linux.lock','notices.json','wheel-provenance-mac.json'])
def test_optional_profile_drift_refuses(tmp_path,member):
 import shutil
 profile=module('verify_nli_profile');shutil.copytree(ROOT/'research/nli',tmp_path/'research/nli',ignore=shutil.ignore_patterns('__pycache__'))
 path=tmp_path/'research/nli'/member
 if path.suffix=='.lock':path.write_text(path.read_text().replace('--hash=sha256:','--hash=sha256:0',1))
 else:
  value=__import__('json').loads(path.read_text())
  if member=='assets.json':value['files'][0]['sha256']='0'*64
  if member=='notices.json':value['permission_cleared']=True
  if member=='wheel-provenance-mac.json':value[0]['version']='0.0.0'
  path.write_text(__import__('json').dumps(value))
 with pytest.raises(ValueError):profile.verify(tmp_path)
