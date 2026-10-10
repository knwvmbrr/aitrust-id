import importlib.util
import json
from pathlib import Path
import shutil
import pytest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('tag_development',ROOT/'scripts/verify-tag-development.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def test_actual_families_are_versioned_development_only():
    r=m.verify();assert r['rows']==36 and not r['independent_accuracy_evidence'] and not r['release_holdout']

@pytest.mark.parametrize('change',['bytes','family','count','independent','holdout','accuracy','identity','duplicate','runtime'])
def test_invalid_or_overclaimed_fixtures_fail(tmp_path,change,monkeypatch):
    folder=tmp_path/'fixtures';shutil.copytree(ROOT/'eval/datasets/tag_development',folder)
    file=folder/'manifest.json';data=json.loads(file.read_text())
    if change=='bytes':(folder/'hp-v1.jsonl').write_text('changed\n')
    elif change=='family':data['files'].pop('fi-v1.jsonl')
    elif change=='count':data['files']['hp-v1.jsonl']['rows']=1
    elif change in ('independent','holdout','accuracy'):data[{'independent':'independently_labeled','holdout':'release_holdout','accuracy':'classifier_accuracy_established'}[change]]=True
    else:
        import hashlib
        path=folder/'hp-v1.jsonl';rows=path.read_text().splitlines();row=json.loads(rows[0])
        if change=='identity':row['id']='HP-02'
        elif change=='runtime':row['expected_runtime']='released'
        if change=='duplicate':rows[0]=rows[0].replace('"id":','"id":"forged","id":',1)
        else:rows[0]=json.dumps(row)
        raw=('\n'.join(rows)+'\n').encode();path.write_bytes(raw);data['files']['hp-v1.jsonl']['sha256']=hashlib.sha256(raw).hexdigest()
    file.write_text(json.dumps(data))
    with pytest.raises(ValueError):m.verify(folder)
