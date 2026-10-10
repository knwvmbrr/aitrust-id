"""Actual refusal rules and injected violating implementations must differ."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import pytest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('verdict_refusals',ROOT/'scripts/verify-verdict-boundaries.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def test_current_refusal_contract():
    r=m.verify();assert r['pass'] and r['disabled_codes_withheld']==8 and r['unknown_codes_refused']==6
    assert not r['provenance_capture_implemented'] and not r['independent_release_validated']
@pytest.mark.parametrize('fault',['context_verdict','disabled_verdict','unknown_verdict','production_expansion'])
def test_violating_gateway_fails(monkeypatch,fault):
    real=m.module
    def replacement(path):
        module=real(path)
        if path!='services/gateway/app.py':return module
        calibrate=module.calibrate
        if fault=='production_expansion':module.PRODUCTION_TAGS=frozenset({'PS','PII_REDACTED','FA'})
        else:
            def broken(candidates):
                if fault=='context_verdict' and not candidates:return [{'code':'FA'}],[]
                if fault=='disabled_verdict' and candidates and candidates[0]['code']=='IV':return [{'code':'IV'}],[]
                if fault=='unknown_verdict' and candidates and candidates[0]['code']=='ROGUE_AI':return [],[]
                return calibrate(candidates)
            module.calibrate=broken
        return module
    monkeypatch.setattr(m,'module',replacement)
    with pytest.raises(ValueError):m.verify()
def test_credential_alone_becoming_origin_fails(monkeypatch):
    monkeypatch.setattr(m.bridge,'contribution_for',lambda *a,**k:SimpleNamespace(candidate_tag=m.bridge.Tag.FA,research_eligible=True))
    with pytest.raises(ValueError,match='authorship'):m.verify()
