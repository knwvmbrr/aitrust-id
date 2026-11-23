#!/usr/bin/env python3
"""Optional bounded CPU image-score reference; never a tag issuer."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.visual_score import main,worker,unavailable
from tools.visual_score_assets import Refused
if __name__=='__main__':
 if sys.argv[1:]==['--worker']:
  try:worker()
  except Refused as error:
   import json
   print(json.dumps(unavailable(error.reason),allow_nan=False,separators=(',',':')))
  except Exception:
   import json
   print(json.dumps(unavailable('worker_unavailable'),allow_nan=False,separators=(',',':')))
 else:
  import signal
  def interrupted(signum,frame):raise KeyboardInterrupt
  previous=signal.signal(signal.SIGTERM,interrupted)
  try:
   try:code=main()
   except KeyboardInterrupt:
    if '--json' in sys.argv[1:]:
     import json
     print(json.dumps(unavailable('cancelled'),allow_nan=False,separators=(',',':')))
    else:print('IMAGE SCORE UNAVAILABLE: cancelled. No origin conclusion or tag.')
    code=2
  finally:signal.signal(signal.SIGTERM,previous)
  raise SystemExit(code)
