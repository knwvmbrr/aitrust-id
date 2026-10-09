"""The CI entry point must work without ignored build outputs and reject drift."""
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]

def checkout(tmp_path):
    for name in ['scripts/verify-device-build-matrix.py','scripts/build-device-detector.py',
                 'services/evaluator/app.py','docs/device-build-reference.json']:
        dest=tmp_path/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,dest)
    return tmp_path

def run(root):
    return subprocess.run([sys.executable,str(root/'scripts/verify-device-build-matrix.py')],
                          cwd=root,capture_output=True,text=True,timeout=60)

def test_matrix_runs_in_clean_checkout_without_generated_manifest(tmp_path):
    root=checkout(tmp_path)
    assert not (root/'site').exists()
    result=run(root)
    assert result.returncode==0,result.stderr
    report=json.loads(result.stdout)
    assert report['pass'] and report['builders'][0]['fresh_output']
    assert not (root/'site').exists(), 'Verification must not require or leave generated checkout assets'

def test_changed_reference_cannot_self_validate(tmp_path):
    root=checkout(tmp_path);p=root/'docs/device-build-reference.json';reference=json.loads(p.read_text())
    reference['bundle_sha256']='0'*64;p.write_text(json.dumps(reference))
    result=run(root)
    assert result.returncode==1
    report=json.loads(result.stdout)
    assert not report['pass'] and report['errors']
