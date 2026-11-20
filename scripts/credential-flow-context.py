#!/usr/bin/env python3
"""Bind explicitly selected Python to caller-declared context; never execute it."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).absolute().parents[1]))


class Parser(argparse.ArgumentParser):
    def error(self,message):
        raise ValueError('Credential context command refused.')


def main(argv=None):
    uncertain=()
    try:
        from tools import credential_flow_context as tool
        uncertain=(tool.io.OutputCommitUncertain,)
        parser=Parser(description=__doc__,allow_abbrev=False)
        commands=parser.add_subparsers(dest='command',required=True,parser_class=Parser)
        prepare=commands.add_parser('prepare',allow_abbrev=False)
        prepare.add_argument('--selection',required=True)
        prepare.add_argument('--output',required=True)
        check=commands.add_parser('check',allow_abbrev=False)
        check.add_argument('--sidecar',required=True)
        check.add_argument('--private-report')
        for sub in (prepare,check):sub.add_argument('--document',required=True)
        args=parser.parse_args(argv)
        with tool.io.Capture() as capture:
            raw=capture.read(args.document,tool.MAX_DOCUMENT_BYTES)
            if args.command=='prepare':
                selection=tool.parse(capture.read(args.selection,tool.MAX_PACKET_BYTES))
                binding=tool.bind(raw,selection,capture)
                capture.save(args.output,binding,tool.MAX_PACKET_BYTES)
                result={'state':'CONTEXT_SELECTION_SAVED','declared_context':binding['declared_context'],
                        'declaration_verified':False,'tags':[]};code=0
            else:
                packet=capture.read(args.sidecar,tool.MAX_PACKET_BYTES)
                value=tool.check(raw,packet,capture)
                saved=args.private_report is not None and value['state']!='UNAVAILABLE'
                if saved:capture.save(args.private_report,value,tool.MAX_RESULT_BYTES)
                capture.check();result=tool.summary(value,saved);code=2 if value['state']=='UNAVAILABLE' else 0
        print(json.dumps(result,ensure_ascii=True,sort_keys=True));return code
    except uncertain:
        print('{"state":"UNAVAILABLE","reason":"output_commit_uncertain","output_may_exist":true,"tags":[]}');return 2
    except Exception:
        print('{"state":"UNAVAILABLE","reason":"invalid_or_unsupported_credential_context","tags":[]}');return 2


if __name__=='__main__':raise SystemExit(main())
