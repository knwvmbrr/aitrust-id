"""Own one JPEG-native process group: bounded pipes, no path/credential forwarding."""
import os
import math
import selectors
import signal
import subprocess
import time
from tools.jpeg_provenance_io import Refused, need

MAX_REQUEST = 10*1024*1024+65536+4096
MAX_REPORT = 4*1024*1024


def run(argv, raw, *, timeout=12, limit=MAX_REPORT):
    need(type(raw) is bytes and len(raw) <= MAX_REQUEST
         and type(timeout) in (int, float) and math.isfinite(timeout) and 0 < timeout <= 12
         and type(limit) is int and 0 < limit <= MAX_REPORT
         and type(argv) is list and 1 <= len(argv) <= 8
         and all(type(a) is str and 0 < len(a) <= 4096 and '\0' not in a for a in argv))
    # Initialize everything that can fail before taking child ownership.
    selector = None
    output, offset, complete = bytearray(), 0, False
    deadline = time.monotonic()+timeout
    environment = {'PATH': os.defpath, 'LANG': 'C.UTF-8', 'PYTHONDONTWRITEBYTECODE': '1'}
    child = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL, env=environment, start_new_session=True, close_fds=True, bufsize=0, cwd='/')
    try:
        selector = selectors.DefaultSelector()
        os.set_blocking(child.stdin.fileno(), False)
        os.set_blocking(child.stdout.fileno(), False)
        selector.register(child.stdout, selectors.EVENT_READ, 'output')
        if raw:
            selector.register(child.stdin, selectors.EVENT_WRITE, 'input')
        else:
            child.stdin.close()
        eof = False
        while not eof:
            remaining = deadline-time.monotonic()
            need(remaining > 0, 'worker_deadline')
            for key, _ in selector.select(min(remaining, .1)):
                if key.data == 'input':
                    try:
                        offset += os.write(key.fd, memoryview(raw)[offset:offset+65536])
                    except BlockingIOError:
                        continue
                    except BrokenPipeError:
                        offset = len(raw)
                    if offset == len(raw):
                        selector.unregister(key.fileobj)
                        key.fileobj.close()
                else:
                    try:
                        block = os.read(key.fd, min(65536, limit-len(output)+1))
                    except BlockingIOError:
                        continue
                    if not block:
                        selector.unregister(key.fileobj)
                        eof = True
                        break
                    need(len(block) <= limit-len(output), 'worker_output_limit')
                    output.extend(block)
        remaining = deadline-time.monotonic()
        need(remaining > 0, 'worker_deadline')
        code = child.wait(timeout=remaining)
        complete = True
        need(time.monotonic() <= deadline, 'worker_deadline')
        need(code == 0, 'worker_unavailable')
        return bytes(output)
    finally:
        try:
            # A wait fault may happen after the child was actually reaped.
            if not complete and child.returncode is None:
                try:
                    try:
                        os.killpg(child.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                finally:
                    child.wait(timeout=5)
        finally:
            try:
                if selector is not None:
                    selector.close()
            finally:
                try:
                    child.stdin.close()
                finally:
                    child.stdout.close()
