"""A full directory software closure requires actual current provider evidence."""
import copy,json,runpy
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
v=runpy.run_path(str(ROOT/'scripts/verify-organization-directory-evidence.py'))

def candidate():
    return {'format':'organization-directory-software/v1','captured_at':'2026-11-06T00:00:00+00:00','platform':'linux','pass':True,'source_unchanged':True,'non_root':True,'isolated_network_namespace':True,'real_provider_and_database':True,'synthetic_identities_only':True,'production_changed':False,'collection_enabled':False,'independent_accuracy_evidence':False,'human_acceptance':False,'certification':False,'keycloak_version':'26.8.2','postgresql_major':18,'failure':None,'sources':v['hashes'](),'controls':[{'case':n,'pass':True} for n in v['CASES']]}

@pytest.mark.parametrize('mutation',['stale','missing_case','failed_case','duplicate_case','root','no_namespace','future','human','intake','startup_failure'])
def test_bad_evidence_refused(mutation):
    row=candidate()
    if mutation=='stale':row['sources'][next(iter(row['sources']))]='0'*64
    elif mutation=='missing_case':row['controls'].pop()
    elif mutation=='failed_case':row['controls'][0]['pass']=False
    elif mutation=='duplicate_case':row['controls'].append(row['controls'][0])
    elif mutation=='root':row['non_root']=False
    elif mutation=='no_namespace':row['isolated_network_namespace']=False
    elif mutation=='future':row['captured_at']='2999-01-01T00:00:00+00:00'
    elif mutation=='human':row['human_acceptance']=True
    elif mutation=='intake':row['collection_enabled']=True
    else:row['failure']={'stage':'startup'}
    with pytest.raises(Exception):v['verify'](row)

def test_full_scope_closure_requires_the_actual_receipt():
    row=next(r for r in json.loads((ROOT/'docs/scope-progress.json').read_bytes())['records'] if r['id']=='F-162')
    if row['percent_complete']==100:
        receipt=json.loads((ROOT/'runs/2026-11-07-directory-clock-linux.json').read_bytes());assert v['verify'](receipt)['pass'] is True
        assert row['required_acceptance']==[] and row['completed_by'] and row['completed_at']
    else:assert row['required_acceptance'] and row['completed_at'] is None
