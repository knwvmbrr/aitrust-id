"""Overstated or stale development records cannot close reporting intake."""
import json,runpy
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1];v=runpy.run_path(str(ROOT/'scripts/verify-hash-reports-evidence.py'))
def candidate():
    return {'format':'private-hash-inbox-engineering/v1','platform':'linux','captured_at':'2026-11-09T00:00:00+00:00','pass':True,'non_root':True,'source_unchanged':True,'actual_cli_processes':True,'synthetic_hash_feedback_only':True,'company_collection_enabled':False,'public_registry_enabled':False,'production_changed':False,'automatic_forwarding':False,'real_user_feedback_collected':False,'training_labels_created':False,'independent_accuracy_evidence':False,'human_acceptance':False,'isolated_network_namespace':True,'sources':v['h'](),'cases':v['cases'](),'test_count':len(v['cases']()),'failures':0,'errors':0,'skipped':0}
@pytest.mark.parametrize('mutation',['source','case','root','namespace','skip','failed','future','collection','registry','real_feedback','training','accuracy'])
def test_altered_or_overstated_receipt_refused(mutation):
    d=candidate()
    if mutation=='source':d['sources'][next(iter(d['sources']))]='0'*64
    elif mutation=='case':d['cases'].pop()
    elif mutation=='root':d['non_root']=False
    elif mutation=='namespace':d['isolated_network_namespace']=False
    elif mutation=='skip':d['skipped']=1
    elif mutation=='failed':d['errors']=1
    elif mutation=='future':d['captured_at']='2999-01-01T00:00:00+00:00'
    else:d[{'collection':'company_collection_enabled','registry':'public_registry_enabled','real_feedback':'real_user_feedback_collected','training':'training_labels_created','accuracy':'independent_accuracy_evidence'}[mutation]]=True
    with pytest.raises(Exception):v['verify'](d,'linux')
def test_full_intake_software_acceptance_requires_both_actual_profiles():
    row=next(r for r in json.loads((ROOT/'docs/scope-progress.json').read_bytes())['records'] if r['id']=='F-045')
    if row['percent_complete']==100:
        for platform,name in [('darwin','macos'),('linux','linux')]:assert v['verify'](json.loads((ROOT/('runs/2026-11-09-hash-inbox-current-'+name+'.json')).read_bytes()),platform)['pass']
        assert row['completed_at'] and row['completed_by'] and not row['required_acceptance']
    else:assert row['required_acceptance'] and not row['completed_at']
