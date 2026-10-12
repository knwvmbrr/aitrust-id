#!/usr/bin/env python3
"""Compare explicitly selected wording with earlier and captured private text."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from protocol import corpus
from tools import session_revisions as tool
from tools.blind_review_io import PacketError,source,create

class Parser(argparse.ArgumentParser):
    def error(self,message):self.exit(2,"Revision context command refused; use --help for arguments.\n")

def main(argv=None):
    p=Parser(description=__doc__)
    for name in ["previous","current","context","selections"]:p.add_argument("--"+name,type=Path,required=True)
    p.add_argument("--details",type=Path)
    a=p.parse_args(argv)
    try:
        previous=source(a.previous,ROOT,32768).decode("utf-8","strict")
        current=source(a.current,ROOT,32768).decode("utf-8","strict")
        captured=source(a.context,ROOT,corpus.MAX_STORE_BYTES)
        selections=tool.decode(source(a.selections,ROOT,tool.MAX_SELECTION_BYTES))
        result=tool.compare(previous,current,captured,selections)
        if a.details:create(a.details,ROOT,{"revision-context.json":(json.dumps(result,sort_keys=True,ensure_ascii=True,indent=2,allow_nan=False)+"\n").encode()})
        print(json.dumps(tool.summary(result,a.details is not None),allow_nan=False))
        return 0
    except (tool.ContextError,corpus.CorpusError,PacketError,OSError,UnicodeError,ValueError,TypeError,RecursionError):
        print(json.dumps({"state":"UNAVAILABLE","reason":"private_revision_context_contract_refused","tag_asserted":False}),file=sys.stderr)
        return 2
if __name__=="__main__":raise SystemExit(main())
