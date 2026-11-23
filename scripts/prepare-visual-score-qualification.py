#!/usr/bin/env python3
"""Explicit qualification operator only; public inference never calls this downloader."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools.visual_score_qualification import main,QualificationRefused,CleanupUncertain
if __name__=='__main__':
 try:main()
 except CleanupUncertain:print('{"pass":false,"reason":"cleanup_uncertain","private_bytes_may_remain":true}');raise SystemExit(2)
 except Exception:print('{"pass":false,"reason":"qualification_refused"}');raise SystemExit(2)
