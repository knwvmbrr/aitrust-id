#!/usr/bin/env python3
"""Review private reference dependencies without publishing text or issuing a tag."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from protocol import corpus
from tools import reference_revision as revision
from tools.blind_review_io import PacketError, source, create


class Parser(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, 'Reference revision command refused; use --help for arguments.\n')


def main(argv=None):
    parser = Parser(description=__doc__)
    for name in ('previous-corpus', 'current-corpus', 'subject', 'observation'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--review-windows', type=Path)
    parser.add_argument('--at', required=True, help='Explicit UTC time, YYYY-MM-DDTHH:MM:SSZ.')
    parser.add_argument('--details', type=Path, help='New private output folder outside the checkout.')
    args = parser.parse_args(argv)
    try:
        previous = corpus.parse(source(args.previous_corpus, ROOT, corpus.MAX_STORE_BYTES))
        current = corpus.parse(source(args.current_corpus, ROOT, corpus.MAX_STORE_BYTES))
        subject = source(args.subject, ROOT, 8000).decode('utf-8', 'strict')
        observation = revision.decode(source(args.observation, ROOT, revision.MAX_OBSERVATION_BYTES), revision.MAX_OBSERVATION_BYTES)
        policy = (revision.decode(source(args.review_windows, ROOT, revision.MAX_POLICY_BYTES), revision.MAX_POLICY_BYTES)
                  if args.review_windows else None)
        if args.review_windows:
            revision.require(type(policy) is dict)
        result = revision.review(previous, current, subject, observation, policy, args.at)
        if args.details:
            create(args.details, ROOT, {'reference-revision.json': (json.dumps(result, ensure_ascii=True,
                sort_keys=True, indent=2, allow_nan=False) + '\n').encode()})
        print(json.dumps(revision.summary(result, args.details is not None), ensure_ascii=True, allow_nan=False))
        return 0
    except (revision.RevisionError, corpus.CorpusError, PacketError, OSError, UnicodeError, ValueError, RecursionError):
        print(json.dumps({'state': 'UNAVAILABLE', 'reason': 'private_input_or_reference_contract_refused',
            'next_step': 'Check the original corpus, observation, declared windows and private file permissions.',
            'tag_asserted': False}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
