#!/usr/bin/env python3
"""Private hash-only feedback software; no company collection or public registry."""
import argparse,json,sys
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
try:from tools import hash_reports as h
except ImportError:
    print('HASH INBOX UNAVAILABLE: use the supported macOS/Linux Python environment.',file=sys.stderr);raise SystemExit(2)
class Parser(argparse.ArgumentParser):
    def error(self,message):self.exit(2,'Hash inbox operation refused; use --help.\n')
def main(argv=None):
    p=Parser(description=__doc__);sub=p.add_subparsers(dest='operation',required=True)
    q=sub.add_parser('preview');q.add_argument('--json',action='store_true')
    q=sub.add_parser('init');q.add_argument('--root',type=Path,required=True);q.add_argument('--days',type=int,default=30)
    q=sub.add_parser('ingest');q.add_argument('--root',type=Path,required=True);q.add_argument('--consent-store-hashes',action='store_true')
    for op in ['stats','prune','export','withdraw','remove']:
        q=sub.add_parser(op);q.add_argument('--root',type=Path,required=True)
        if op=='export':q.add_argument('--output',type=Path,required=True)
        if op=='withdraw':q.add_argument('--ticket',required=True)
        if op=='remove':q.add_argument('--confirm-inbox-removal',action='store_true')
    a=p.parse_args(argv)
    try:
        op=a.operation
        if op in ('preview','ingest'):
            row=h.feedback(h.parse(sys.stdin.buffer.read(4097)))
            if op=='preview':
                if a.json:print(json.dumps({'feedback':row,'stored':False,'verified':False,'training_label':None,'company_collection_enabled':False}))
                else:print('Unverified '+row['code']+' feedback: '+row['category']+'.\nSubject and method hashes are linkable metadata. Nothing was stored or sent.')
                return 0
            result=h.Inbox(a.root).ingest(row,consent=a.consent_store_hashes)
        elif op=='init':result=h.Inbox.initialize(a.root,a.days)
        elif op in ('stats','prune'):result=h.Inbox(a.root).stats()
        elif op=='withdraw':result=h.Inbox(a.root).withdraw(a.ticket)
        elif op=='remove':result=h.Inbox(a.root).remove(consent=a.confirm_inbox_removal)
        else:
            row=h.Inbox(a.root).export();raw=h.encode(row);h.publish(a.output,raw);result={'exported_records':len(row['records']),'sha256':h.hashlib.sha256(raw).hexdigest(),'verified':False,'training_labels_included':False}
        print(json.dumps(result,allow_nan=False));return 0
    except KeyboardInterrupt:print('Hash inbox operation cancelled. Inspect local status before continuing.',file=sys.stderr);return 130
    except Exception:print('HASH INBOX UNAVAILABLE: no valid intake operation completed. Personal checking remains separate.',file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
