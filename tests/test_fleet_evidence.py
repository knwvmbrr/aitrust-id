"""Missing, altered and overstated receipts never complete fleet software acceptance."""
import copy,json,runpy
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1];v=runpy.run_path(str(ROOT/'scripts/verify-fleet-evidence.py'))
def candidate():
    return {'format':'fleet-software-engineering/v1','platform':'linux','captured_at':'2026-11-09T00:00:00+00:00',
            'pass':True,'non_root':True,'source_unchanged':True,'actual_cli_processes':True,'synthetic_credentials_and_inputs_only':True,
            'enrolled_real_devices':False,'production_changed':False,'collection_enabled':False,'commercial_service_activated':False,
            'independent_accuracy_evidence':False,'human_acceptance':False,'physical_phone_tested':False,'isolated_network_namespace':True,
            'sources':v['h'](),'cases':v['cases'](),'test_count':len(v['cases']()),'failures':0,'errors':0,'skipped':0}
@pytest.mark.parametrize('mutation',['source','missing_case','duplicate_case','failed','root','no_namespace','skipped','future','human','collection','commercial','real_devices'])
def test_altered_or_overstated_evidence_refused(mutation):
    row=candidate()
    if mutation=='source':row['sources'][next(iter(row['sources']))]='0'*64
    elif mutation=='missing_case':row['cases'].pop()
    elif mutation=='duplicate_case':row['cases'].append(row['cases'][0])
    elif mutation=='failed':row['failures']=1
    elif mutation=='root':row['non_root']=False
    elif mutation=='no_namespace':row['isolated_network_namespace']=False
    elif mutation=='skipped':row['skipped']=1
    elif mutation=='future':row['captured_at']='2999-01-01T00:00:00+00:00'
    elif mutation=='human':row['human_acceptance']=True
    elif mutation=='collection':row['collection_enabled']=True
    elif mutation=='commercial':row['commercial_service_activated']=True
    else:row['enrolled_real_devices']=True
    with pytest.raises(Exception):v['verify'](row,'linux')
def test_full_fleet_requirement_requires_both_actual_profiles():
    ledger=json.loads((ROOT/'docs/scope-progress.json').read_bytes());row=next(r for r in ledger['records'] if r['id']=='F-159')
    if row['percent_complete']==100:
        for platform,name in [('darwin','macos'),('linux','linux')]:
            assert v['verify'](json.loads((ROOT/('runs/2026-11-09-fleet-accepted-'+name+'.json')).read_bytes()),platform)['pass']
        assert row['completed_at'] and row['completed_by'] and not row['required_acceptance']
    else:assert row['required_acceptance'] and not row['completed_at']
