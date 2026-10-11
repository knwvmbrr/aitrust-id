"""Execute reference consent, statement files and real gateway modality refusals."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import runpy
import subprocess

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
BOUNDARY = runpy.run_path(str(ROOT/'scripts/verify-image-provenance-boundary.py'))

@pytest.mark.parametrize('file', ['tests/author-choice.cjs', 'tests/conformance-statement.cjs'])
def test_actual_node_controls(file):
    result = subprocess.run(['node','--test','--test-reporter=tap',file],cwd=ROOT,capture_output=True,timeout=45)
    assert result.returncode == 0, result.stdout.decode()+result.stderr.decode()
    assert b'# fail 0' in result.stdout

@pytest.mark.parametrize('field', list(BOUNDARY['EXPECTED']))
def test_changed_current_or_next_policy_refused(field):
    policy = copy.deepcopy(BOUNDARY['EXPECTED'])
    value = policy[field]
    policy[field] = not value if type(value) is bool else 'unaccepted'
    with pytest.raises(ValueError): BOUNDARY['inspect'](policy)

def test_boundary_sources_and_missing_unknown_duplicate_fields():
    assert BOUNDARY['verify'](ROOT)['pass'] is True
    p=copy.deepcopy(BOUNDARY['EXPECTED']);p['stealth_exception']=True
    with pytest.raises(ValueError): BOUNDARY['inspect'](p)
    p=copy.deepcopy(BOUNDARY['EXPECTED']);del p['next_release_image_provenance_issuance']
    with pytest.raises(ValueError): BOUNDARY['inspect'](p)
    with pytest.raises(ValueError):json.loads('{"scope_id":"X-07","scope_id":"waived"}',object_pairs_hook=BOUNDARY['unique'])
    p=copy.deepcopy(BOUNDARY['EXPECTED']);p['current_image_provenance_issuance']=0
    with pytest.raises(ValueError): BOUNDARY['inspect'](p)

def test_future_issuer_allowlist_requires_explicit_review(tmp_path):
    (tmp_path/'spec').mkdir();(tmp_path/'services/gateway').mkdir(parents=True)
    (tmp_path/'spec/image-provenance-boundary.json').write_text(json.dumps(BOUNDARY['EXPECTED']))
    current=(ROOT/'services/gateway/app.py').read_text()
    (tmp_path/'services/gateway/app.py').write_text(current.replace("frozenset({'PS','PII_REDACTED'})","frozenset({'PS','PII_REDACTED','FA'})"))
    with pytest.raises(ValueError): BOUNDARY['verify'](tmp_path)

@pytest.mark.parametrize('modality',['image','audio','video','document','code'])
def test_actual_gateway_refuses_modality_before_dependencies(monkeypatch,modality):
    monkeypatch.setenv('AITRUST_TOKEN','synthetic-image-boundary-token-32chars')
    spec=importlib.util.spec_from_file_location('boundary_gateway',ROOT/'services/gateway/app.py')
    gateway=importlib.util.module_from_spec(spec);spec.loader.exec_module(gateway)
    calls=[]
    def forbidden(**kwargs):
        calls.append(kwargs)
        raise AssertionError('Unsupported request reached a dependency')
    monkeypatch.setattr(gateway.httpx,'AsyncClient',forbidden)
    with TestClient(gateway.app) as client:
        result=client.post('/v1/evaluate',headers={'authorization':'Bearer '+gateway.TOKEN},json={'text':'Synthetic unsupported subject','modality':modality})
    assert result.status_code == 422
    assert result.json()['detail']=='Unsupported modality; only text is currently evaluated'
    assert calls == []
    assert gateway.LIMIT._value == 4
