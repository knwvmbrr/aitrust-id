import copy
import importlib.util
import json
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('dependency_contract',ROOT/'scripts/verify-dependencies.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def test_actual_selected_inventory():
    r=m.verify();assert r['pass'] and r['active_services']==['anonymizer','evaluator','gateway']
    assert len(r['python'])==4 and len(r['npm'])==2

@pytest.mark.parametrize('text',['foo==1.0','foo>=1.0 --hash=sha256:'+'a'*64,'foo==1.0 --hash=sha256:nope','--index-url https://example.test','foo==1.0 \\',''])
def test_missing_unpinned_malformed_and_empty_locks_fail(text):
    with pytest.raises(ValueError):m.python_lock(text)

def test_duplicate_and_private_url_refused():
    line='foo==1.0 --hash=sha256:'+'a'*64
    for value in [line+'\n'+line,'foo @ https://user:private@example.test/a.whl --hash=sha256:'+'a'*64]:
        with pytest.raises(ValueError):m.python_lock(value)

@pytest.mark.parametrize('field,value',[('integrity',None),('integrity','sha512-invalid'),('version','latest'),('resolved','http://registry.npmjs.org/a.tgz'),('resolved','https://private.example/a.tgz')])
def test_npm_negative_integrity_controls(field,value):
    lock=json.loads((ROOT/'package-lock.json').read_text());key=next(k for k in lock['packages'] if k)
    lock['packages'][key][field]=value
    with pytest.raises((ValueError,AttributeError)):m.npm_lock(lock)

@pytest.mark.parametrize('change',['base','install','active-service','format-dep'])
def test_release_inventory_rejects_mutations(tmp_path,change):
    import shutil
    for path in ['deploy/docker-compose.yml','eval/requirements.lock','package-lock.json','package.json','site/package-lock.json','site/package.json',*[f'services/{name}/{file}' for name in ('gateway','anonymizer','evaluator') for file in ('Dockerfile','requirements.lock')]]:
        target=tmp_path/path;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/path,target)
    if change=='base':
        p=tmp_path/'services/gateway/Dockerfile';p.write_text(p.read_text().replace(m.BASE,'python:3.12-slim'))
    elif change=='install':
        p=tmp_path/'services/gateway/Dockerfile';p.write_text(p.read_text().replace('--require-hashes ',''))
    elif change=='active-service':
        p=tmp_path/'deploy/docker-compose.yml';p.write_text(p.read_text().replace('    profiles: [registry]\n',''))
    else:
        p=tmp_path/'eval/requirements.lock';p.write_text(p.read_text().replace('rfc3339-validator==0.1.4','not-the-format-dependency==0.1.4'))
    with pytest.raises(ValueError):m.verify(tmp_path)
