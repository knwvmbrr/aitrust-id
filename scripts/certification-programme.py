#!/usr/bin/env python3
"""Prepare/check private nonoperating reference-programme review records."""
import argparse
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError('Reference programme unavailable.')


def main(argv=None):
    uncertain = ()
    try:
        from tools import certification_programme as tool
        uncertain = (tool.OutputCommitUncertain,)
        parser = Parser(description=__doc__, allow_abbrev=False)
        sub = parser.add_subparsers(dest='operation', required=True, parser_class=Parser)
        for kind, names in [('practice',()), ('start',('application',)),
                            ('advance',('record','event')), ('inspect',('record',)),
                            ('revalidate',('record','application'))]:
            p = sub.add_parser(kind, allow_abbrev=False)
            for name in names:
                p.add_argument('--'+name, type=Path, required=True)
            if kind != 'inspect':
                p.add_argument('--output', type=Path, required=True)
        args = parser.parse_args(argv)
        inputs = {name:getattr(args,name) for name in ('application','record','event')
                  if hasattr(args,name)}
        result = tool.execute(args.operation, inputs, getattr(args,'output',None))
        print(json.dumps(result, sort_keys=True))
        return 0
    except uncertain:
        print('{"state":"UNAVAILABLE","reason":"output_commit_uncertain","output_may_exist":true}')
        return 2
    except (ValueError,OSError,TypeError,KeyError,ImportError,SyntaxError,RecursionError,
            UnicodeError,RuntimeError,KeyboardInterrupt):
        print('{"state":"UNAVAILABLE","reason":"reference_programme_refused"}')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
