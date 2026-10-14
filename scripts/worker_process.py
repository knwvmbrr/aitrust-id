"""Bounded Linux/macOS pipe supervision. No shell, content files or stderr capture."""
import math
import os
import selectors
import signal
import subprocess
import time


class WorkerOutputLimit(RuntimeError):
    pass


def run_worker(argv,*,input,timeout,output_limit):
    if (os.name!='posix' or not isinstance(argv,list) or not argv
            or any(not isinstance(v,str) or not v or '\0' in v for v in argv)
            or not isinstance(input,bytes) or len(input)>1_000_000
            or type(timeout) not in (int,float) or not math.isfinite(timeout) or not 0<timeout<=60
            or type(output_limit) is not int or not 0<output_limit<=2_000_000):
        raise ValueError('Unsupported bounded worker request')
    child=subprocess.Popen(argv,stdin=subprocess.PIPE,stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,bufsize=0,start_new_session=True,close_fds=True)
    selector=selectors.DefaultSelector();complete=False
    output=bytearray();offset=0;deadline=time.monotonic()+timeout
    try:
        os.set_blocking(child.stdin.fileno(),False);os.set_blocking(child.stdout.fileno(),False)
        selector.register(child.stdout,selectors.EVENT_READ,'output')
        if input:selector.register(child.stdin,selectors.EVENT_WRITE,'input')
        else:child.stdin.close()
        eof=False
        while not eof:
            remaining=deadline-time.monotonic()
            if remaining<=0:raise subprocess.TimeoutExpired(argv,timeout)
            for key,_ in selector.select(min(remaining,.1)):
                if key.data=='input':
                    try:offset+=os.write(key.fileobj.fileno(),memoryview(input)[offset:offset+65536])
                    except BlockingIOError:continue
                    except BrokenPipeError:offset=len(input)
                    if offset==len(input):selector.unregister(key.fileobj);key.fileobj.close()
                else:
                    try:chunk=os.read(key.fileobj.fileno(),min(65536,output_limit-len(output)+1))
                    except BlockingIOError:continue
                    if not chunk:
                        selector.unregister(key.fileobj);eof=True;break
                    if len(chunk)>output_limit-len(output):
                        raise WorkerOutputLimit('Selected worker exceeded its output budget')
                    output.extend(chunk)
        remaining=deadline-time.monotonic()
        if remaining<=0:raise subprocess.TimeoutExpired(argv,timeout)
        code=child.wait(timeout=remaining)
        complete=True
        return subprocess.CompletedProcess(argv,code,bytes(output),b'')
    finally:
        # Do not poll/reap before signaling a failed group: its unreaped leader
        # reserves the ID so an unrelated reused PID cannot be targeted.
        if not complete:
            try:os.killpg(child.pid,signal.SIGKILL)
            except ProcessLookupError:pass
            child.wait(timeout=5)
        selector.close()
        child.stdin.close();child.stdout.close()
