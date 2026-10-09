"""Provenance must not invent authorship, merge subjects or hide disagreement."""
from dataclasses import replace
import itertools
import json
import pytest
from services.adjudicator import tag_bridge as B
from services.adjudicator import verdict as V

SUBJECT='a'*64
COMPLETE=['claimSignature.validated','signingCredential.trusted','assertion.dataHash.match','signingCredential.ocsp.notRevoked']

def valid(): return V.from_status_codes(COMPLETE)
def evidence(claim=B.Claim.AI_HUMAN_REWORK,source='fixture:one',subject=SUBJECT,bound=True):
    return B.ClaimEvidence(claim,subject,source,bound)
def contribution(claim=B.Claim.AI_HUMAN_REWORK,source='fixture:one',verdict=None):
    return B.contribution_for(verdict or valid(),evidence=evidence(claim,source),subject_sha256=SUBJECT)

def test_valid_credential_alone_is_not_ai_participation():
    row=B.contribution_for(valid())
    assert row.candidate_tag is B.Tag.UNK and not row.research_eligible
    assert 'alone' in row.basis
    assert not hasattr(row,'actionable'), 'Research candidates must not reuse the old live-action flag'
    assert not row.to_dict()['production_assertion']

@pytest.mark.parametrize('claim,tag',[(B.Claim.AI_HUMAN_REWORK,B.Tag.PA),(B.Claim.AI_NO_HUMAN,B.Tag.FA)])
def test_only_explicit_verified_subject_bound_claim_supports_research_candidate(claim,tag):
    row=contribution(claim)
    assert row.candidate_tag is tag and row.research_eligible
    output=row.to_dict()
    assert output['claim']==claim.value and output['subject_sha256']==SUBJECT
    assert output['research_eligible'] and not output['production_assertion']
    assert not output['independent_release_validated']

@pytest.mark.parametrize('codes,kwargs',[
    ([],{'manifest_present':False}),([],{}),
    (['claimSignature.validated'],{}),
    (COMPLETE[:-1],{}),
    (['assertion.dataHash.mismatch'],{}),
    (['signingCredential.ocsp.revoked'],{}),
    (['signingCredential.expired'],{}),
    (['signingCredential.untrusted'],{}),
    (['claim.multiple'],{}),
    (COMPLETE,{'ocsp_checked':False}),
    (COMPLETE+['future.unknown'],{'strict':False}),
])
@pytest.mark.parametrize('claim',list(B.Claim))
def test_credential_failure_or_unknown_cannot_establish_authorship(codes,kwargs,claim):
    row=contribution(claim,verdict=V.from_status_codes(codes,**kwargs))
    assert row.candidate_tag is B.Tag.UNK and not row.research_eligible
    assert not row.credential_supported
    assert not row.to_dict()['production_assertion']

def test_human_claim_is_not_positive_ai_or_human_authenticity_clearance():
    row=contribution(B.Claim.HUMAN)
    assert row.candidate_tag is B.Tag.UNK and not row.research_eligible
    assert 'not a human-authenticity clearance' in row.basis

def test_unbound_claim_cannot_be_promoted():
    row=B.contribution_for(valid(),evidence=evidence(bound=False),subject_sha256=SUBJECT)
    assert not row.research_eligible and not row.credential_supported

@pytest.mark.parametrize('value',[None,'', 'A'*64,'g'*64,'a'*63,123,True])
def test_invalid_hash_is_rejected(value):
    with pytest.raises(ValueError):evidence(subject=value)

@pytest.mark.parametrize('value',['', 'raw answer with spaces', 'person@example.invalid', 'x'*161,123])
def test_evidence_reference_is_bounded_and_not_raw_content(value):
    with pytest.raises(ValueError):evidence(source=value)

@pytest.mark.parametrize('value',['ai','human',None,{},1])
def test_generic_or_unrecognized_authorship_claim_is_not_guessed(value):
    with pytest.raises(ValueError):evidence(claim=value)

@pytest.mark.parametrize('value',[None,'true',1,{}])
def test_verification_flag_is_not_coerced(value):
    with pytest.raises(ValueError):evidence(bound=value)

