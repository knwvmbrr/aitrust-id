"""The report writers cannot alter historical evidence or escape their destination."""
import json
from pathlib import Path
import subprocess
import pytest
from protocol.reports import write_report
ROOT=Path(__file__).resolve().parents[1]

def test_scratch_atomic_replace_and_exclusive_history(tmp_path):
    assert write_report('output/verification/check.json',{'pass':True},tmp_path).is_file()
    write_report('output/verification/check.json',{'pass':False},tmp_path)
    assert json.loads((tmp_path/'output/verification/check.json').read_text())=={'pass':False}
    p=write_report('runs/new.json',{'pass':True},tmp_path);before=p.read_bytes()
    with pytest.raises(FileExistsError):write_report('runs/new.json',{'pass':False},tmp_path)
    assert p.read_bytes()==before
    assert not list((tmp_path/'runs').glob('.report-*'))

@pytest.mark.parametrize('name',['../escape.json','state.json','runs/../state.json','runs/not-json.txt'])
def test_path_boundary(tmp_path,name):
    with pytest.raises(ValueError):write_report(name,{'x':1},tmp_path)

def test_symlink_parent_and_target_refused(tmp_path):
    external=tmp_path/'private';external.mkdir();(external/'value.json').write_text('private')
    (tmp_path/'runs').symlink_to(external,target_is_directory=True)
    with pytest.raises(ValueError):write_report('runs/value.json',{},tmp_path)
    assert (external/'value.json').read_text()=='private'
    (tmp_path/'runs').unlink();(tmp_path/'runs').mkdir();(tmp_path/'runs/value.json').symlink_to(external/'value.json')
    with pytest.raises(ValueError):write_report('runs/value.json',{},tmp_path)

def test_invalid_json_creates_nothing(tmp_path):
    with pytest.raises(ValueError):write_report('runs/no.json',{'number':float('nan')},tmp_path)
    assert not (tmp_path/'runs').exists()

def test_javascript_boundary_and_history(tmp_path):
    program="""const {writeReport}=require('./scripts/execution-report.cjs');const fs=require('fs'),path=require('path'),assert=require('assert/strict');const root=process.argv[1];
writeReport('output/verification/x.json',{pass:true},root);writeReport('output/verification/x.json',{pass:false},root);
assert.equal(JSON.parse(fs.readFileSync(path.join(root,'output/verification/x.json'))).pass,false);
writeReport('runs/x.json',{pass:true},root);assert.throws(()=>writeReport('runs/x.json',{pass:false},root));
for(const name of ['../escape.json','state.json','runs/a.txt'])assert.throws(()=>writeReport(name,{},root));
const privatePath=path.join(root,'private');fs.mkdirSync(privatePath);fs.symlinkSync(privatePath,path.join(root,'output/link'));
assert.throws(()=>writeReport('output/link/x.json',{},root));
fs.symlinkSync(path.join(root,'runs/x.json'),path.join(root,'output/symlink.json'));assert.throws(()=>writeReport('output/symlink.json',{},root));
assert.throws(()=>writeReport('runs/invalid.json',undefined,root));
assert.throws(()=>writeReport('runs/nan.json',{number:NaN},root));assert.throws(()=>writeReport('runs/infinity.json',{number:Infinity},root));
assert.equal(fs.readFileSync(path.join(root,'runs/x.json'),'utf8').includes('true'),true);
"""
    subprocess.run(['node','-e',program,str(tmp_path)],cwd=ROOT,check=True)

def test_browser_scripts_use_scratch_defaults_not_fixed_historical_outputs():
    for p in (ROOT/'scripts').glob('verify-*.cjs'):
        text=p.read_text()
        assert "||'runs/2026" not in text,p.name
        if 'writeReport(' in text:assert "require('./execution-report.cjs')" in text,p.name
    assert "runs/2026-10-10-normalization-version-gap.json" in (ROOT/'scripts/verify-device.cjs').read_text()
