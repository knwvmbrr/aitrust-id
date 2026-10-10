"""Missing owners, unsupported promises and missing risk evidence must fail."""
import importlib.util
import json
from pathlib import Path
import shutil
import pytest
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('project_controls',ROOT/'scripts/verify-project-controls.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
@pytest.fixture
def snapshot(tmp_path):
    roster=json.loads((ROOT/'docs/maintainers.json').read_text());threats=json.loads((ROOT/'docs/threat-controls.json').read_text())
    names=['docs/maintainers.json','docs/threat-controls.json','CONTRIBUTING.md','THREAT_MODEL.md']+[r['contract'] for r in roster['lanes']]+[p for r in threats['threats'] for p in r['evidence']]
    for name in set(names):
        p=tmp_path/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,p)
    return tmp_path

def mutate(root,name,fn):
    p=root/name;d=json.loads(p.read_text());fn(d);p.write_text(json.dumps(d))

def test_current_controls():assert m.verify()['threats']==10
@pytest.mark.parametrize('lane',['security','adapters'])
def test_missing_ongoing_owner(snapshot,lane):
    mutate(snapshot,'docs/maintainers.json',lambda d:next(r for r in d['lanes'] if r['id']==lane).update(owner=''))
    with pytest.raises(ValueError,match='owner'):m.verify(snapshot)

def test_unaccepted_sla(snapshot):
    mutate(snapshot,'docs/maintainers.json',lambda d:d.update(response_sla_accepted=True))
    with pytest.raises(ValueError):m.verify(snapshot)

def test_missing_invariant(snapshot):
    p=snapshot/'CONTRIBUTING.md';p.write_text(p.read_text().replace('6. **','7. **'))
    with pytest.raises(ValueError,match='invariant'):m.verify(snapshot)

@pytest.mark.parametrize('field',['residual','control','owner_lane','evidence'])
def test_incomplete_threat(snapshot,field):
    mutate(snapshot,'docs/threat-controls.json',lambda d:d['threats'][0].update({field:[] if field=='evidence' else ''}))
    with pytest.raises(ValueError):m.verify(snapshot)

def test_missing_evidence(snapshot):
    (snapshot/'runs/2026-10-10-model-image-integrity.json').unlink()
    with pytest.raises(ValueError,match='evidence'):m.verify(snapshot)

def test_stale_render(snapshot):
    p=snapshot/'THREAT_MODEL.md';p.write_text(p.read_text()+'Unsupported sentence.\n')
    with pytest.raises(ValueError,match='stale'):m.verify(snapshot)
