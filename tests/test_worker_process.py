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
    # Signal delivery to descendants can lag behind the reaped group leader.
    # Require observed exit/zombie within a bounded grace period, on both OSes.
    deadline=time.monotonic()+2
    while True:
        status=Path('/proc')/str(pid)/'stat'
        if status.exists():
            try:dead=status.read_text().split()[2]=='Z'
            except FileNotFoundError:dead=True
        else:
            observed=subprocess.run(['ps','-o','stat=','-p',str(pid)],capture_output=True,timeout=2)
            dead=observed.returncode!=0 or observed.stdout.strip().startswith(b'Z')
        if dead:break
        assert time.monotonic()<deadline,'Owned descendant remained running after group kill'
        time.sleep(.02)


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


def test_selector_startup_failure_reaps_owned_child_and_closes_pipes(monkeypatch):
    created=[];spawn=w.subprocess.Popen
    def capture(*args,**kwargs):
        child=spawn(*args,**kwargs);created.append(child);return child
    monkeypatch.setattr(w.subprocess,'Popen',capture)
    def failed_selector():raise OSError('Synthetic selector startup failure')
    monkeypatch.setattr(w.selectors,'DefaultSelector',failed_selector)
    with pytest.raises(OSError):run('import time;time.sleep(30)')
    assert len(created)==1 and created[0].returncode is not None
    assert created[0].stdin.closed and created[0].stdout.closed


def test_post_reap_failure_never_signals_released_process_group(monkeypatch):
    created=[];signals=[];spawn=w.subprocess.Popen;kill=w.os.killpg
    def capture(*args,**kwargs):
        child=spawn(*args,**kwargs);created.append(child);wait=child.wait
        def after_wait(*a,**kw):
            wait(*a,**kw)
            raise OSError('Synthetic failure after actual reap')
        child.wait=after_wait
        return child
    def guarded_signal(pid,sig):
        signals.append((pid,sig))
        # Never send a real signal to an already released identifier in a test.
        if created[0].returncode is None:kill(pid,sig)
    monkeypatch.setattr(w.subprocess,'Popen',capture)
    monkeypatch.setattr(w.os,'killpg',guarded_signal)
    with pytest.raises(OSError):run('pass')
    assert created[0].returncode==0 and signals==[]
    assert created[0].stdin.closed and created[0].stdout.closed


def test_selector_close_failure_still_closes_both_owned_pipes(monkeypatch):
    created=[];spawn=w.subprocess.Popen;select=w.selectors.DefaultSelector
    def capture(*args,**kwargs):
        child=spawn(*args,**kwargs);created.append(child);return child
    def closing_selector():
        selector=select();close=selector.close
        def failed_close():
            close();raise OSError('Synthetic selector close failure')
        selector.close=failed_close
        return selector
    monkeypatch.setattr(w.subprocess,'Popen',capture)
    monkeypatch.setattr(w.selectors,'DefaultSelector',closing_selector)
    with pytest.raises(OSError):run('pass')
    assert created[0].returncode==0
    assert created[0].stdin.closed and created[0].stdout.closed


def test_clock_start_failure_occurs_before_any_child_is_spawned(monkeypatch):
    def failed_clock():raise OSError('Synthetic clock startup failure')
    monkeypatch.setattr(w.time,'monotonic',failed_clock)
    monkeypatch.setattr(w.subprocess,'Popen',lambda *args,**kw:pytest.fail('Clock failure spawned a worker'))
    with pytest.raises(OSError):run('pass')


def test_clock_failure_inside_pipe_loop_reaps_owned_child(monkeypatch):
    created=[];spawn=w.subprocess.Popen;clock=w.time.monotonic;calls=0
    def capture(*args,**kwargs):
        child=spawn(*args,**kwargs);created.append(child);return child
    def failed_second_clock():
        nonlocal calls
        calls+=1
        if calls>1:raise OSError('Synthetic clock loop failure')
        return clock()
    monkeypatch.setattr(w.subprocess,'Popen',capture)
    monkeypatch.setattr(w.time,'monotonic',failed_second_clock)
    with pytest.raises(OSError):run('import time;time.sleep(30)')
    assert created[0].returncode is not None
    assert created[0].stdin.closed and created[0].stdout.closed
