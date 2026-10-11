#!/usr/bin/env python3
"""Create a private invented choice-frame packet, without reading a user example."""
import argparse,json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'));sys.path.insert(0,str(ROOT))
from protocol import corpus
from tools.choice_framing import observe
from tools.language_observations import digest
from tools.blind_review_io import create,PacketError

class Parser(argparse.ArgumentParser):
    def error(self,message):self.exit(2,'Demo preparation refused; use --help.\n')

def main(argv=None):
    parser=Parser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(argv)
    try:
        subject='Either agree or oppose.';reference='You can remain undecided.'
        doc={'id':'reference','text':reference,'sha256':corpus.sha(reference.encode())}
        content={'format':corpus.VERSION,'documents':[doc]}
        record={**content,'manifest_sha256':corpus.sha(corpus.encoded(content))}
        context={'format':'choice-frame-context/v1','language':'en','subject_sha256':digest(subject),
            'manifest_sha256':record['manifest_sha256'],'frames':[{'span':[0,len(subject)],
            'choices':[[7,12],[16,22]],'additional_reference':{'document_id':'reference',
            'document_sha256':doc['sha256'],'source_span':[0,len(reference)]}}]}
        observe(subject,record,context)
        create(args.output,ROOT,{'subject.txt':subject.encode(),'corpus.json':corpus.encoded(record),
            'context.json':(json.dumps(context,indent=2)+'\n').encode()})
        print(json.dumps({'created':True,'synthetic_only':True,'user_example_read':False,
            'next_step':'Run check-choice-framing.py with --packet and your new private folder.',
            'tag_asserted':False,'independent_accuracy_evidence':False}));return 0
    except (ValueError,OSError,KeyError,TypeError,RuntimeError,RecursionError,PacketError):
        print('Demo preparation unavailable; choose a new folder in an owner-held private directory outside the checkout.',file=sys.stderr);return 2

if __name__=='__main__':raise SystemExit(main())
