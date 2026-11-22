"""Artifact-only bounded child supervision; no signal after an owned child is reaped.

Adapted from scripts/worker_process.py at40d85df. Budgets stay60seconds/2MB
stdout/1MBinput. Selector construction is within the ownership guard. A close
attempt relinquishes that object before calling it, so later cleanup does not
retry a possibly released descriptor number. Every other owned handle is tried.
"""
import math
import os
import selectors
import signal
import subprocess
import time


class ArtifactProcessError(ValueError):pass


def run_worker(argv,*,input,timeout,output_limit):
    if(os.name!='posix'or type(argv)is not list or not argv
       or any(type(v)is not str or not v or '\0'in v for v in argv)
       or type(input)is not bytes or len(input)>1_000_000
       or type(timeout)not in(int,float)or not math.isfinite(timeout)or not 0<timeout<=60
       or type(output_limit)is not int or not 0<output_limit<=2_000_000):
        raise ArtifactProcessError('Artifact subprocess unavailable.')
    child=None;selector=None;owned={'input':True,'output':True};cleanup_error=None
    def close_pipe(key):
        if owned[key]:
            owned[key]=False
            stream=child.stdin if key=='input'else child.stdout
            if stream is not None:stream.close()
    try:
        child=subprocess.Popen(argv,stdin=subprocess.PIPE,stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,bufsize=0,start_new_session=True,close_fds=True)
        selector=selectors.DefaultSelector()
        os.set_blocking(child.stdin.fileno(),False);os.set_blocking(child.stdout.fileno(),False)
        selector.register(child.stdout,selectors.EVENT_READ,'output')
        if input:selector.register(child.stdin,selectors.EVENT_WRITE,'input')
        else:close_pipe('input')
        offset=0;output=bytearray();deadline=time.monotonic()+timeout;eof=False
        while not eof:
            remaining=deadline-time.monotonic()
            if remaining<=0:raise ArtifactProcessError('Artifact subprocess unavailable.')
            for key,_ in selector.select(min(remaining,.1)):
                if key.data=='input':
                    try:offset+=os.write(key.fileobj.fileno(),input[offset:offset+65536])
                    except BlockingIOError:continue
                    except BrokenPipeError:offset=len(input)
                    if offset==len(input):selector.unregister(key.fileobj);close_pipe('input')
                else:
                    try:raw=os.read(key.fileobj.fileno(),min(65536,output_limit-len(output)+1))
                    except BlockingIOError:continue
                    if not raw:selector.unregister(key.fileobj);eof=True;break
                    if len(raw)>output_limit-len(output):raise ArtifactProcessError('Artifact subprocess unavailable.')
                    output.extend(raw)
        remaining=deadline-time.monotonic()
        if remaining<=0:raise ArtifactProcessError('Artifact subprocess unavailable.')
        code=child.wait(timeout=remaining)
        return subprocess.CompletedProcess(argv,code,bytes(output),b'')
    except Exception:
        raise ArtifactProcessError('Artifact subprocess unavailable.')from None
    finally:
        # No poll()/wait() before this test: an unreaped owned leader reserves its
        # process-group ID. If wait already reaped it, that numeric ID is released
        # and MUST NOT be targeted even when a later exception interrupted return.
        if child is not None and child.returncode is None:
            try:os.killpg(child.pid,signal.SIGKILL)
            except ProcessLookupError:pass
            except BaseException as failure:cleanup_error=failure
            try:child.wait(timeout=5)
            except BaseException as failure:
                if cleanup_error is None:cleanup_error=failure
        if selector is not None:
            try:selector.close()
            except BaseException as failure:
                if cleanup_error is None:cleanup_error=failure
        for key in ('input','output'):
            try:
                if child is not None:close_pipe(key)
            except BaseException as failure:
                if cleanup_error is None:cleanup_error=failure
        if cleanup_error is not None:raise ArtifactProcessError('Artifact subprocess cleanup unavailable.')from None
