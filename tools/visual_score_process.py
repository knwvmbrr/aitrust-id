"""Owned bounded pipe worker. Never signals an already reaped numeric group."""
import math
import os
import selectors
import signal
import subprocess
import time
from tools.visual_score_assets import Refused,need
MAX_REPORT=16384

def run(argv,input,timeout=150):
 need(type(argv)is list and argv and all(type(x)is str and x and '\0' not in x for x in argv),'invalid_request')
 need(type(input)is bytes and len(input)<=10*1024*1024+8192 and type(timeout)in(int,float) and math.isfinite(timeout) and 0<timeout<=150,'invalid_request')
 selector=None;complete=False;output=bytearray();offset=0;deadline=time.monotonic()+timeout
 child=subprocess.Popen(argv,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,bufsize=0,start_new_session=True,close_fds=True,
  env={k:v for k,v in os.environ.items() if k in ('PATH','SYSTEMROOT')}|{'PYTHONDONTWRITEBYTECODE':'1','HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1','HF_HUB_DISABLE_TELEMETRY':'1','DO_NOT_TRACK':'1','CUDA_VISIBLE_DEVICES':'','OMP_NUM_THREADS':'1','MKL_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1'})
 try:
  selector=selectors.DefaultSelector();os.set_blocking(child.stdin.fileno(),False);os.set_blocking(child.stdout.fileno(),False);selector.register(child.stdout,selectors.EVENT_READ,'output')
  if input:selector.register(child.stdin,selectors.EVENT_WRITE,'input')
  else:child.stdin.close()
  eof=False
  while not eof:
   remaining=deadline-time.monotonic();need(remaining>0,'deadline')
   for key,_ in selector.select(min(.1,remaining)):
    if key.data=='input':
     try:offset+=os.write(key.fileobj.fileno(),memoryview(input)[offset:offset+65536])
     except BlockingIOError:continue
     except BrokenPipeError:offset=len(input)
     if offset==len(input):selector.unregister(key.fileobj);key.fileobj.close()
    else:
     try:chunk=os.read(key.fileobj.fileno(),min(65536,MAX_REPORT-len(output)+1))
     except BlockingIOError:continue
     if not chunk:selector.unregister(key.fileobj);eof=True;break
     need(len(chunk)<=MAX_REPORT-len(output),'output_limit');output.extend(chunk)
  remaining=deadline-time.monotonic();need(remaining>0,'deadline');code=child.wait(timeout=remaining);complete=True
  need(code==0,'worker_unavailable');return bytes(output)
 except subprocess.TimeoutExpired:raise Refused('deadline') from None
 finally:
  try:
   if not complete and child.returncode is None:
    try:os.killpg(child.pid,signal.SIGKILL)
    except ProcessLookupError:pass
    finally:child.wait(timeout=5)
  finally:
   try:
    if selector is not None:selector.close()
   finally:
    try:child.stdin.close()
    finally:child.stdout.close()
