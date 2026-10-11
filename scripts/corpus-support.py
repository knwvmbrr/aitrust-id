#!/usr/bin/env python3
"""Read a private query from standard input; emit metadata, never reference text."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from protocol import corpus,corpus_support


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--corpus',type=Path,required=True)
    p.add_argument('--threshold',type=float,default=.75)
    p.add_argument('--maximum',type=int,default=10)
    a=p.parse_args(argv)
    try:
        record=corpus.load(a.corpus)
        result=corpus_support.observe(record,sys.stdin.read(2001),a.threshold,a.maximum)
        print(json.dumps(result,ensure_ascii=True,indent=2));return 0
    except (corpus.CorpusError,OSError,UnicodeError):
        print(json.dumps({'state':'UNAVAILABLE','reason':'invalid_or_unsupported_subject_reference_or_parameters','tags':[],'truth_established':False}));return 2

if __name__=='__main__':raise SystemExit(main())
