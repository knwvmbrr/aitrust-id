#!/usr/bin/env python3
"""Inspect/package an observed static web artifact or privately verify a managed release."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools import web_checker_artifact as web


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation',choices=('sources','prepare','inspect','managed'))
    parser.add_argument('--source-commit')
    parser.add_argument('--directory',type=Path)
    parser.add_argument('--artifact',type=Path)
    parser.add_argument('--destination',type=Path)
    parser.add_argument('--packet',type=Path)
    parser.add_argument('--spdx',type=Path)
    parser.add_argument('--bundle',type=Path)
    parser.add_argument('--trusted-roots',type=Path)
    args=parser.parse_args()
    try:
        if args.operation=='sources':
            web.need(all(v is None for k,v in vars(args).items()if k!='operation'))
            result=web.verify_sources()
        else:
            web.need(args.source_commit is not None)
            if args.operation=='prepare':
                web.need(args.directory is not None and args.destination is not None and all(getattr(args,k)is None for k in ('artifact','packet','spdx','bundle','trusted_roots')))
                result=web.prepare(args.directory,args.destination,args.source_commit)
            elif args.operation=='inspect':
                web.need(args.artifact is not None and all(getattr(args,k)is None for k in ('directory','destination','packet','spdx','bundle','trusted_roots')))
                result=web.inspect(args.artifact,args.source_commit)
            else:
                web.need(args.directory is None and all(getattr(args,k)is not None for k in ('artifact','destination','packet','spdx','bundle','trusted_roots')))
                result=web.verify_managed(args.artifact,args.packet,args.spdx,args.bundle,args.trusted_roots,args.destination,args.source_commit)
        result['captured_at']=datetime.now(timezone.utc).isoformat()
        print(json.dumps(result,sort_keys=True,separators=(',',':')));return 0
    except web.WebOutputUncertain:
        print(json.dumps({'pass':False,'status':'Unavailable','output_may_exist':True,
          'diagnostic':'Private web output may exist; inspect before retrying.'}));return 2
    except BaseException:
        print(json.dumps({'pass':False,'status':'Unavailable','diagnostic':'Selected web artifact unavailable.'}));return 2


if __name__=='__main__':raise SystemExit(main())
