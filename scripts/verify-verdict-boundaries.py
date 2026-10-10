"""Execute current verdict refusal contracts; does not release provenance tags."""
import argparse
from datetime import datetime,timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from protocol.reports import write_report
from services.adjudicator import tag_bridge as bridge,verdict

def module(relative):
    spec=importlib.util.spec_from_file_location(relative.replace('/','_'),ROOT/relative)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result

def verify():
    # Private synthetic process-local credential; never printed or persisted.
    previous=os.environ.get('AITRUST_TOKEN');os.environ['AITRUST_TOKEN']='verdict-boundary-control-not-a-live-credential'
    try:gateway=module('services/gateway/app.py')
    finally:
        if previous is None:os.environ.pop('AITRUST_TOKEN',None)
        else:os.environ['AITRUST_TOKEN']=previous
    evaluator=module('services/evaluator/app.py')
    if gateway.PRODUCTION_TAGS!=frozenset({'PS','PII_REDACTED'}) or evaluator.PRODUCTION_TAGS!=frozenset({'PS'}):raise ValueError('Unaccepted production verdict')
    cases=['An ordinary answer.','ACT NOW! Only two choices. Everybody agrees.','Repeated template. '*30,'Information absent from the captured window.','Dictation, switch access, IME composition.','2020 2021 2022 2023']
    for text in cases:
        candidates=evaluator.signals(evaluator.Doc(text=text))['candidates']
        tags,_=gateway.calibrate(candidates)
        if tags:raise ValueError('Ordinary/context-only input became a verdict')
    for code in ['NF','FI','HP','MT','IV','FA','PA','UNK']:
        tags,withheld=gateway.calibrate([{'code':code,'confidence':1.,'signals':[]}])
        if tags or withheld[0]['floor'] is not None or withheld[0]['reason']!='not_in_production_allowlist':raise ValueError('Disabled verdict asserted')
    for code in ['ROGUE_AI','HUMAN','BOT','UC','SC','BT']:
        try:gateway.calibrate([{'code':code,'confidence':1.,'signals':[]}])
        except ValueError:pass
        else:raise ValueError('Unknown verdict was promoted or recorded as adopted')
    complete=['claimSignature.validated','signingCredential.trusted','assertion.dataHash.match','signingCredential.ocsp.notRevoked']
    for codes in [[],complete,complete[:-1],['signingCredential.ocsp.revoked']]:
        v=verdict.from_status_codes(codes)
        row=bridge.contribution_for(v)
        if row.candidate_tag is not bridge.Tag.UNK or row.research_eligible or row.to_dict()['production_assertion']:raise ValueError('Credential or missing evidence became authorship')
    v=verdict.from_status_codes(complete)
    human=bridge.ClaimEvidence(bridge.Claim.HUMAN,'a'*64,'fixture:human',True)
    if bridge.contribution_for(v,evidence=human,subject_sha256='a'*64).candidate_tag is not bridge.Tag.UNK:raise ValueError('Human claim became AI or authenticity verdict')
    files=['services/gateway/app.py','services/evaluator/app.py','services/adjudicator/tag_bridge.py','services/adjudicator/verdict.py','rfcs/0001-behavioral-provenance.md','rfcs/0002-authorship-receipts.md']
    stale=['we detect the second and report the first only as its complement','only recombine its own context','the most durable behavioral signal','time is the only adversarial asymmetry that does not erode','out of scope everywhere','the composition then routes to `iv`']
    for name in files[-2:]:
        text=(ROOT/name).read_text().lower()
        if any(term in text for term in stale):raise ValueError('Unsupported draft proof reintroduced')
    return {'captured_at':datetime.now(timezone.utc).isoformat(),'pass':True,'current_routes':['production_gateway','development_evaluator','experimental_typed_provenance_interpretation'],'ordinary_context_cases':len(cases),'disabled_codes_withheld':8,'unknown_codes_refused':6,'credential_missing_or_incomplete_cases':4,'human_claim_is_not_ai_or_authenticity_clearance':True,'machine_iv_unassertable':True,'outside_knowledge_not_authorship':True,'rogue_ai_code_unassertable':True,'source_sha256':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in files},'provenance_capture_implemented':False,'independent_release_validated':False,'scope':'Current production refusal and supplied-observation research contract; no human-authorship detector or real credential adapter is implemented'}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=ROOT/'output/verification/verdict-boundaries.json');a=p.parse_args();r=verify();write_report(a.output,r);print(json.dumps(r))
