#!/usr/bin/env python3
"""Demonstrate synthetic tag-boundary cases; no file/signature/media validation."""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from services.adjudicator import tag_bridge as B
from services.adjudicator import verdict as V

def main():
    subject='a'*64
    complete=['claimSignature.validated','signingCredential.trusted','assertion.dataHash.match','signingCredential.ocsp.notRevoked']
    valid=V.from_status_codes(complete)
    def supplied(claim,reference):
        return B.contribution_for(valid,evidence=B.ClaimEvidence(claim,subject,reference,True),subject_sha256=subject)
    partial=supplied(B.Claim.AI_HUMAN_REWORK,'synthetic:human-rework')
    full=supplied(B.Claim.AI_NO_HUMAN,'synthetic:full-generation')
    cases={'credential_only':B.summarize([B.contribution_for(valid)]),
           'explicit_human_rework_claim':B.summarize([partial]),
           'explicit_full_generation_claim':B.summarize([full]),
           'conflicting_claims':B.summarize([partial,full]),
           'missing_evidence':B.summarize([])}
    print(json.dumps({'synthetic_inputs_only':True,'production_assertion':False,
                      'independent_release_validated':False,'cases':cases},indent=2))
    return 0
if __name__=='__main__':raise SystemExit(main())
