#!/usr/bin/env python3
"""Offline exact selected embedded-zlib source/notice delivery."""
import argparse
import json
from pathlib import Path
import sys
import tarfile
import zlib
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
try:
    from tools import zlib_source_delivery as delivery
except (ImportError,OSError):
    print('{"pass":false,"reason":"zlib_source_notice_unavailable"}');raise SystemExit(2)

class Parser(argparse.ArgumentParser):
    def error(self,message):raise delivery.DeliveryError('Zlib source command refused')

def main(argv=None):
    parser=Parser();group=parser.add_mutually_exclusive_group()
    group.add_argument('--export');group.add_argument('--check-built');group.add_argument('--replay-cache')
    try:
        args=parser.parse_args(argv)
        if args.export:
            raw=delivery.export(args.export);result={'pass':True,'artifacts':{n:{'bytes':len(v),'sha256':delivery.sha(v)} for n,v in raw.items()},**delivery.CLAIMS}
        elif args.check_built:result=delivery.check_built(args.check_built)
        elif args.replay_cache:
            value,_=delivery.replay_cached(args.replay_cache);delivery.need(delivery.canonical(value)==delivery.canonical(delivery.checked()[0]));result={'pass':True,'cached_archives_replayed':2,'zlib_version':delivery.VERSION,**delivery.CLAIMS}
        else:
            delivery.checked();result={'pass':True,'zlib_version':delivery.VERSION,**delivery.CLAIMS}
        print(json.dumps(result));return 0
    except delivery.OutputUncertain:
        print('{"pass":false,"reason":"output_commit_uncertain","output_may_exist":true}');return 2
    except (OSError,ValueError,TypeError,KeyError,RecursionError,UnicodeError,EOFError,tarfile.TarError,zlib.error,OverflowError):
        print('{"pass":false,"reason":"zlib_source_notice_unavailable"}');return 2
if __name__=='__main__':raise SystemExit(main())
