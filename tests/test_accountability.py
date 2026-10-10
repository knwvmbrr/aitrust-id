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
    for name in set(names):
        (tmp_path/name).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,tmp_path/name)
    (tmp_path/'runs/changes').mkdir(parents=True);(tmp_path/'runs/changes/synthetic.json').write_text('{}')
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
def test_missing_execution_contract_rejected(snapshot):
    (snapshot/'docs/changelog-policy.md').unlink()
    with pytest.raises(ValueError):m.verify(snapshot)
def test_reader_date_uses_ledger_client_date(monkeypatch,tmp_path):
    spec=importlib.util.spec_from_file_location('ledger_render',ROOT/'scripts/scope-progress.py');v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
    (tmp_path/'docs').mkdir();monkeypatch.setattr(v,'ROOT',tmp_path)
    data=json.loads((ROOT/'docs/scope-progress.json').read_text());data['client_date']='2026-10-10';v.render(data)
    text=(tmp_path/'docs/scope-progress.md').read_text();assert 'ledger — 2026-10-10' in text and 'client date October 10' in text
