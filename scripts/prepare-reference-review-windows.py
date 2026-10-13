#!/usr/bin/env python3
"""Bind your declared dates to a private corpus; this does not review its content."""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from protocol import corpus
from tools import reference_revision as revision
from tools.blind_review_io import create,source,PacketError


class Parser(argparse.ArgumentParser):
    def error(self,message):
        self.exit(2,'Window preparation refused; use --help for required arguments.\n')


def main(argv=None):
    parser=Parser(description=__doc__)
    parser.add_argument('--corpus',type=Path,required=True)
    parser.add_argument('--opens-at',required=True,help='Caller-declared UTC start: YYYY-MM-DDTHH:MM:SSZ.')
    parser.add_argument('--expires-at',required=True,help='Caller-declared exclusive UTC expiry.')
    parser.add_argument('--output',type=Path,required=True,help='New private folder outside the source checkout.')
    args=parser.parse_args(argv)
    try:
        record=corpus.parse(source(args.corpus,ROOT,corpus.MAX_STORE_BYTES))
        policy={'profile':revision.POLICY,'manifest_sha256':record['manifest_sha256'],'documents':[
            {'document_id':d['id'],'document_sha256':d['sha256'],'opens_at':args.opens_at,'expires_at':args.expires_at}
            for d in record['documents']]}
        at=revision.timestamp(args.opens_at)
        revision.windows(policy,record,at)
        create(args.output,ROOT,{'review-windows.json':corpus.encoded(policy)})
        print(json.dumps({'state':'caller_declared_policy_prepared','documents_bound':len(record['documents']),
                          'reviewer_authenticated':False,'source_freshness_established':False,'tag_asserted':False}))
        return 0
    except (ValueError,OSError,TypeError,KeyError,UnicodeError,RecursionError,PacketError):
        print(json.dumps({'state':'UNAVAILABLE','reason':'private_corpus_dates_or_output_refused',
            'next_step':'Use a private corpus, valid UTC start before expiry, and a new private output folder.',
            'tag_asserted':False}),file=sys.stderr)
        return 2


if __name__=='__main__':
    raise SystemExit(main())
