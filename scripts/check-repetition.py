"""Read bounded private UTF-8 stdin and print an observation; no upload or tag."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import json
from protocol.repetition import inspect

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--n',type=int,default=3);args=parser.parse_args()
    try:
        raw=sys.stdin.buffer.read(80001)
        if len(raw)>80000:raise ValueError('Input too large')
        result=inspect(raw.decode('utf-8'),n=args.n)
    except (ValueError,UnicodeError):
        print('Input or configuration unsupported; no finding issued.',file=sys.stderr);sys.exit(2)
    print(json.dumps(result,ensure_ascii=False,allow_nan=False))