def test_subject_binding_is_explicit():
    with pytest.raises(ValueError):B.contribution_for(valid(),evidence=evidence())
    with pytest.raises(ValueError):B.contribution_for(valid(),evidence=evidence(),subject_sha256='b'*64)
    with pytest.raises(ValueError):B.contribution_for({'state':'valid','is_asserted':True})
    with pytest.raises(ValueError):B.contribution_for(valid(),evidence={'claim':'ai'},subject_sha256=SUBJECT)

@pytest.mark.parametrize('change',[
    {'candidate_tag':'PA'}, {'direction':'raise'}, {'research_eligible':1},
    {'credential_supported':1}, {'subject_sha256':'b'*64},
    {'verdict_state':'future'}, {'evidence':None},
    {'credential_supported':False}, {'basis':''}, {'basis':'x'*501},
    {'direction':B.Direction.NEUTRAL}, {'candidate_tag':B.Tag.FA},
    {'research_eligible':False,'candidate_tag':B.Tag.UNK,'direction':B.Direction.NEUTRAL},
])
def test_direct_construction_cannot_bypass_research_contract(change):
    with pytest.raises(ValueError):replace(contribution(),**change)

@pytest.mark.parametrize('left,right',[
    (B.Claim.AI_HUMAN_REWORK,B.Claim.AI_NO_HUMAN),
    (B.Claim.AI_HUMAN_REWORK,B.Claim.HUMAN),
    (B.Claim.AI_NO_HUMAN,B.Claim.HUMAN),
])
def test_equal_verified_claim_disagreement_never_selects_first_tag(left,right):
    rows=[contribution(left,'fixture:left'),contribution(right,'fixture:right')]
    for ordered in (rows,rows[::-1]):
        result=B.summarize(ordered)
        assert result['state']=='CONFLICTED' and result['candidate_tag']=='UNK'
        assert not result['research_eligible']
        assert {r['source_id'] for r in result['inputs']}=={'fixture:left','fixture:right'}

def test_conflicted_credential_is_not_hidden_by_another_positive():
    bad=contribution(source='fixture:conflict',verdict=V.from_status_codes(['claim.multiple']))
    result=B.summarize([contribution(),bad])
    assert result['state']=='CONFLICTED' and not result['research_eligible']

def test_weak_credential_is_preserved_but_does_not_cancel_separate_supported_claim():
    bad=contribution(source='fixture:untrusted',verdict=V.from_status_codes(['signingCredential.untrusted']))
    result=B.summarize([bad,contribution()])
    assert result['candidate_tag']=='PA' and result['research_eligible']
    assert len(result['inputs'])==2

def test_repeating_one_evidence_object_does_not_become_independent_validation():
    row=contribution();result=B.summarize([row]*200)
    assert len(result['inputs'])==1
    assert result['independent_source_count'] is None
    assert not result['independent_release_validated'] and not result['production_assertion']

def test_inconsistent_same_reference_fails_without_selecting_a_winner():
    with pytest.raises(ValueError):B.summarize([contribution(),contribution(B.Claim.AI_NO_HUMAN)])

def test_mixed_subjects_fail_without_combining_tags():
    row=B.contribution_for(valid(),evidence=evidence(subject='b'*64,source='fixture:other'),subject_sha256='b'*64)
    with pytest.raises(ValueError):B.summarize([contribution(),row])

def test_empty_or_repeated_neutral_evidence_cannot_become_fa():
    for rows in ([],[B.contribution_for(valid())]*50):
        result=B.summarize(rows)
        assert result['candidate_tag']=='UNK' and not result['research_eligible']
        assert not result['production_assertion']

@pytest.mark.parametrize('rows',[[{}],[None],['PA']])
def test_rollup_requires_typed_contributions(rows):
    with pytest.raises(ValueError):B.summarize(rows)

def test_unbounded_iterable_stops_at_contract_limit():
    consumed=[]
    def rows():
        for n in itertools.count():
            consumed.append(n);yield B.contribution_for(valid())
    with pytest.raises(ValueError):B.summarize(rows())
    assert len(consumed)==257

def test_serialization_preserves_proposed_claim_and_truth_boundary():
    output=B.summarize([contribution()]);assert json.loads(json.dumps(output))==output
    assert 'no cryptographic or media verification' in output['trust_boundary']
    assert set(B.Tag)=={B.Tag.PA,B.Tag.FA,B.Tag.UNK}
