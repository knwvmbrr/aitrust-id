#!/usr/bin/env python3
"""Use an operator-owned OpenID Connect directory for private audit operations."""
import argparse,json,sys
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools.organization_directory import config,Provider,Broker,parse,encoded,private_file,create
class Parser(argparse.ArgumentParser):
    def error(self,message):self.exit(2,'Directory command refused; use --help.\n')
def main():
    p=Parser(description=__doc__);p.add_argument('--config',required=True,type=Path)
    sub=p.add_subparsers(dest='command',required=True);sub.add_parser('initialize')
    q=sub.add_parser('begin');q.add_argument('--output',type=Path,required=True)
    q=sub.add_parser('finish');q.add_argument('--pending',type=Path,required=True);q.add_argument('--output',type=Path,required=True)
    q=sub.add_parser('call');q.add_argument('--output',type=Path,required=True)
    q=sub.add_parser('logout');q.add_argument('--session',type=Path,required=True)
    q=sub.add_parser('recover');q.add_argument('--compromised-subject',required=True);q.add_argument('--replacement-session',type=Path,required=True)
    a=p.parse_args()
    try:
        c=config(a.config);broker=Broker(c)
        if a.command=='initialize':result=broker.journal.initialize()
        elif a.command=='begin':
            v=broker.provider.begin();create(a.output,ROOT,{'pending.json':encoded(v)+b'\n'})
            result={'verification_uri':v['verification_uri'],'user_code':v['user_code'],'private_pending_saved':True}
        elif a.command=='finish':
            v=broker.provider.finish_once(parse(private_file(a.pending)));create(a.output,ROOT,{'session.json':encoded(v)+b'\n'});result={'signed_in':True,'session_saved_privately':True}
        elif a.command=='call':
            raw=sys.stdin.buffer.read(131073);v=broker.dispatch(parse(raw,131072));create(a.output,ROOT,{'result.json':encoded(v)+b'\n'});result={'completed':True,'result_saved_privately':True,'independent_validation':False}
        elif a.command=='logout':result=broker.logout(parse(private_file(a.session)))
        else:
            session=parse(private_file(a.replacement_session));result=broker.journal.recover(a.compromised_subject,session['access_token'],broker.provider)
        print(json.dumps(result));return 0
    except Exception:
        print('{"state":"UNAVAILABLE","reason":"organization_directory_contract_refused"}',file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
