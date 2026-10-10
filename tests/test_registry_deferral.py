"""Release deferral must refuse opt-in activation before storage or network begins."""
import copy
import importlib.util
from pathlib import Path
import os
import subprocess
import sys
import yaml
import pytest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('registry_guard',ROOT/'scripts/verify-route-boundaries.py')
guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)

def test_current_deferred_image_and_profile_contract():
    value=yaml.safe_load((ROOT/'deploy/docker-compose.yml').read_text())
    assert guard.compose_boundary(value)==['anonymizer','evaluator','gateway']
    guard.registry_image_boundary(ROOT)

@pytest.mark.parametrize('field,value',[('ports',['127.0.0.1:8501:8501']),('volumes',['private:/data']),('command',['streamlit','run','prototype/app.py']),('entrypoint','sh'),('image','unreviewed:latest'),('environment',{'VERSION':'1.0.0'}),('network_mode','host'),('read_only',False),('cap_drop',[]),('restart','always')])
def test_activation_or_persistence_overrides_are_refused(field,value):
    config=yaml.safe_load((ROOT/'deploy/docker-compose.yml').read_text())
    config['services']['registry'][field]=value
    with pytest.raises(ValueError,match='Deferred registry'):
        guard.compose_boundary(config)

def test_unused_persistent_volume_is_also_refused():
    config=yaml.safe_load((ROOT/'deploy/docker-compose.yml').read_text())
    config['volumes']={'registry-data':{}}
    with pytest.raises(ValueError,match='persistent registry'):
        guard.compose_boundary(config)

@pytest.mark.parametrize('extra',['\nRUN pip install streamlit\n','\nEXPOSE 8501\n','\nENTRYPOINT ["sh"]\n'])
def test_image_cannot_activate_other_code_even_if_source_is_available(tmp_path,extra):
    folder=tmp_path/'services/registry';folder.mkdir(parents=True)
    (folder/'deferred.py').write_bytes((ROOT/'services/registry/deferred.py').read_bytes())
    (folder/'Dockerfile').write_text((ROOT/'services/registry/Dockerfile').read_text()+extra)
    with pytest.raises(ValueError,match='image activates'):
        guard.registry_image_boundary(tmp_path)

def test_modified_launcher_is_refused(tmp_path):
    folder=tmp_path/'services/registry';folder.mkdir(parents=True)
    (folder/'deferred.py').write_bytes((ROOT/'services/registry/deferred.py').read_bytes()+b'\nopen("/data/leak", "w")\n')
    with pytest.raises(ValueError,match='launcher changed'):
        guard.registry_image_boundary(tmp_path)

@pytest.mark.parametrize('version',['0.1.0','1.0.0','PRIVATE_ENV_CANARY'])
def test_actual_launcher_exits_without_creating_or_reading_application_data(tmp_path,version):
    data=tmp_path/'data';data.mkdir();marker=data/'private-marker';marker.write_bytes(b'SYNTHETIC_PRIVATE_RECORD')
    before={str(p.relative_to(tmp_path)):p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    result=subprocess.run([sys.executable,str(ROOT/'services/registry/deferred.py'),'PRIVATE_ARG_CANARY'],cwd=tmp_path,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','AITRUST_REGISTRY_VERSION':version,'AITRUST_REGISTRY_DATA':str(data)},capture_output=True,timeout=5)
    assert result.returncode==64
    assert result.stdout==b'AI Trust ID registry is deferred from this release. No registry storage or listener was started.\n'
    assert not result.stderr
    assert b'PRIVATE' not in result.stdout
    assert before=={str(p.relative_to(tmp_path)):p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}


def test_actual_linux_refusal_evidence_matches_current_sources():
    import json
    manifest=json.loads((ROOT/'eval/route-boundaries.json').read_text())
    assert guard.registry_evidence(manifest['registry_evidence'])==2

@pytest.mark.parametrize('change',['pass','source','activation','identity','cleanup','missing_case','write','port'])
def test_failed_or_stale_container_evidence_is_refused(monkeypatch,change):
    import json
    selected=json.loads((ROOT/'eval/route-boundaries.json').read_text())['registry_evidence']
    original=guard.read_json
    def altered(file):
        report=original(file)
        if change=='pass':report['pass']=False
        if change=='source':report['sources']['services/registry/deferred.py']='0'*64
        if change=='activation':report['registry_activated']=True
        if change=='identity':report['runtime_identity']['uid']=0
        if change=='cleanup':report['cleanup']['verified']=False
        if change=='missing_case':report['cases'].pop()
        if change=='write':report['cases'][0]['data_unchanged']=False
        if change=='port':report['cases'][0]['no_published_ports']=False
        return report
    monkeypatch.setattr(guard,'read_json',altered)
    with pytest.raises(ValueError):guard.registry_evidence(selected)
