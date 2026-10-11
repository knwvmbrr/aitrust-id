#!/usr/bin/env python3
"""Inspect explicitly selected Python source from stdin; never execute it."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from protocol.corpus import CorpusError
from tools import credential_flow


def main():
    try:
        result = credential_flow.observe(sys.stdin.read(credential_flow.MAX_CHARACTERS+1))
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0
    except (CorpusError, UnicodeError, RecursionError):
        print(json.dumps({'state': 'UNAVAILABLE', 'reason': 'invalid_or_unsupported_python_flow', 'tags': [], 'subject_executed': False}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
