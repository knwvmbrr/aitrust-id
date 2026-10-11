#!/usr/bin/env python3
"""Inspect selected either/or wording with caller-provided context; no accusation."""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'));sys.path.insert(0,str(ROOT))
from protocol import corpus
from source_snapshot import unique
from tools import choice_framing
from tools.blind_review_io import create,source,PacketError

class Parser(argparse.ArgumentParser):
    def error(self,message):
        self.exit(2,'Choice-framing command refused; use --help for required arguments.\n')

def summary(result,saved):
    count=len(result['observations'])
    return {'profile':result['profile'],'state':result['state'],
        'selected_frames_checked':count+len(result['unmatched_selected_frames']),
        'supported_binary_patterns':count,
        'result':('Selected wording presents two choices; the extra passage is your nominated context, not a verified alternative.'
            if count else 'No supported either/or pattern matched your selected frames. This does not clear the wording or judge its intent.'),
        'detailed_output_saved':saved,'additional_options_verified':False,
        'manipulation_established':False,'truth_established':False,
        'independent_corroboration':False,'tag_asserted':False,'release_approved':False}

def main(argv=None):
    parser=Parser(description=__doc__)
    parser.add_argument('--packet',type=Path,help='Private folder containing subject.txt, corpus.json and context.json.')
    parser.add_argument('--subject',type=Path)
    parser.add_argument('--corpus',type=Path)
    parser.add_argument('--context',type=Path)
    parser.add_argument('--details',type=Path,help='New private folder; never overwrite.')
    args=parser.parse_args(argv)
    try:
        if args.packet is not None:
            if any(value is not None for value in (args.subject,args.corpus,args.context)):
                raise ValueError('Use one input mode')
            args.subject=args.packet/'subject.txt';args.corpus=args.packet/'corpus.json';args.context=args.packet/'context.json'
        elif any(value is None for value in (args.subject,args.corpus,args.context)):
            raise ValueError('Supply a complete input mode')
        text=source(args.subject,ROOT,32000).decode('utf-8','strict')
        record=corpus.parse(source(args.corpus,ROOT,corpus.MAX_STORE_BYTES))
        raw=source(args.context,ROOT,32768).decode('utf-8','strict')
        context=json.loads(raw,object_pairs_hook=unique,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Invalid number')))
        result=choice_framing.observe(text,record,context)
        if args.details:
            create(args.details,ROOT,{'choice-observations.json':(json.dumps(result,indent=2,allow_nan=False)+'\n').encode()})
        print(json.dumps(summary(result,args.details is not None),ensure_ascii=True,allow_nan=False))
        return 0
    except (ValueError,OSError,KeyError,TypeError,RuntimeError,RecursionError,ImportError,AttributeError,PacketError):
        print(json.dumps({'state':'UNAVAILABLE','reason':'invalid_private_subject_corpus_or_context',
            'next_step':'Check private file permissions, exact source bindings and supported selection limits.',
            'manipulation_established':False,'tag_asserted':False}),file=sys.stderr)
        return 2

if __name__=='__main__':raise SystemExit(main())
