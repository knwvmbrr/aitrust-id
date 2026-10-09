"""Experimental, subject-bound provenance contributions; never production tags.

Credential validity alone does not establish authorship. Explicit claim semantics
and verification observations are trusted upstream inputs, not checks performed
here. No file, watermark, signature, key or network is read by this module.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Iterable
from services.adjudicator import verdict as V

SPEC_VERSION = 'tag-bridge/0.2.0-research'
_HASH = re.compile(r'[a-f0-9]{64}\Z')
_REFERENCE = re.compile(r'[A-Za-z0-9][A-Za-z0-9._:/-]{0,159}\Z')

class Tag(str, Enum):
    PA = 'PA'
    FA = 'FA'
    UNK = 'UNK'

class Claim(str, Enum):
    AI_HUMAN_REWORK = 'ai_generated_then_human_reworked'
    AI_NO_HUMAN = 'ai_generated_without_human_intervention'
    HUMAN = 'human_origin_claim'

class Direction(str, Enum):
    RAISE = 'raise'
    NEUTRAL = 'neutral'

def _hash(value):
    if not isinstance(value, str) or not _HASH.fullmatch(value):
        raise ValueError('Require a lowercase SHA-256 subject identifier')

def _reference(value):
    if not isinstance(value, str) or not _REFERENCE.fullmatch(value):
        raise ValueError('Require a bounded opaque evidence reference; no raw content')

@dataclass(frozen=True)
class ClaimEvidence:
    """A future trusted adapter's decoded, signed, subject-bound claim.

    binding_verified=True is an explicit upstream observation, not a verification
    operation here. source_id identifies the evidence object, not an independent
    person/source count. A hash match identifies bytes, not truth or privacy.
    """
    claim: Claim
    subject_sha256: str
    source_id: str
    binding_verified: bool

    def __post_init__(self):
        if not isinstance(self.claim, Claim):
            raise ValueError('Require an explicit supported authorship claim')
        _hash(self.subject_sha256)
        _reference(self.source_id)
        if type(self.binding_verified) is not bool:
            raise ValueError('Binding verification must be explicitly boolean')

@dataclass(frozen=True)
class Contribution:
    candidate_tag: Tag
    direction: Direction
    basis: str
    verdict_state: str
    research_eligible: bool
    subject_sha256: str | None = None
    evidence: ClaimEvidence | None = None
    credential_supported: bool = False

    def __post_init__(self):
        if not isinstance(self.candidate_tag, Tag) or not isinstance(self.direction, Direction):
            raise ValueError('Require known contribution tag/direction')
        if type(self.research_eligible) is not bool or type(self.credential_supported) is not bool:
            raise ValueError('Contribution flags must be boolean')
        if self.evidence is not None and not isinstance(self.evidence, ClaimEvidence):
            raise ValueError('Require typed claim evidence')
        if not isinstance(self.basis, str) or not self.basis.strip() or len(self.basis)>500:
            raise ValueError('Contribution basis is required')
        if self.verdict_state not in {i.name.lower() for i in V.Integrity} | {'valid_revocation_unknown'}:
            raise ValueError('Unknown credential verdict state')
        if self.subject_sha256 is not None:
            _hash(self.subject_sha256)
        if self.evidence and self.evidence.subject_sha256 != self.subject_sha256:
            raise ValueError('Claim evidence is bound to another subject')
        expected = _TAG_FOR_CLAIM.get(self.evidence.claim) if self.evidence else None
        if self.research_eligible:
            if (self.direction is not Direction.RAISE or self.candidate_tag is not expected
                or not self.credential_supported or self.verdict_state != 'valid'
                or not self.evidence.binding_verified):
                raise ValueError('Eligible research candidate requires complete explicit claim evidence')
        elif self.candidate_tag is not Tag.UNK or self.direction is not Direction.NEUTRAL:
            raise ValueError('Ineligible evidence must remain neutral UNK')
        if self.credential_supported and (self.verdict_state != 'valid' or self.evidence is None or not self.evidence.binding_verified):
            raise ValueError('Unsupported credential cannot contribute a trusted claim')
        if self.research_eligible != bool(self.credential_supported and expected):
            raise ValueError('Contribution eligibility must match its explicit supported claim')

    def to_dict(self):
        return {'spec_version':SPEC_VERSION, 'candidate_tag':self.candidate_tag.value,
                'direction':self.direction.value, 'basis':self.basis,
                'verdict_state':self.verdict_state, 'research_eligible':self.research_eligible,
                'subject_sha256':self.subject_sha256,
                'claim':self.evidence.claim.value if self.evidence else None,
                'source_id':self.evidence.source_id if self.evidence else None,
                'governing_rule':'F-083', 'production_assertion':False,
                'independent_release_validated':False}

_TAG_FOR_CLAIM = {Claim.AI_HUMAN_REWORK:Tag.PA, Claim.AI_NO_HUMAN:Tag.FA}

def contribution_for(verdict: V.Verdict, *, evidence: ClaimEvidence | None = None,
                     subject_sha256: str | None = None) -> Contribution:
    """Map explicit supplied observations to a research candidate, not a tag.

    A complete VALID verdict without a decoded authorship claim is neutral.
    Production use additionally needs an actual verified adapter, accepted claim
    mapping, independent evidence and the relevant tag's release contract.
    """
    if not isinstance(verdict, V.Verdict):
        raise ValueError('Require a typed credential verdict, not asserted flags')
    if subject_sha256 is not None:
        _hash(subject_sha256)
    if evidence is not None:
        if not isinstance(evidence, ClaimEvidence):
            raise ValueError('Require typed claim evidence')
        if subject_sha256 is None or evidence.subject_sha256 != subject_sha256:
            raise ValueError('Claim and target subject must match explicitly')
    trusted = verdict.is_asserted and evidence is not None and evidence.binding_verified
    tag = _TAG_FOR_CLAIM.get(evidence.claim) if trusted else None
    if tag:
        basis = ('The supplied verified claim describes AI generation followed by human rework.'
                 if tag is Tag.PA else 'The supplied verified claim describes generation without human intervention.')
    elif not verdict.is_asserted:
        basis = 'Credential verification is incomplete or failed; it establishes no AI authorship claim.'
    elif evidence is None:
        basis = 'A valid credential alone does not establish AI participation or human editing.'
    elif not evidence.binding_verified:
        basis = 'The authorship claim was not verified as bound to this subject.'
    else:
        basis = 'A human-origin claim is not evidence of AI participation; it is not a human-authenticity clearance.'
    return Contribution(tag or Tag.UNK, Direction.RAISE if tag else Direction.NEUTRAL,
                        basis, verdict.state, bool(tag), subject_sha256, evidence, bool(trusted))

def summarize(contributions: Iterable[Contribution]) -> dict:
    """Keep contradictions/subjects separate; repeated evidence adds no standing."""
    rows=[]
    for c in contributions:
        if len(rows)>=256 or not isinstance(c, Contribution):
            raise ValueError('Require at most 256 typed contributions')
        rows.append(c)
    subjects = {c.subject_sha256 for c in rows if c.subject_sha256 is not None}
    if len(subjects)>1:
        raise ValueError('Do not combine evidence for different subjects')
    unique=[];seen={}
    for c in rows:
        if c.evidence:
            key=c.evidence.source_id
            if key in seen:
                if c != seen[key]:
                    raise ValueError('One evidence reference has inconsistent observations')
                continue
            seen[key]=c
        unique.append(c)
    trusted_claims={c.evidence.claim for c in unique if c.credential_supported}
    conflict=len(trusted_claims)>1 or any(c.verdict_state=='conflicted' for c in unique)
    eligible=[c for c in unique if c.research_eligible]
    chosen=eligible[0] if eligible and not conflict else None
    return {'spec_version':SPEC_VERSION, 'candidate_tag':chosen.candidate_tag.value if chosen else 'UNK',
            'research_eligible':bool(chosen), 'state':'CONFLICTED' if conflict else 'SUPPORTED' if chosen else 'UNSUPPORTED',
            'subject_sha256':next(iter(subjects),None),
            'basis':'Verified authorship claims conflict; retain every source and choose no tag.' if conflict else chosen.basis if chosen else 'No supported AI authorship claim was established.',
            'inputs':[c.to_dict() for c in unique], 'governing_rule':'F-083',
            'production_assertion':False, 'independent_release_validated':False,
            'independent_source_count':None,
            'trust_boundary':'Supplied adapter observations only; no cryptographic or media verification performed here.'}
