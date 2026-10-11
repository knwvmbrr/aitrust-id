"""Boundary/compatibility controls; actual database cases run separately on Linux."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import shutil

import pytest

ROOT=Path(__file__).resolve().parents[1]


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def test_existing_local_export_matches_synthetic_fixture():
    module=load('metadata_store_fixture','scripts/verify-metadata-store.py')
    code="import {feedbackRecord} from './site/src/research-feedback.js';console.log(JSON.stringify(feedbackRecord({reported_result:'pattern_found',failure_category:'none_observed',feedback:'easy_to_understand'})));"
    actual=subprocess.check_output(['node','--input-type=module','-e',code],cwd=ROOT,text=True)
    assert json.loads(actual)==module.LOCAL
    assert module.ENVELOPE['synthetic'] is True
    assert module.ENVELOPE['permission']=='synthetic_test_only'


@pytest.mark.parametrize('path',['/','/tmp','/var/lib/postgresql/18/main','/tmp/unapproved-name','relative'])
def test_verifier_refuses_non_sandbox_before_any_database_call(path,monkeypatch):
    module=load('metadata_store_boundary','scripts/verify-metadata-store.py')
    monkeypatch.setattr(module.subprocess,'run',lambda *a,**k:pytest.fail('Refusal must precede any database call'))
    with pytest.raises((ValueError,OSError)):module.sandbox(path)


def test_root_execution_is_refused_before_database_call(tmp_path,monkeypatch):
    module=load('metadata_store_root','scripts/verify-metadata-store.py')
    monkeypatch.setattr(module.os,'geteuid',lambda:0)
    with pytest.raises(ValueError):module.sandbox(tmp_path)


def test_symlink_sandbox_is_refused(tmp_path):
    module=load('metadata_store_link','scripts/verify-metadata-store.py')
    link=tmp_path/'aitrust-metadata-link';link.symlink_to(tmp_path,target_is_directory=True)
    with pytest.raises(ValueError):module.sandbox(link)


def test_sandbox_runner_refuses_root_before_launch(tmp_path,monkeypatch):
    module=load('metadata_runner_root','scripts/metadata-store-sandbox.py')
    monkeypatch.setattr(module.sys,'platform','linux');monkeypatch.setattr(module.os,'geteuid',lambda:0)
    monkeypatch.setattr(module.subprocess,'run',lambda *a,**k:pytest.fail('No root cluster launch'))
    with pytest.raises(ValueError,match='ordinary Linux user'):module.run_control('output/verification/not-created.json')


def test_sandbox_runner_refuses_missing_binary_before_launch(monkeypatch):
    module=load('metadata_runner_missing','scripts/metadata-store-sandbox.py')
    monkeypatch.setattr(module.sys,'platform','linux');monkeypatch.setattr(module.os,'geteuid',lambda:1000)
    monkeypatch.setattr(module,'BIN',Path('/nonexistent/aitrust-control-binaries'))
    monkeypatch.setattr(module.subprocess,'run',lambda *a,**k:pytest.fail('No missing-binary launch'))
    with pytest.raises(ValueError,match='Install PostgreSQL'):module.run_control('output/verification/not-created.json')


@pytest.mark.parametrize('script',['verify-metadata-store.py','metadata-store-sandbox.py'])
def test_actual_cli_refusal_has_no_traceback_or_application_content(script):
    argv=[sys.executable,str(ROOT/'scripts'/script)]
    if script=='verify-metadata-store.py':argv += ['--sandbox-dir','/']
    elif sys.platform=='linux' and os.geteuid()!=0:
        pytest.skip('The real Linux runner is exercised by the actual database gate.')
    result=subprocess.run(argv,cwd=ROOT,capture_output=True,timeout=5)
    assert result.returncode==1 and not result.stdout
    assert b'Traceback' not in result.stderr and b'PRIVATE_METADATA_CANARY' not in result.stderr


@pytest.mark.parametrize('still_running',[True,False])
def test_shutdown_confirmation_controls_directory_retention(tmp_path,monkeypatch,still_running):
    module=load('metadata_runner_cleanup','scripts/metadata-store-sandbox.py')
    monkeypatch.setattr(module.sys,'platform','linux');monkeypatch.setattr(module.os,'geteuid',lambda:1000)
    binary=tmp_path/'bin';binary.mkdir()
    for name in ('initdb','pg_ctl','psql','postgres'):(binary/name).write_bytes(b'isolated fixture')
    directory=tmp_path/'private-synthetic-cluster';directory.mkdir(mode=0o700)
    monkeypatch.setattr(module,'BIN',binary)
    monkeypatch.setattr(module.tempfile,'mkdtemp',lambda **kwargs:str(directory))
    calls=[]
    def run(argv,**kwargs):
        calls.append(argv)
        if argv[0].endswith('initdb'):
            (directory/'data').mkdir();(directory/'data/postgresql.conf').write_text('')
        if argv[-1]=='stop':return subprocess.CompletedProcess(argv,1,b'',b'fixture stop refusal')
        if argv[-1]=='status':return subprocess.CompletedProcess(argv,0 if still_running else 3,b'',b'')
        return subprocess.CompletedProcess(argv,0,b'{"pass":true}',b'')
    monkeypatch.setattr(module.subprocess,'run',run)
    try:
        if still_running:
            with pytest.raises(ValueError,match='retained'):module.run_control('output/verification/not-written.json')
            assert directory.exists()
        else:
            assert json.loads(module.run_control('output/verification/not-written.json'))['pass']
            assert not directory.exists()
        assert any(call[-1]=='status' for call in calls)
    finally:
        if directory.exists():shutil.rmtree(directory)
