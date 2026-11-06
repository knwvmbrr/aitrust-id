#!/usr/bin/env python3
"""Explicit foreground capture of one owner-selected private text file."""
import argparse,json,sys
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools.host_capture import run,fingerprint
class Parser(argparse.ArgumentParser):
    def error(self,message):self.exit(2,'Host capture refused; use --help for supported arguments.\n')
def main(argv=None):
    p=Parser(description=__doc__);p.add_argument('--fingerprint',action='store_true')
    p.add_argument('--root',type=Path);p.add_argument('--file');p.add_argument('--source-sha256')
    p.add_argument('--consent-local-text-only',action='store_true');p.add_argument('--tag',choices=['PS'])
    p.add_argument('--record-dir',type=Path,help='Optional NEW private metadata directory outside source repositories; hashes can link to input')
    a=p.parse_args(argv)
    try:
        if a.fingerprint:
            if any(v for v in (a.root,a.file,a.source_sha256,a.consent_local_text_only,a.record_dir)):raise ValueError('Mixed request')
            print(json.dumps(fingerprint(a.tag)));return 0
        if not a.root or not a.file or not a.source_sha256:raise ValueError('Missing explicit scope')
        return run(a.root,a.file,a.source_sha256,consent=a.consent_local_text_only,tag=a.tag,record_dir=a.record_dir)
    except KeyboardInterrupt:
        print('HOST STOPPED · interrupted; capture does not restart automatically');return 130
    except Exception:
        print('HOST UNAVAILABLE · start or operation refused; private content was not printed',file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
