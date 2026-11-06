"""Foreground owner-selected text capture. No network, original edits or daemon."""
from contextlib import contextmanager, nullcontext
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import selectors
import signal
import stat
import subprocess
import sys
import tempfile
import time
import uuid

from tools.blind_review_io import directory, member, create
from protocol.normalization import normalize_nfc, NORMALIZATION_ID

ROOT=Path(__file__).resolve().parents[1]
CORE_SOURCES=('tools/host_capture.py','scripts/host-capture.py','tools/blind_review_io.py',
 'protocol/normalization.py','protocol/unicode15-data.json')
PS_SOURCES=('scripts/build-device-detector.py','scripts/check-ps.py','scripts/worker_process.py',
 'services/evaluator/app.py')
MAX_BYTES=80000
MAX_CHARS=20000
MAX_RECORD=2_000_000
SENSITIVE={'.ssh','.gnupg','.aws','.azure','.kube','.git','library','.mozilla','.password-store','.config'}


def require(ok):
    if not ok:raise ValueError('Host capture contract refused')


def encode(value):
    return json.dumps(value,ensure_ascii=True,sort_keys=True,allow_nan=False,separators=(',',':')).encode()


def sha(value):return hashlib.sha256(value).hexdigest()
def utc():return datetime.now(timezone.utc).isoformat()


def fingerprint(tag=None):
    require(tag in (None,'PS'));files={}
    for name in CORE_SOURCES+(PS_SOURCES if tag else ()):
        path=ROOT/name
        fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
        with os.fdopen(fd,'rb') as stream:
            before=os.fstat(stream.fileno())
            require(stat.S_ISREG(before.st_mode) and before.st_size<=2_000_000)
            raw=stream.read(2_000_001);after=os.fstat(stream.fileno())
            require(len(raw)<=2_000_000 and (before.st_size,before.st_mtime_ns,before.st_ctime_ns)==
                    (after.st_size,after.st_mtime_ns,after.st_ctime_ns))
            files[name]=sha(raw)
    return {'format':'ai-trust-id-host-source/v1','analysis':tag,'files':files,'sha256':sha(encode({'analysis':tag,'files':files}))}


