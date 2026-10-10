"""Inventories fail on changed artifacts/inputs and cannot become signed clearance."""
import importlib.util
import json
from pathlib import Path
import shutil
import pytest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('runtime_sbom',ROOT/'scripts/verify-runtime-sbom.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


@pytest.fixture
def copy_root(tmp_path):
    names=module.SOURCES+['eval/dependencies/runtime-sbom.json',
        'runs/2026-10-10-runtime-license-inventory.json']+[
        f'sbom/runtime/{role}-linux-amd64.spdx.json' for role in module.ROLES]
    for name in names:
        target=tmp_path/name;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/name,target)
    return tmp_path


def test_actual_inventory_is_verifiable_and_remains_unsigned():
    r=module.verify()
    assert r['images']==3 and r['package_occurrences']==421
    assert r['sbom_identity_verified']
    assert not r['license_cleared'] and not r['release_signed']
    assert not r['vulnerabilities_assessed'] and not r['tag_release_approved']


@pytest.mark.parametrize('field', ['license_cleared','release_signed','scanner_signed_identity_verified'])
def test_self_promotion_refused(copy_root,field):
    path=copy_root/'eval/dependencies/runtime-sbom.json';m=json.loads(path.read_text())
    m[field]=True;path.write_text(json.dumps(m))
    with pytest.raises(ValueError,match='overclaimed'):module.verify(copy_root)


@pytest.mark.parametrize('mutation',['artifact','source','missing_image','wrong_image',
                                    'unsafe_path','wrong_digest','extra','missing'])
def test_binding_mutations_refused(copy_root,mutation):
    path=copy_root/'eval/dependencies/runtime-sbom.json';m=json.loads(path.read_text())
    if mutation=='artifact':(copy_root/m['images'][0]['artifact']).write_text('{}')
    elif mutation=='source':(copy_root/module.SOURCES[0]).write_text('changed')
    elif mutation=='missing_image':m['images'].pop()
    elif mutation=='wrong_image':m['images'][0]['image_id']='0'*64
    elif mutation=='unsafe_path':m['images'][0]['artifact']='../secret'
    elif mutation=='wrong_digest':m['images'][0]['manifest_digest']='0'*64
    elif mutation=='extra':m['license_permission']='approved'
    else:del m['sources']
    path.write_text(json.dumps(m))
    with pytest.raises(ValueError):module.verify(copy_root)


def test_artifact_symlink_refused(copy_root):
    path=copy_root/'sbom/runtime/gateway-linux-amd64.spdx.json'
    target=copy_root/'outside';path.rename(target);path.symlink_to(target)
    with pytest.raises(ValueError,match='evidence file'):module.verify(copy_root)
