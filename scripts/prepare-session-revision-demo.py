#!/usr/bin/env python3
"""Prepare an invented private revision-context example without capturing anything."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from protocol import corpus
from tools import session_revisions as tool
from tools.blind_review_io import PacketError,create
class Parser(argparse.ArgumentParser):
    def error(self,message):self.exit(2,"Revision practice command refused; use --help for arguments.\n")
def main(argv=None):
    p=Parser(description=__doc__);p.add_argument("--output",type=Path,required=True);a=p.parse_args(argv)
    try:
        previous="The answer.";current="The answer is 4.";text="2 + 2"
        content={"format":corpus.VERSION,"documents":[{"id":"invented-context","text":text,"sha256":corpus.sha(text.encode())}]}
        record=dict(content,manifest_sha256=corpus.sha(corpus.encoded(content)))
        selection={"profile":tool.PROFILE,"previous_sha256":tool.digest(previous),"current_sha256":tool.digest(current),"context_manifest_sha256":record["manifest_sha256"],"spans":[[14,15]]}
        create(a.output,ROOT,{"previous.txt":previous.encode(),"current.txt":current.encode(),"context.json":corpus.encoded(record),"selections.json":corpus.encoded(selection)})
        print(json.dumps({"state":"invented_practice_files_created","files":4,"captured_user_data":False,"tag_asserted":False}));return 0
    except (PacketError,OSError,ValueError,UnicodeError):
        print(json.dumps({"state":"UNAVAILABLE","reason":"new_private_practice_destination_refused","tag_asserted":False}),file=sys.stderr);return 2
if __name__=="__main__":raise SystemExit(main())
