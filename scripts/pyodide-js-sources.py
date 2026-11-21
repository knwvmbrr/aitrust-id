#!/usr/bin/env python3
"""Offline selected runtime source/notice exporter and actual artifact gate."""
import argparse
import json
from pathlib import Path
import sys
import tarfile
import zlib
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
try:
    from tools import pyodide_js_sources as source
except (ImportError,OSError):
    print('{"pass":false,"reason":"selected_runtime_source_notice_unavailable"}');raise SystemExit(2)

class Parser(argparse.ArgumentParser):
    def error(self,message):raise source.SourceError('Runtime source command refused')

def main(argv=None):
    p=Parser();group=p.add_mutually_exclusive_group()
    group.add_argument('--export');group.add_argument('--check-built');p.add_argument('--npm-archive')
    try:
        args=p.parse_args(argv)
        if args.export:
            source.need(args.npm_archive is None);result=source.export(args.export)
            print(json.dumps({'pass':True,'artifacts':{n:{'bytes':len(v),'sha256':source.sha(v)} for n,v in result.items()},**source.CLAIMS}));return 0
        if args.check_built:
            source.need(args.npm_archive is None);print(json.dumps(source.check_built(args.check_built)));return 0
        npm=source.read(Path(args.npm_archive).absolute().parent,Path(args.npm_archive).name,source.MAX_ARCHIVE) if args.npm_archive else None
        value,_=source.checked(npm=npm)
        print(json.dumps({'pass':True,'preferred_source_files':len(value['preferred']),'verbatim_license_texts':2,'cached_npm_replayed':npm is not None,**source.CLAIMS}));return 0
    except source.OutputUncertain:
        print('{"pass":false,"reason":"output_commit_uncertain","output_may_exist":true}');return 2
    except (OSError,ValueError,TypeError,KeyError,RecursionError,UnicodeError,EOFError,tarfile.TarError,zlib.error,OverflowError):
        print('{"pass":false,"reason":"selected_runtime_source_notice_unavailable"}');return 2

if __name__=='__main__':raise SystemExit(main())
