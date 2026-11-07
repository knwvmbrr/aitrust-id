"""Recovery evidence must not substitute empty-state or staged checks for broader claims."""
import copy,json,runpy
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1];v=runpy.run_path(str(ROOT/'scripts/verify-host-recovery-evidence.py'))
def test_recorded_recovery_acceptance_is_current():
    d=json.loads((ROOT/'runs/2026-11-06-host-final-acceptance.json').read_bytes());assert v['verify'](d)['pass'] is True
@pytest.mark.parametrize('bad',['stale','missing','duplicate','failed','retained_disk','physical_erasure','occupied_tables','human','scale','current_full_rerun','intake','source_changed','no_private_channel','sla'])
def test_bad_recovery_evidence_refused(bad):
    d=json.loads((ROOT/'runs/2026-11-06-host-final-acceptance.json').read_bytes())
    if bad=='stale':d['sources'][next(iter(d['sources']))]='0'*64
    elif bad=='missing':d['controls'].pop()
    elif bad=='duplicate':d['controls'][-1]=d['controls'][0]
    elif bad=='failed':d['controls'][0]['pass']=False
    elif bad=='retained_disk':d['cleanup']['decrypted_guest_disk_removed']=False
    elif bad=='physical_erasure':d['physical_erasure_claimed']=True
    elif bad=='occupied_tables':d['occupied_application_table_recovery_claimed']=True
    elif bad=='human':d['physical_or_human_acceptance']=True
    elif bad=='scale':d['production_scale_rto_claimed']=True
    elif bad=='current_full_rerun':d['current_source_full_vm_rerun_claimed']=True
    elif bad=='intake':d['collection_enabled']=True
    elif bad=='source_changed':d['production_source_host_changed']=True
    elif bad=='no_private_channel':d['private_security_reporting_enabled']=False
    else:d['response_sla_claimed']=True
    with pytest.raises(Exception):v['verify'](d)


def test_operational_acceptance_and_full_closure_preserve_the_original_job():
    assert v['verify_operations']()['private_reporting_channel_enabled'] is True
    row=next(r for r in json.loads((ROOT/'docs/scope-progress.json').read_bytes())['records'] if r['id']=='F-073')
    if row['percent_complete']==100:
        assert row['completed_by'] and row['completed_at'] and row['required_acceptance']==[]
        assert 'runs/2026-11-07-security-operations-acceptance.json' in row['evidence']
        assert v['verify'](json.loads((ROOT/'runs/2026-11-06-host-final-acceptance.json').read_bytes()))['pass'] is True
    else:assert row['required_acceptance'] and row['completed_at'] is None
