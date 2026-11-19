#!/usr/bin/env python3
"""Associate selected literal numbered markers with documents already attached."""
import argparse
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).absolute().parents[1]))


class Refusal(ValueError):
    pass


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise Refusal('Unsupported command.')


def main(argv=None):
    try:
        from tools import citation_resolution as tool
        parser = Parser(description=__doc__, allow_abbrev=False)
        sub = parser.add_subparsers(dest='command', required=True, parser_class=Parser)
        prepare = sub.add_parser('prepare', allow_abbrev=False)
        prepare.add_argument('--map', action='append', default=[], metavar='NUMBER=DOCUMENT_ID')
        prepare.add_argument('--output', required=True)
        check = sub.add_parser('check', allow_abbrev=False)
        check.add_argument('--sidecar', required=True)
        check.add_argument('--private-report')
        for command in (prepare, check):
            command.add_argument('--subject', required=True, help='Explicit owner-private UTF-8 file, 0600.')
            command.add_argument('--corpus', required=True, help='Existing private corpus-v1 file, 0600.')
        args = parser.parse_args(argv)
        with tool.Capture() as capture:
            sources = tool.current_sources(capture)
            corpus_raw = capture.read(args.corpus, tool.corpus.MAX_STORE_BYTES)
            subject_raw = capture.read(args.subject, tool.MAX_SUBJECT_BYTES)
            if args.command == 'prepare':
                tool.need(len(args.map) <= tool.MAX_MAPPINGS)
                pairs = []
                for item in args.map:
                    tool.need(len(item) <= 70)
                    match = re.fullmatch(r'([1-9][0-9]{0,3})=([A-Za-z0-9][A-Za-z0-9_-]{0,63})', item, re.ASCII)
                    tool.need(match is not None)
                    pairs.append((int(match.group(1)), match.group(2)))
                value = tool._prepare(corpus_raw, subject_raw, pairs, sources)
                capture.save(args.output, value, tool.MAX_SIDECAR_BYTES)
                result = {'state': 'SIDECAR_SAVED', 'mapping_count': len(pairs),
                          'network_used': False, 'tags': [], 'subject_text_included': False}
            else:
                sidecar_raw = capture.read(args.sidecar, tool.MAX_SIDECAR_BYTES)
                result, detail = tool._check(corpus_raw, subject_raw, sidecar_raw, sources)
                if args.private_report:
                    capture.save(args.private_report, detail, tool.MAX_REPORT_BYTES)
                    result['private_report_saved'] = True
                else:
                    capture.check()
        print(json.dumps(result, ensure_ascii=True, sort_keys=True))
        return 0
    except (ValueError, OSError, UnicodeError, TypeError, RecursionError, RuntimeError, ImportError, SyntaxError):
        print('{"state":"UNAVAILABLE","reason":"invalid_or_unsupported_local_citation_request","tags":[]}')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
