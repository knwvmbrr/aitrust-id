#!/usr/bin/env python3
"""Explicit local claim/passage selections; no NF assertion or source-truth claim."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).absolute().parents[1]))


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError('Selected source command refused.')


def main(argv=None):
    uncertain = ()
    try:
        from tools import nf_source_evidence as nf
        uncertain = (nf.io.OutputCommitUncertain,)
        parser = Parser(description=__doc__, allow_abbrev=False)
        commands = parser.add_subparsers(dest='command', required=True, parser_class=Parser)
        prepare = commands.add_parser('prepare', allow_abbrev=False)
        prepare.add_argument('--selections', required=True, help='Private closed JSON pair-span selections.')
        prepare.add_argument('--check', action='append', required=True, choices=nf.CHECKS)
        prepare.add_argument('--output', required=True, help='New private sidecar file, never overwritten.')
        check = commands.add_parser('check', allow_abbrev=False)
        check.add_argument('--sidecar', required=True)
        check.add_argument('--private-report')
        for command in (prepare, check):
            command.add_argument('--corpus', required=True)
            command.add_argument('--subject', required=True)
        args = parser.parse_args(argv)
        with nf.io.Capture() as capture:
            corpus_raw = capture.read(args.corpus, nf.corpus.MAX_STORE_BYTES)
            subject_raw = capture.read(args.subject, nf.MAX_SUBJECT_BYTES)
            if args.command == 'prepare':
                selection = nf.parse(capture.read(args.selections, nf.MAX_SIDECAR_BYTES), nf.MAX_SIDECAR_BYTES)
                value = nf.bind(corpus_raw, subject_raw, selection, args.check, capture)
                capture.save(args.output, value, nf.MAX_SIDECAR_BYTES)
                result = {'state': 'SELECTION_SAVED', 'selected_pairs': len(value['pairs']), 'tags': []}
                code = 0
            else:
                raw = capture.read(args.sidecar, nf.MAX_SIDECAR_BYTES)
                value = nf.check(corpus_raw, subject_raw, raw, capture)
                saved = args.private_report is not None and value['state'] != 'UNAVAILABLE'
                if saved:
                    capture.save(args.private_report, value, nf.MAX_RESULT_BYTES)
                capture.check()
                result = nf.summary(value, saved)
                code = 2 if value['state'] == 'UNAVAILABLE' else 0
        print(json.dumps(result, sort_keys=True, ensure_ascii=True))
        return code
    except uncertain:
        print('{"state":"UNAVAILABLE","reason":"output_commit_uncertain","output_may_exist":true,"tags":[]}')
        return 2
    except Exception:
        print('{"state":"UNAVAILABLE","reason":"invalid_or_unsupported_selected_source_request","tags":[]}')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