def load_script(name):
    path=ROOT/'scripts'/name
    spec=importlib.util.spec_from_file_location('host_'+name.replace('.','_'),path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


class ForegroundLost(BaseException):
    pass


class SourceGuard:
    def __init__(self,expected,tag=None):
        self.tag=tag
        require(type(expected) is str and re.fullmatch(r'[a-f0-9]{64}',expected))
        self.identity=fingerprint(tag);require(self.identity['sha256']==expected)
    def check(self):require(fingerprint(self.tag)==self.identity)


class FileScope:
    def __init__(self,path,name):
        self.path=Path(path).expanduser().absolute()
        require(type(name) is str and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}[.]txt',name))
        resolved=self.path.resolve(strict=True)
        require(not any(p.lower() in SENSITIVE for p in resolved.parts))
        require(not any((p/'.git').exists() for p in (resolved,*resolved.parents)))
        self.context=directory(self.path,ROOT);self.fd=self.context.__enter__()
        self.identity=self._identity(os.fstat(self.fd));self.name=name
    @staticmethod
    def _identity(info):return info.st_dev,info.st_ino
    def check(self):
        info=self.path.stat(follow_symlinks=False)
        require(stat.S_ISDIR(info.st_mode) and info.st_uid==os.getuid() and not info.st_mode&0o077
                and self._identity(info)==self.identity==self._identity(os.fstat(self.fd)))
    def snapshot(self):
        self.check();raw=member(self.fd,self.name,MAX_BYTES);self.check()
        text=raw.decode('utf-8','strict')
        require(text.strip() and len(text)<=MAX_CHARS and not any(ord(c)<32 and c not in '\n\r\t' for c in text))
        normalized=normalize_nfc(text)
        require(len(normalized)<=MAX_CHARS)
        return {'raw_sha256':sha(raw),'sha256':sha(normalized.encode()),'codepoint_count':len(normalized),
                'byte_count':len(raw),'normalization':NORMALIZATION_ID},text
    def close(self):self.context.__exit__(None,None,None)
    def __enter__(self):return self
    def __exit__(self,*args):self.close()


class Journal:
    """Optional owner-requested metadata. Delete only verified generated members."""
    def __init__(self,path,header):
        self.path=Path(path).expanduser().absolute();self.owned={};self.seq=0;self.bytes=0
        parent=self.path.parent.resolve(strict=True)
        require(not any((p/'.git').exists() for p in (parent,*parent.parents)))
        raw=encode(header)+b'\n';create(self.path,ROOT,{'session.json':raw})
        self.context=directory(self.path,ROOT);self.fd=self.context.__enter__()
        self.identity=(os.fstat(self.fd).st_dev,os.fstat(self.fd).st_ino)
        self._remember('session.json',raw)
    def _remember(self,name,raw):
        info=os.stat(name,dir_fd=self.fd,follow_symlinks=False)
        self.owned[name]=((info.st_dev,info.st_ino),sha(raw));self.bytes+=len(raw)
    def check(self):
        info=self.path.stat(follow_symlinks=False)
        require(stat.S_ISDIR(info.st_mode) and info.st_uid==os.getuid() and not info.st_mode&0o077
                and (info.st_dev,info.st_ino)==self.identity)
        require(set(os.listdir(self.fd))==set(self.owned))
    def append(self,row):
        self.check();raw=encode(row)+b'\n'
        require(len(raw)<=MAX_RECORD and len(self.owned)<1001 and self.bytes+len(raw)<=20_000_000)
        self.seq+=1;name='event-'+str(self.seq).zfill(8)+'.json'
        fd=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=self.fd)
        try:
            with os.fdopen(fd,'wb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
            self._remember(name,raw);os.fsync(self.fd)
        except BaseException:
            # Preserve a failed write for explicit operator review; never claim deletion.
            raise
    def purge(self,all_records=False):
        self.check()
        for name,(identity,expected) in self.owned.items():
            info=os.stat(name,dir_fd=self.fd,follow_symlinks=False)
            require((info.st_dev,info.st_ino)==identity and sha(member(self.fd,name,MAX_RECORD))==expected)
        for name in list(self.owned):
            if name=='session.json' and not all_records:continue
            info=os.stat(name,dir_fd=self.fd,follow_symlinks=False);require((info.st_dev,info.st_ino)==self.owned[name][0])
            os.unlink(name,dir_fd=self.fd);del self.owned[name]
        self.bytes=sum(os.stat(name,dir_fd=self.fd,follow_symlinks=False).st_size for name in self.owned)
        os.fsync(self.fd)
        if all_records:
            require(not os.listdir(self.fd));self.context.__exit__(None,None,None);self.fd=None
            # rmdir refuses nonempty substitutions; no recursive deletion.
            require((self.path.stat(follow_symlinks=False).st_dev,self.path.stat(follow_symlinks=False).st_ino)==self.identity)
            self.path.rmdir()
    def close(self):
        if self.fd is not None:self.context.__exit__(None,None,None);self.fd=None


class Worker:
    """One frozen PS projection, no grandchild processes or content files."""
    def __init__(self,script,text):
        self.process=subprocess.Popen([sys.executable,'-I','-S','-B',str(script),str(os.getpid())],stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,bufsize=0,start_new_session=True,close_fds=True,env={'LANG':'C.UTF-8'})
        self.selector=selectors.DefaultSelector();self.output=bytearray();self.input=text.encode();self.offset=0
        self.deadline=time.monotonic()+12;self.done=False;self.eof=False
        try:
            for pipe in (self.process.stdin,self.process.stdout):os.set_blocking(pipe.fileno(),False)
            self.selector.register(self.process.stdin,selectors.EVENT_WRITE,'input')
            self.selector.register(self.process.stdout,selectors.EVENT_READ,'output')
        except BaseException:self.close();raise
    def step(self):
        require(time.monotonic()<self.deadline)
        for key,_ in self.selector.select(0):
            if key.data=='input':
                try:self.offset+=os.write(key.fileobj.fileno(),memoryview(self.input)[self.offset:self.offset+65536])
                except BlockingIOError:continue
                except BrokenPipeError:self.offset=len(self.input)
                if self.offset==len(self.input):self.selector.unregister(key.fileobj);key.fileobj.close();self.input=b''
            else:
                try:chunk=os.read(key.fileobj.fileno(),min(65536,MAX_RECORD-len(self.output)+1))
                except BlockingIOError:continue
                require(len(chunk)<=MAX_RECORD-len(self.output));self.output.extend(chunk)
                if not chunk:self.selector.unregister(key.fileobj);self.eof=True
        if not self.eof:return None
        try:code=self.process.wait(timeout=.001)
        except subprocess.TimeoutExpired:return None
        self.done=True;require(code==0)
        return bytes(self.output)
    def close(self):
        # Do not reap a failed leader before signaling its reserved process-group ID.
        if not self.done:
            try:os.killpg(self.process.pid,signal.SIGKILL)
            except ProcessLookupError:pass
            except PermissionError:
                # macOS may deny signaling an already-exited reserved group.
                # This worker has no descendants; retain the Popen child handle
                # and stop/wait that exact child, never an unrelated process.
                self.process.kill()
            self.process.wait(timeout=5)
        self.selector.close()
        for pipe in (self.process.stdin,self.process.stdout):pipe.close()
        self.input=b'';self.output.clear()


@contextmanager
def frozen_worker(guard):
    guard.check();project=load_script('build-device-detector.py').project
    raw=(ROOT/'services/evaluator/app.py').read_bytes();bundle,_=project(raw)
    guard.check()
    # The child has no descendants. A parent-death watcher also bounds orphan work
    # after SIGKILL/power-independent parent loss; no automatic restart exists.
    driver=b'''
import sys,os,threading,time
parent=int(sys.argv[1])
if os.getppid()!=parent:os._exit(125)
def watch_parent():
    while True:
        if os.getppid()!=parent:os._exit(125)
        time.sleep(.1)
threading.Thread(target=watch_parent,daemon=True).start()
raw=sys.stdin.buffer.read(80001)
if len(raw)>80000:raise ValueError('Input too large')
print(check_device(raw.decode('utf-8')))
'''
    with tempfile.TemporaryDirectory(prefix='aitrust-host-code-') as name:
        directory_path=Path(name);directory_path.chmod(0o700);script=directory_path/'worker.py'
        fd=os.open(script,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o400)
        with os.fdopen(fd,'wb') as stream:stream.write(bundle+driver)
        yield script,sha(bundle+driver)


def foreground(stdin,stdout):
    require(sys.platform in {'darwin','linux'} and stdin.isatty() and stdout.isatty())
    require(os.tcgetpgrp(stdin.fileno())==os.getpgrp())


@contextmanager
def interrupt_cleanup(stdin,stdout):
    """Job control cannot resume a blocked terminal read behind the shell."""
    prior={sig:signal.getsignal(sig) for sig in
           (signal.SIGTERM,signal.SIGHUP,signal.SIGTSTP,signal.SIGTTIN,signal.SIGTTOU,signal.SIGCONT)}
    def stop(signum,frame):raise KeyboardInterrupt
    def lost(signum,frame):raise ForegroundLost
    def continued(signum,frame):
        try:foreground(stdin,stdout)
        except (OSError,ValueError):raise ForegroundLost from None
    try:
        for sig in prior:signal.signal(sig,continued if sig==signal.SIGCONT else
                                        lost if sig in (signal.SIGTTIN,signal.SIGTTOU) else stop)
        yield
    finally:
        for sig,handler in prior.items():signal.signal(sig,handler)


def run(root,name,expected,*,consent,tag=None,record_dir=None,stdin=sys.stdin,stdout=sys.stdout):
    require(consent is True and tag in (None,'PS'));foreground(stdin,stdout)
    guard=SourceGuard(expected,tag);scope=None;journal=None;worker=None
    selector=selectors.DefaultSelector()
    epoch=0;revision=0;last=None;pending=None;paused=False;running=True
    next_scan=0;next_guard=0;last_status=None;commands=bytearray()
    session=str(uuid.uuid4());validator=load_script('check-ps.py').validate if tag else None
    def say(message):print(message,file=stdout,flush=True)
    def record(action,**fields):
        # A full/failed journal stops this foreground session, rather than claiming
        # events were retained or repeatedly attempting a failed write.
        if journal:journal.append({'format':'ai-trust-id-host-event/v1','session_id':session,'epoch':epoch,
            'revision':revision,'at':utc(),'action':action,'source_sha256':expected,
            'text_included':False,'automatic_upload':False,'independently_validated':False,**fields})
    def cancel():
        nonlocal worker,pending
        if worker:worker.close();worker=None
        pending=None
    try:
        scope=FileScope(root,name)
        if record_dir:journal=Journal(record_dir,{'format':'ai-trust-id-host-session/v1','session_id':session,'started_at':utc(),
            'source_sha256':expected,'scope':'one_private_text_file','analysis':tag,'text_included':False,'upload_enabled':False})
        selector.register(stdin.fileno(),selectors.EVENT_READ)
        context=frozen_worker(guard) if tag else nullcontext((None,None))
        with interrupt_cleanup(stdin,stdout),context as (script,script_hash):
            record('start');say('HOST ACTIVE · one approved local text file · nothing uploaded')
            say('p: pause | c: continue | r: reset and pause | d: delete records and stop | q: stop')
            if tag:say('PS development check selected. No redaction or independent accuracy validation.')
            while running:
                try:foreground(stdin,stdout)
                except (OSError,ValueError):
                    cancel();record('interrupted',reason='foreground_ownership_lost')
                    say('HOST UNAVAILABLE · foreground terminal ownership lost; start a new visible session');return 2
                # Read bounded command bytes directly; buffered readline can hide
                # queued commands from select and can block on an incomplete line.
                for _,_ in selector.select(.02):
                    chunk=os.read(stdin.fileno(),256)
                    if not chunk:running=False;break
                    commands.extend(chunk)
                    require(len(commands)<=512)
                while b'\n' in commands and running:
                    line,_,remainder=commands.partition(b'\n');commands[:]=remainder
                    command=bytes(line).strip().lower()
                    if command==b'p':
                        epoch+=1;paused=True;cancel();record('pause');say('HOST PAUSED · no file reads or analysis')
                    elif command==b'c':
                        guard.check();scope.check();epoch+=1;paused=False;last=None;last_status=None
                        record('resume');say('HOST ACTIVE · fresh capture required')
                    elif command==b'r':
                        epoch+=1;paused=True;cancel();last=None;last_status=None
                        if journal:journal.purge()
                        record('reset');say('HOST RESET · records cleared · paused')
                    elif command==b'd':
                        epoch+=1;paused=True;cancel()
                        if journal:journal.purge(all_records=True)
                        running=False;say('HOST DELETED · captured records removed · stopped')
                    elif command==b'q':running=False
                    else:say('Use p, c, r, d or q, then Return.')
                if not running:break
                now=time.monotonic()
                if now>=next_guard:
                    next_guard=now+.5
                    try:guard.check()
                    except Exception:
                        cancel();record('interrupted',reason='source_version_changed')
                        say('HOST UNAVAILABLE · source version changed; stop, verify the update and restart');return 2
                if paused:continue
                if now>=next_scan:
                    next_scan=now+.25
                    try:
                        foreground(stdin,stdout);snapshot,text=scope.snapshot()
                    except (OSError,ValueError,UnicodeError):
                        cancel();last=None
                        if last_status!='unavailable':
                            record('unavailable',reason='selected_file_unavailable')
                            say('HOST UNAVAILABLE · selected file is outside the accepted read contract')
                        last_status='unavailable';continue
                    if snapshot['raw_sha256']!=last:
                        cancel();revision+=1;last=snapshot['raw_sha256'];last_status='captured'
                        record('captured',subject=snapshot);say('HOST CAPTURED · revision '+str(revision))
                        if tag:
                            require(sha(script.read_bytes())==script_hash)
                            worker=Worker(script,text);pending=(epoch,revision,snapshot,text)
                        text=None
                if worker:
                    completed=False
                    try:
                        raw=worker.step()
                        if raw is None:continue
                        completed=True
                        row=json.loads(raw);active_epoch,active_revision,snapshot,text=pending
                        require((active_epoch,active_revision)==(epoch,revision))
                        foreground(stdin,stdout);current,_=scope.snapshot();require(current==snapshot)
                        guard.check();row=validator(row,text);foreground(stdin,stdout)
                    except (OSError,ValueError,UnicodeError,RuntimeError,subprocess.SubprocessError):
                        completed=True
                        record('analysis_unavailable',code='PS')
                        say('PS UNAVAILABLE · capture and other checker routes remain separate')
                    else:
                        record('result',code='PS',state=row['state'],subject=snapshot,result=row)
                        say('PS FINDING · supported command pattern; review before running' if row['state']=='FINDING'
                            else 'PS NO FINDING · not a safety clearance')
                    finally:
                        if completed:cancel()
            cancel()
            if journal and journal.fd is not None:record('stop')
            say('HOST STOPPED · input file unchanged');return 0
    except ForegroundLost:
        cancel();record('interrupted',reason='foreground_ownership_lost')
        say('HOST UNAVAILABLE · foreground terminal ownership lost; start a new visible session');return 2
    finally:
        cancel();selector.close()
        if journal:journal.close()
        if scope:scope.close()
