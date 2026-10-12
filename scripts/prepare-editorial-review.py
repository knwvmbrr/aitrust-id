#!/usr/bin/env python3
"""Owner-private editorial review; no network or detector execution."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.editorial_cli import prepare
if __name__ == '__main__':
    raise SystemExit(prepare(sys.argv[1:], ROOT))
