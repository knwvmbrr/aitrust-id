#!/usr/bin/env python3
"""Measure fixed synthetic recognition/masking on the existing staging redactor only."""
import argparse,hashlib,json,os,re,resource,stat,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from protocol.evidence import read_evidence, unique, reject, finite
from protocol.reports import write_report
from protocol.replay_identity import RedactorIdentity
from tools.redaction_observations import compare,coverage,aggregate
SOURCES={'app':'services/anonymizer/app.py','model_loader':'services/anonymizer/model_identity.py','requirements_lock':'services/anonymizer/requirements.lock','identity_contract':'protocol/replay_identity.py','identity_builder':'services/anonymizer/replay_metadata.py'}
FIXTURE='eval/fixtures/pii-recognition-development.json'
COMPACT_FIXTURE='eval/fixtures/pii-compact-addresses.json'
PROFILES={'english':(FIXTURE,42),'compact':(COMPACT_FIXTURE,6)}
WORKER='scripts/redaction-development-worker.py'
FILES=[*SOURCES.values(),FIXTURE,COMPACT_FIXTURE,WORKER,'scripts/measure-redaction-development.py','tools/redaction_observations.py','protocol/evidence.py','protocol/reports.py']

def source_bytes(name):
    file=ROOT/name
    for path in [file,*file.parents]:
        if path==ROOT:break
        if path.is_symlink():raise ValueError('Staging diagnostic unavailable')
    fd=os.open(file,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    if not stat.S_ISREG(os.fstat(fd).st_mode):
        os.close(fd)
        raise ValueError('Staging diagnostic unavailable')
    with os.fdopen(fd,'rb') as stream:value=stream.read(2_000_001)
    if len(value)>2_000_000:raise ValueError('Staging diagnostic unavailable')
    return value

def child_limits():resource.setrlimit(resource.RLIMIT_FSIZE,(4_000_000,4_000_000))
def invoke(command,raw=None):
    # File-backed pipes cap malicious/noisy engine output without holding it in memory.
    with tempfile.TemporaryDirectory(prefix='aitrust-synthetic-redaction-') as folder:
        os.chmod(folder,0o700)
        with open(Path(folder)/'stdout','w+b') as out,open(Path(folder)/'stderr','w+b') as err:
            os.fchmod(out.fileno(),0o600);os.fchmod(err.fileno(),0o600)
            r=subprocess.run(command,input=raw,stdout=out,stderr=err,timeout=90,preexec_fn=child_limits)
            out.seek(0);data=out.read(2_000_001)
        if r.returncode or len(data)>2_000_000:raise ValueError('Staging diagnostic unavailable')
        value=json.loads(data.decode('utf-8',errors='strict'),object_pairs_hook=unique,parse_constant=reject)
        finite(value)
        return value

def summarize_observations(result,fixture,sources):
    rows=fixture['rows'];ids={r['id'] for r in rows}
    identity=RedactorIdentity.model_validate(result['redactor_identity'])
    if identity.configuration.sources.model_dump()!=sources:raise ValueError('Staging diagnostic unavailable')
    expected_fixture_hash=hashlib.sha256(json.dumps(fixture,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
    if result['fixture_sha256']!=expected_fixture_hash or not isinstance(result['rows'],list) or len(result['rows'])!=len(rows):raise ValueError('Staging diagnostic unavailable')
    if any(not isinstance(r,dict) or not isinstance(r.get('id'),str) for r in result['rows']):raise ValueError('Staging diagnostic unavailable')
    by_id={r['id']:r for r in result['rows']}
    if len(by_id)!=len(rows) or set(by_id)!=ids:raise ValueError('Staging diagnostic unavailable')
    cases=[];masking=[]
    for row in rows:
        observed=by_id[row['id']]
        if set(observed)!={'id','predicted','applied','redaction_changed','expected_literal_values_still_present'} or type(observed['redaction_changed']) is not bool or type(observed['expected_literal_values_still_present']) is not int or not 0<=observed['expected_literal_values_still_present']<=len(row['expected']):raise ValueError('Staging diagnostic unavailable')
        cases.append({'id':row['id'],'coverage':row['coverage'],'counts':compare(row['expected'],observed['predicted'],len(row['text']))})
        masking.append({'id':row['id'],'coverage':row['coverage'],**coverage(row['expected'],observed['applied'],len(row['text']))})
    summary=aggregate(cases);summary['redaction_coverage']=masking
    return summary

def measure(engine,profile='english'):
    if profile not in PROFILES:raise ValueError('Staging diagnostic unavailable')
    fixture_name,case_count=PROFILES[profile]
    before={n:hashlib.sha256(source_bytes(n)).hexdigest() for n in FILES}
    fixture=read_evidence(ROOT/fixture_name)
    # This diagnostic uses a committed fixed corpus, with no user-file argument.
    if not isinstance(fixture,dict) or set(fixture)!={'schema_version','kind','supported_language','independently_labeled','representative_sample','real_user_data','rows'} or type(fixture['schema_version']) is not int or fixture.get('schema_version')!=1 or fixture.get('kind')!='synthetic_redaction_recognition_cases' or fixture.get('real_user_data') is not False or fixture.get('representative_sample') is not False or fixture.get('independently_labeled') is not False or fixture.get('supported_language')!='en':raise ValueError('Staging diagnostic unavailable')
    rows=fixture.get('rows');ids=set()
    if not isinstance(rows,list) or len(rows)!=case_count:raise ValueError('Staging diagnostic unavailable')
    for row in rows:
        if not isinstance(row,dict) or set(row)!={'id','coverage','text','expected'} or not isinstance(row['id'],str) or not re.fullmatch('[a-z][a-z0-9_]{0,63}',row['id']) or not isinstance(row['text'],str) or len(row['text'])>2000 or row['coverage'] not in ['en','out_of_coverage'] or row['id'] in ids:raise ValueError('Staging diagnostic unavailable')
        ids.add(row['id']);compare(row['expected'],[],len(row['text']))
    target='aitrust-staging_anonymizer_1';inspection=invoke([engine,'inspect',target])
    if not isinstance(inspection,list) or len(inspection)!=1 or not isinstance(inspection[0],dict):raise ValueError('Staging diagnostic unavailable')
    details=inspection[0]
    if not isinstance(details.get('Config'),dict) or not isinstance(details.get('State'),dict) or not isinstance(details['Config'].get('Labels'),dict):raise ValueError('Staging diagnostic unavailable')
    if details['Config']['Labels'].get('com.docker.compose.project')!='aitrust-staging' or details['State']['Running'] is not True or details['Config']['User']!='10001:10001':raise ValueError('Staging diagnostic unavailable')
    sources={k:before[v] for k,v in SOURCES.items()}
    payload=json.dumps({'fixtures':fixture,'sources':sources}).encode()
    result=invoke([engine,'exec','-i',target,'python','-c',source_bytes(WORKER).decode('utf-8')],payload)
    if not isinstance(result,dict) or set(result)!={'captured_at','pass','kind','rows','redactor_identity','sources','fixture_sha256','source_unchanged','independent_accuracy_evidence','real_user_data','production_services_modified'} or result['pass'] is not True or result['kind']!='synthetic_english_engine_observations' or result['source_unchanged'] is not True or any(result[k] is not False for k in ['independent_accuracy_evidence','real_user_data','production_services_modified']) or result['sources']!=sources:raise ValueError('Staging diagnostic unavailable')
    summary=summarize_observations(result,fixture,sources)
    if before!={n:hashlib.sha256(source_bytes(n)).hexdigest() for n in FILES}:raise ValueError('Staging diagnostic unavailable')
    return {**result,'client_sources':before,'measurement':summary,'worker_operation_observed':True,'http_route_tested':False,'candidate_recognizer_override':False,'source_identity_is_not_remote_attestation':True}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--engine',choices=['docker','podman'],required=True);p.add_argument('--project',choices=['aitrust-staging'],required=True);p.add_argument('--profile',choices=sorted(PROFILES),default='english');p.add_argument('--output',required=True);a=p.parse_args()
    try:r=measure(a.engine,a.profile);write_report(a.output,r)
    except (ValueError,TypeError,KeyError,IndexError,OSError,AssertionError,subprocess.SubprocessError):
        print('Synthetic redaction diagnostic unavailable; no privacy clearance.',file=sys.stderr);return 1
    print(json.dumps({'pass':True,'cases':len(r['rows']),'independent_accuracy_evidence':False}));return 0
if __name__=='__main__':raise SystemExit(main())
