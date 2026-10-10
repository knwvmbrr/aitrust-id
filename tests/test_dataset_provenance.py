"""Per-row origin and label changes must be explicit, never silent history edits."""
import importlib.util,json,shutil
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('dataset_provenance',ROOT/'scripts/verify-dataset-provenance.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
@pytest.fixture
def folder(tmp_path):
    for p in (ROOT/'eval/datasets/unsafe_code').glob('*'):
        if p.is_file():shutil.copyfile(p,tmp_path/p.name)
    return tmp_path

def mutate(folder,fn):
    p=folder/'provenance-v1.json';x=json.loads(p.read_text());fn(x);p.write_text(json.dumps(x))

def test_all_active_and_historical_rows_are_accounted_for():
    r=m.verify(verify_history=True);assert r['examples']==101 and r['active_examples']==86 and r['source_history_verified']

@pytest.mark.parametrize('field,value',[('row_sha256','0'*64),('text_sha256','0'*64),('source_file_sha256','0'*64),('declared_labels',[]),('independent_labeler',True),('author_attribution','invented author')])
def test_bad_row_provenance(folder,field,value):
    mutate(folder,lambda d:d['examples'][0].update({field:value}))
    with pytest.raises(ValueError):m.verify(folder)

def test_missing_row(folder):
    mutate(folder,lambda d:d['examples'].pop())
    with pytest.raises(ValueError):m.verify(folder)

def test_duplicate_row(folder):
    mutate(folder,lambda d:d['examples'].append(d['examples'][0]))
    with pytest.raises(ValueError):m.verify(folder)

def test_unknown_extra_row(folder):
    mutate(folder,lambda d:d['examples'].append({**d['examples'][0],'id':'orphan:1'}))
    with pytest.raises(ValueError):m.verify(folder)

def test_changed_dataset_requires_new_manifest_and_provenance(folder):
    p=folder/'ps_v1.jsonl';p.write_text(p.read_text()+'{}\n')
    with pytest.raises(ValueError):m.verify(folder)

def test_forged_source_date_refused_when_history_verification_requested(folder):
    mutate(folder,lambda d:d['examples'][0]['origin'].update(committed_at='2020-01-01T00:00:00+00:00'))
    with pytest.raises(ValueError):m.verify(folder,verify_history=True)

def test_zip_style_metadata_check_does_not_claim_history_verification(folder):
    assert m.verify(folder)['source_history_verified'] is False
