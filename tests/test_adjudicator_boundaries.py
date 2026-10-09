"""Independent boundary probes of the research components, not media validation."""
import importlib.util
import itertools
import sys
from pathlib import Path
import pytest
ROOT = Path(__file__).resolve().parents[1]
def load(path):
    name = 'audit_' + path.replace('/', '_').replace('.', '_')
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    mod = importlib.util.module_from_spec(spec); sys.modules[name] = mod
    spec.loader.exec_module(mod); return mod
V = load('services/adjudicator/verdict.py')
A = load('services/adjudicator/adjudicate.py')
M = load('eval/measure.py')
GOOD = ['claimSignature.validated', 'signingCredential.trusted', 'assertion.dataHash.match', 'signingCredential.ocsp.notRevoked']
@pytest.mark.parametrize('codes', [[], ['signingCredential.ocsp.notRevoked'], GOOD[1:], GOOD[:1]+GOOD[2:], GOOD[:2]+GOOD[3:]])
def test_missing_required_verification_never_passes(codes):
    assert not V.from_status_codes(codes, ocsp_checked=True).is_asserted

def test_unknown_code_cannot_be_laundered_by_a_clean_revocation():
    assert not V.from_status_codes(GOOD + ['new.failure'], strict=False).is_asserted

def test_attempted_revocation_is_not_a_clean_result():
    v = V.from_status_codes(GOOD[:-1], ocsp_checked=True)
    assert v.revocation is V.Revocation.UNKNOWN_INACCESSIBLE
    assert not v.is_asserted

@pytest.mark.parametrize('codes', list(itertools.permutations(['signingCredential.ocsp.notRevoked','signingCredential.ocsp.skipped','signingCredential.ocsp.inaccessible'])))
def test_revocation_order_does_not_choose_an_optimistic_answer(codes):
    v = V.from_status_codes(GOOD[:3] + list(codes))
    assert v.revocation is V.Revocation.UNKNOWN_INACCESSIBLE and not v.is_asserted

@pytest.mark.parametrize('integrity,revocation', [(V.Integrity.VALID,V.Revocation.REVOKED),(V.Integrity.VALID,V.Revocation.NOT_APPLICABLE),(V.Integrity.REVOKED,V.Revocation.NOT_REVOKED)])
def test_direct_constructor_cannot_bypass_pair_guard(integrity,revocation):
    with pytest.raises(ValueError): V.Verdict(integrity,revocation,codes=tuple(GOOD))

# `verified` is now required for MANIFEST/WATERMARK, so the unverified cases
# state it explicitly. The intent of the test is unchanged: none of these
# three carries standing alone.
@pytest.mark.parametrize('signal', [A.Signal(A.Layer.MANIFEST,'origin','human','m',verified=False), A.Signal(A.Layer.MANIFEST,'origin','human','m',verified=True), A.Signal(A.Layer.WATERMARK,'origin','ai','w',verified=False)])
def test_unverified_source_is_not_an_assertion(signal):
    assert not A.adjudicate([signal],claim='origin').is_asserted

@pytest.mark.parametrize('k,n', [(True,2),(1.5,3),(1,3.5)])
def test_fractional_or_boolean_counts_rejected(k,n):
    with pytest.raises(ValueError): M.wilson(k,n)

def test_extreme_confidence_uses_stable_quantiles():
    i=M.wilson(1,2,1-1e-12)
    assert 0 <= i.low < i.point < i.high <= 1

def test_missing_answers_are_published_alongside_conditional_accuracy():
    d=M.summarize([M.FixtureResult('a',{'v':'valid'},'valid'),M.FixtureResult('b',{'v':None},'valid')])
    assert d['answer_coverage']['v']=={'attempted':2,'answered':1,'missing':1}
    assert d['per_validator_accuracy']['v']['trials']==1

def test_study_width_is_twenty_points_total_not_twenty_each_side():
    n=M.min_trials_for_width(.20)
    assert n==93
    assert M.wilson(n//2,n).width<=.20

@pytest.mark.parametrize('bad', [1,'yes'])
def test_survival_cannot_count_arbitrary_truthy_inputs(bad):
    with pytest.raises(ValueError): M.SurvivalTrial('p','f',bad)


def test_clean_manifest_cannot_hide_uninterpreted_verification_in_another():
    good=V.from_status_codes(GOOD)
    unknown=V.from_status_codes(GOOD+["future.failure"],strict=False)
    result=V.worst([good,unknown])
    assert result.state=="unverified" and not result.is_asserted
