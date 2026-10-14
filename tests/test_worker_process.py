"""Actual bounded pipes: memory caps apply before buffering, without response-content files."""
import importlib.util
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('worker_process',ROOT/'scripts/worker_process.py')
w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w)


def run(code,data=b'',limit=100000,timeout=3):
    return w.run_worker([sys.executable,'-I','-S','-B','-c',code],input=data,timeout=timeout,output_limit=limit)


def test_exact_output_limit_and_partial_writes():
    result=run('import sys;sys.stdout.buffer.write(sys.stdin.buffer.read())',b'a'*100000)
    assert result.returncode==0 and result.stdout==b'a'*100000 and result.stderr==b''


def test_actual_flood_is_stopped_at_cap_before_stalled_input(tmp_path):
    marker=tmp_path/'worker.pid'
    code='import os,sys,time;open('+repr(str(marker))+',"w").write(str(os.getpid()));sys.stdout.buffer.write(b"x"*10000000);sys.stdout.flush();time.sleep(30)'
    start=time.monotonic()
    with pytest.raises(w.WorkerOutputLimit):run(code,b'a'*800000,limit=1024)
    assert time.monotonic()-start<3
    with pytest.raises(ProcessLookupError):os.kill(int(marker.read_text()),0)


def test_deadline_kills_a_worker_that_never_reads_input(tmp_path):
    marker=tmp_path/'worker.pid'
    code='import os,time;open('+repr(str(marker))+',"w").write(str(os.getpid()));time.sleep(30)'
    with pytest.raises(subprocess.TimeoutExpired):run(code,b'a'*800000,timeout=.3)
    with pytest.raises(ProcessLookupError):os.kill(int(marker.read_text()),0)


def test_deadline_kills_descendant_holding_the_output_pipe(tmp_path):
    marker=tmp_path/'child.pid'
    code='import os,sys,time;pid=os.fork();open('+repr(str(marker))+',"w").write(str(pid)) if pid else time.sleep(30)'
    with pytest.raises(subprocess.TimeoutExpired):run(code,timeout=.3)
    pid=int(marker.read_text())
    # A killed orphan can briefly remain a zombie before init reaps it.
    status=Path('/proc')/str(pid)/'stat'
    if status.exists():assert status.read_text().split()[2]=='Z'
    else:
        observed=subprocess.run(['ps','-o','stat=','-p',str(pid)],capture_output=True,timeout=2)
        assert observed.returncode!=0 or observed.stdout.strip().startswith(b'Z')


def test_stderr_is_discarded_and_nonzero_exit_preserved():
    result=run('import sys;sys.stderr.write("PRIVATE CANARY");raise SystemExit(9)')
    assert result.returncode==9 and result.stdout==b'' and result.stderr==b''


@pytest.mark.parametrize('key,value',[('timeout',0),('timeout',float('inf')),('timeout',True),('output_limit',True),('output_limit',2000001),('input',b'a'*1000001)])
def test_invalid_budget_is_refused_before_spawn(monkeypatch,key,value):
    monkeypatch.setattr(w.subprocess,'Popen',lambda *args,**kw:pytest.fail('Invalid worker spawned'))
    options={'input':b'','timeout':3,'output_limit':1000};options[key]=value
    with pytest.raises(ValueError):w.run_worker([sys.executable,'-c','pass'],**options)


def test_unsupported_control_platform_fails_before_spawn(monkeypatch):
    monkeypatch.setattr(w.os,'name','unsupported')
    monkeypatch.setattr(w.subprocess,'Popen',lambda *args,**kw:pytest.fail('Unsupported worker spawned'))
    with pytest.raises(ValueError):run('pass')
