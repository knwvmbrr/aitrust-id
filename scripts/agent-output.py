#!/usr/bin/env python3
"""Record a reviewed Python stdio agent and optional independent PS check."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools import agent_output as a

class Parser(argparse.ArgumentParser):
    def error(self,message):self.exit(2,'Agent operation refused; use --help. Private input and paths are not echoed.\n')

def main(argv=None):
    p=Parser(description=__doc__,epilog='Your selected agent has your OS-user file/network privileges. This is not a sandbox. Credential environment variables are not forwarded automatically. No service, account or local Docker is required.')
    sub=p.add_subparsers(dest='operation',required=True,parser_class=Parser)
    r=sub.add_parser('record',help='Execute only a program you reviewed; save an owner-private answer and signed source statement.')
    for name in ['program','task','agent','key','public-key','output']:r.add_argument('--'+name,type=Path,required=True)
    r.add_argument('--execute-reviewed-agent',action='store_true')
    r.add_argument('--check-ps',action='store_true')
    r.add_argument('--include-output-view',action='store_true',help='Separately include answer text in the private offline HTML.')
    r.add_argument('--timeout',type=int,default=10)
    v=sub.add_parser('verify',help='Use the separately trusted agent descriptor/key and exact private answer.')
    for name in ['record','answer','agent','public-key']:v.add_argument('--'+name,type=Path,required=True)
    d=sub.add_parser('demo',help='Create invented practice inputs and a practice key in a new private folder.')
    d.add_argument('--output',type=Path,required=True)
    args=p.parse_args(argv)
    try:
        if args.operation=='record':
            result=a.record_run(program=args.program,task=args.task,agent=args.agent,key=args.key,
               public_key=args.public_key,output=args.output,execute=args.execute_reviewed_agent,
               check_ps=args.check_ps,include_output=args.include_output_view,timeout=args.timeout)
        elif args.operation=='verify':result=a.verify_run(record=args.record,answer=args.answer,agent=args.agent,public_key=args.public_key)
        else:result=a.demo(args.output)
        print(json.dumps(result));return 0
    except Exception:
        print(json.dumps({'state':'UNAVAILABLE','reason':'agent_operation_incomplete_or_refused',
                         'next_step':'Check the reviewed program, selected key/descriptor, private file permissions and new destination.',
                         'independent_accuracy_evidence':False,'certification':False}),file=sys.stderr)
        return 2

if __name__=='__main__':raise SystemExit(main())
