"""Missing owners and contradictory state must fail instead of appearing complete."""
import importlib.util,json,shutil
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('accountability',ROOT/'scripts/verify-accountability.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
@pytest.fixture
def snapshot(tmp_path):
    roster=json.loads((ROOT/'docs/maintainers.json').read_text())
    names=['README.md','CHANGELOG.md','MAINTAINERS.md','DECISIONS.md','state.json','docs/changelog-policy.md','docs/maintainers.json','docs/scope-progress.json']+[r['contract'] for r in roster['lanes']]
    state=json.loads((ROOT/'state.json').read_text())
    def refs(v):
        if isinstance(v,dict):
            for x in v.values():yield from refs(x)
        elif isinstance(v,list):
            for x in v:yield from refs(x)
        elif isinstance(v,str) and v.startswith('runs/') and v.endswith('.json'):yield v
    names+=list(refs(state))
    for name in set(names):
        (tmp_path/name).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,tmp_path/name)
    (tmp_path/'runs/changes').mkdir(parents=True,exist_ok=True);(tmp_path/'runs/changes/synthetic.json').write_text('{}')
    return tmp_path
def mutate(root,name,change):
    p=root/name;d=json.loads(p.read_text());change(d);p.write_text(json.dumps(d))
def test_current_accountability_contract_matches_state():assert m.verify()['named_lanes']==6
@pytest.mark.parametrize('field',['institution_operating','response_sla_accepted','tools_are_legal_officers'])
def test_unaccepted_institution_or_guarantee_rejected(snapshot,field):
    mutate(snapshot,'docs/maintainers.json',lambda d:d.update({field:True}))
    with pytest.raises(ValueError,match='Unaccepted'):m.verify(snapshot)
def test_unassigned_lane_rejected(snapshot):
    mutate(snapshot,'docs/maintainers.json',lambda d:d['lanes'][0].update(owner=''))
    with pytest.raises(ValueError,match='Unassigned'):m.verify(snapshot)
def test_stale_scope_count_rejected(snapshot):
    mutate(snapshot,'state.json',lambda d:d['scope_completion'].update(open_records=d['scope_completion']['open_records']+1))
    with pytest.raises(ValueError,match='contradicts'):m.verify(snapshot)
@pytest.mark.parametrize('target',[None,True,-1,203])
def test_invalid_goal_target_refused(snapshot,target):
    mutate(snapshot,'state.json',lambda d:d['scope_completion'].update(target_open_records=target))
    with pytest.raises(ValueError,match='Scope target'):m.verify(snapshot)
def test_remaining_work_cannot_be_erased_from_target(snapshot):
    mutate(snapshot,'state.json',lambda d:d['scope_completion'].update(target_remaining_closures=0))
    with pytest.raises(ValueError,match='remaining closures'):m.verify(snapshot)
def test_missing_execution_contract_rejected(snapshot):
    (snapshot/'docs/changelog-policy.md').unlink()
    with pytest.raises(ValueError):m.verify(snapshot)
def test_reader_date_uses_ledger_client_date(monkeypatch,tmp_path):
    spec=importlib.util.spec_from_file_location('ledger_render',ROOT/'scripts/scope-progress.py');v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
    (tmp_path/'docs').mkdir();monkeypatch.setattr(v,'ROOT',tmp_path)
    data=json.loads((ROOT/'docs/scope-progress.json').read_text());data['client_date']='2026-10-10';v.render(data)
    text=(tmp_path/'docs/scope-progress.md').read_text();assert 'ledger — 2026-10-10' in text and 'client date October 10' in text


def test_snapshot_cannot_predate_referenced_execution(snapshot):
    mutate(snapshot,'state.json',lambda d:d.update(updated='2026-01-01T00:00:00+00:00',updated_at='2026-01-01T00:00:00+00:00'))
    with pytest.raises(ValueError,match='predates'):m.verify(snapshot)

@pytest.mark.parametrize('value',['2026-10-10T12:00:00','2999-01-01T00:00:00Z','2026-02-30T00:00:00Z',None])
def test_invalid_state_time_refused(snapshot,value):
    mutate(snapshot,'state.json',lambda d:d.update(updated=value,updated_at=value))
    with pytest.raises(ValueError,match='timestamp'):m.verify(snapshot)

