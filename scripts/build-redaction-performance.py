#!/usr/bin/env python3
"""Verify synthetic redaction observations and produce a bounded public chart."""
import hashlib,importlib.util,json,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from protocol.evidence import read_evidence
spec=importlib.util.spec_from_file_location('redaction_development',ROOT/'scripts/measure-redaction-development.py')
client=importlib.util.module_from_spec(spec);spec.loader.exec_module(client)
REPORT='runs/2026-10-11-pii-recognition-staging.json'
ENTITIES=['EMAIL_ADDRESS','PHONE_NUMBER','PERSON','LOCATION','IP_ADDRESS','URL','DATE_TIME']
def public_summary(report):
    wanted={'captured_at','pass','kind','rows','redactor_identity','sources','fixture_sha256','source_unchanged','independent_accuracy_evidence','real_user_data','production_services_modified','client_sources','measurement','worker_operation_observed','http_route_tested','candidate_recognizer_override','source_identity_is_not_remote_attestation'}
    if not isinstance(report,dict) or set(report)!=wanted or report['pass'] is not True or report['kind']!='synthetic_english_engine_observations' or any(report[k] is not False for k in ['independent_accuracy_evidence','real_user_data','production_services_modified','http_route_tested','candidate_recognizer_override']) or any(report[k] is not True for k in ['source_unchanged','worker_operation_observed','source_identity_is_not_remote_attestation']):raise ValueError('Invalid redaction development evidence')
    if not isinstance(report['captured_at'],str) or len(report['captured_at'])>40:raise ValueError('Invalid redaction development date')
    measured=datetime.fromisoformat(report['captured_at'])
    if measured.utcoffset() is None or measured>datetime.now(timezone.utc):raise ValueError('Invalid redaction development date')
    current={n:hashlib.sha256(client.source_bytes(n)).hexdigest() for n in client.FILES}
    if report['client_sources']!=current or report['sources']!={k:current[p] for k,p in client.SOURCES.items()}:raise ValueError('Stale redaction development source')
    fixture=read_evidence(ROOT/client.FIXTURE)
    measurement=client.summarize_observations(report,fixture,report['sources'])
    if report['measurement']!=measurement:raise ValueError('Redaction summary differs from observations')
    rows={r['id']:r for r in fixture['rows']}
    slices={k:{'fully_masked':0,'partial':0,'untouched':0,'expected':0,'cases_with_extra_masking':0,'extra_masked_characters':0} for k in ['en','out_of_coverage']}
    for row in measurement['redaction_coverage']:
        if rows[row['id']]['coverage']!=row['coverage']:raise ValueError('Invalid redaction coverage')
        s=slices[row['coverage']]
        for key,source in [('fully_masked','fully_masked_expected_spans'),('partial','partially_masked_expected_spans'),('untouched','untouched_expected_spans'),('expected','expected_spans'),('extra_masked_characters','masked_outside_expected_characters')]:s[key]+=row[source]
        s['cases_with_extra_masking']+=row['masked_outside_expected_characters']>0
    categories=[r for r in measurement['categories'] if r['coverage']=='en' and r['entity'] in ENTITIES]
    if {r['entity'] for r in categories}!=set(ENTITIES):raise ValueError('Incomplete redaction categories')
    return {'format':'ai-trust-id-redaction-development/v1','measured_at':report['captured_at'],'kind':'synthetic_development','independently_validated':False,'population_accuracy_measured':False,'privacy_clearance':False,'english':{**measurement['slices']['en'],**slices['en']},'challenges':{**measurement['slices']['out_of_coverage'],**slices['out_of_coverage']},'categories':categories,'other_extra_candidates':sum(r['fp'] for r in measurement['categories'] if r['coverage']=='en' and r['entity'] not in ENTITIES),'sources':{'report':'/reference/redaction-recognition.json','fixture':'/reference/pii-recognition-development.json'},'limits':'38 developer-authored English examples and four out-of-coverage challenges. Exact entity/span matches and actual masking are different measures; no population or independent accuracy claim.'}
def main():
    try:result=public_summary(read_evidence(ROOT/REPORT))
    except (ValueError,TypeError,KeyError,IndexError,OSError):
        print('Current synthetic redaction evidence unavailable; no chart or privacy clearance.',file=sys.stderr);return 1
    print(json.dumps(result,allow_nan=False));return 0
if __name__=='__main__':raise SystemExit(main())
