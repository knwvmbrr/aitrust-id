"""Owned real child controls; signals are either intercepted or exact-child checked."""
import os
from pathlib import Path
import signal
import subprocess
import sys
import unittest
from unittest import mock
from tools import artifact_process as process

class ArtifactProcess(unittest.TestCase):
    def setUp(self):
        self.children=[];self.real_popen=subprocess.Popen;self.real_kill=os.killpg
    def spawned(self,*args,**kwargs):
        child=self.real_popen(*args,**kwargs);self.children.append(child);return child
    def safe_kill(self,pid,sig):
        self.assertTrue(any(c.pid==pid and c.returncode is None for c in self.children))
        self.real_kill(pid,sig)
    def assert_clean(self):
        for child in self.children:
            self.assertIsNotNone(child.returncode);self.assertTrue(child.stdin.closed);self.assertTrue(child.stdout.closed)
    def run(self,result=None):
        return super().run(result)
    def execute(self,code,input=b'',timeout=2,limit=4096):
        return process.run_worker([sys.executable,'-I','-S','-B','-c',code],input=input,timeout=timeout,output_limit=limit)
    def test_actual_stdin_stdout_normal_completion(self):
        with mock.patch.object(process.subprocess,'Popen',side_effect=self.spawned):
            r=self.execute('import sys;sys.stdout.buffer.write(sys.stdin.buffer.read().upper())',b'owned fixture')
        self.assertEqual(r.stdout,b'OWNED FIXTURE');self.assertEqual(r.returncode,0);self.assert_clean()
    def test_postwait_error_never_signals_reaped_group(self):
        def spawn(*args,**kwargs):
            child=self.spawned(*args,**kwargs);wait=child.wait
            def postwait(*args,**kwargs):wait(*args,**kwargs);raise OSError('PRIVATE_POSTWAIT_CANARY')
            child.wait=postwait;return child
        signals=[]
        with mock.patch.object(process.subprocess,'Popen',side_effect=spawn),mock.patch.object(process.os,'killpg',side_effect=lambda *args:signals.append(args)):
            with self.assertRaises(ValueError):self.execute('print("OWNED")')
        self.assertEqual(signals,[]);self.assertEqual(self.children[0].returncode,0);self.assert_clean()
    def test_selector_construction_failure_reaps_only_owned_child(self):
        with mock.patch.object(process.subprocess,'Popen',side_effect=self.spawned),mock.patch.object(process.selectors,'DefaultSelector',side_effect=OSError('PRIVATE_SELECTOR_CANARY')),mock.patch.object(process.os,'killpg',side_effect=self.safe_kill):
            with self.assertRaises(ValueError):self.execute('import time;time.sleep(30)')
        self.assert_clean()
    def test_postspawn_clock_failure_is_inside_ownership_guard(self):
        with mock.patch.object(process.subprocess,'Popen',side_effect=self.spawned),mock.patch.object(process.time,'monotonic',side_effect=OSError('PRIVATE_CLOCK_CANARY')),mock.patch.object(process.os,'killpg',side_effect=self.safe_kill):
            with self.assertRaises(ValueError):self.execute('import time;time.sleep(30)')
        self.assert_clean()
    def test_input_close_after_release_is_not_retried_and_other_pipe_closes(self):
        calls=[]
        class Proxy:
            def __init__(self,stream):self.stream=stream
            def __getattr__(self,name):return getattr(self.stream,name)
            def close(self):calls.append('input');self.stream.close();raise OSError('PRIVATE_CLOSE_CANARY')
        def spawn(*args,**kwargs):
            child=self.spawned(*args,**kwargs);child.stdin=Proxy(child.stdin);return child
        with mock.patch.object(process.subprocess,'Popen',side_effect=spawn),mock.patch.object(process.os,'killpg',side_effect=self.safe_kill):
            with self.assertRaises(ValueError):self.execute('import time;time.sleep(30)')
        self.assertEqual(calls,['input']);self.assert_clean()
    def test_selector_close_failure_attempts_pipes_without_reaped_signal(self):
        original=process.selectors.DefaultSelector;signals=[]
        class Proxy:
            def __init__(self):self.selector=original()
            def __getattr__(self,name):return getattr(self.selector,name)
            def close(self):self.selector.close();raise OSError('PRIVATE_SELECTOR_CLOSE_CANARY')
        with mock.patch.object(process.subprocess,'Popen',side_effect=self.spawned),mock.patch.object(process.selectors,'DefaultSelector',Proxy),mock.patch.object(process.os,'killpg',side_effect=lambda *args:signals.append(args)):
            with self.assertRaises(ValueError):self.execute('print("OWNED")')
        self.assertEqual(signals,[]);self.assert_clean()
    def test_actual_output_and_deadline_bounds_cleanup_owned_child(self):
        for code,timeout,limit in [('print("x"*4097)',2,4096),('import time;time.sleep(30)',.05,4096)]:
            with mock.patch.object(process.subprocess,'Popen',side_effect=self.spawned),mock.patch.object(process.os,'killpg',side_effect=self.safe_kill):
                with self.assertRaises(ValueError):self.execute(code,timeout=timeout,limit=limit)
        self.assert_clean()

if __name__=='__main__':unittest.main()