def test_disagreeing_state_times_refused(snapshot):
    mutate(snapshot,'state.json',lambda d:d.update(updated='2026-01-01T00:00:00Z'))
    with pytest.raises(ValueError,match='disagree'):m.verify(snapshot)

@pytest.mark.parametrize('case',['missing','naive','future','invalid','link','traversal','duplicate','not-object'])
def test_state_evidence_reference_errors_refused(snapshot,case):
    relative='runs/state-chronology-control.json';p=snapshot/relative
    p.write_text(json.dumps({'captured_at':'2026-01-01T00:00:00+00:00'}))
    if case=='missing':p.unlink()
    elif case in ['naive','future','invalid']:p.write_text(json.dumps({'captured_at':{'naive':'2026-01-01T00:00:00','future':'2999-01-01T00:00:00Z','invalid':'not-a-date'}[case]}))
    elif case=='link':
        target=snapshot/'actual-receipt.json';target.write_bytes(p.read_bytes());p.unlink();p.symlink_to(target)
    elif case=='traversal':relative='runs/../state.json'
    elif case=='duplicate':p.write_text('{"captured_at":"2026-01-01T00:00:00Z","captured_at":"2026-01-02T00:00:00Z"}')
    elif case=='not-object':p.write_text('[]')
    mutate(snapshot,'state.json',lambda d:d.update(chronology_control=relative))
    with pytest.raises((ValueError,OSError)):m.verify(snapshot)

def test_date_only_history_stays_explicitly_untimed(snapshot):
    p=snapshot/'runs/date-only-history.json';p.write_text('{"date":"2026-01-01"}')
    mutate(snapshot,'state.json',lambda d:d.update(chronology_control='runs/date-only-history.json'))
    report=m.verify(snapshot)
    assert report['state_chronology_verified'] and report['untimed_evidence_references']>0

def publication_receipt(snapshot,after=False):
    receipt={'captured_at':'2026-01-03T00:00:00Z','published_at':'2026-01-02T00:00:00Z',
        'verification_finished_before_publication':not after,
        'actual_mac_verification':{'pass':True,'captured_at':'2026-01-01T00:00:00Z'},
        'actual_network_isolated_linux_verification':{'pass':True,'captured_at':
            '2026-01-02T12:00:00Z' if after else '2026-01-01T12:00:00Z'}}
    path=snapshot/'runs/publication-timing-control.json';path.write_text(json.dumps(receipt))
    mutate(snapshot,'state.json',lambda d:d.update(publication_timing_control='runs/publication-timing-control.json'))
    return receipt,path

@pytest.mark.parametrize('after',[False,True])
def test_publication_timing_accepts_truthful_before_and_after_checks(snapshot,after):
    publication_receipt(snapshot,after)
    assert m.verify(snapshot)['state_chronology_verified']

@pytest.mark.parametrize('case',['late-check','early-capture','missing-check-date','failed-check','missing-published','nonboolean','no-checks'])
def test_false_or_incomplete_publication_timing_refused(snapshot,case):
    receipt,path=publication_receipt(snapshot,after=True)
    if case=='late-check':receipt['verification_finished_before_publication']=True
    elif case=='early-capture':receipt['captured_at']='2026-01-02T00:00:00Z'
    elif case=='missing-check-date':del receipt['actual_mac_verification']['captured_at']
    elif case=='failed-check':receipt['actual_mac_verification']['pass']=False
    elif case=='missing-published':del receipt['published_at']
    elif case=='nonboolean':receipt['verification_finished_before_publication']=1
    else:
        del receipt['actual_mac_verification'];del receipt['actual_network_isolated_linux_verification']
    path.write_text(json.dumps(receipt))
    with pytest.raises(ValueError):m.verify(snapshot)

@pytest.mark.parametrize('platform,value',[('mac',False),('network_isolated_linux',True),('mac',1)])
def test_false_platform_publication_timing_refused(snapshot,platform,value):
    receipt,path=publication_receipt(snapshot,after=True)
    receipt[platform+'_verification_finished_before_publication']=value
    path.write_text(json.dumps(receipt))
    with pytest.raises(ValueError,match='Platform'):m.verify(snapshot)
