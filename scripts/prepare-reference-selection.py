#!/usr/bin/env python3
"""Bind one chosen claim/reference line privately; no model, retrieval or upload."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from protocol import corpus
from research.nli import selected_references as selected
from tools.blind_review_io import create, source, PacketError


class Parser(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, 'Reference selection refused; use --help for required arguments.\n')


def main(argv=None):
    parser = Parser(description=__doc__)
    parser.add_argument('--corpus', type=Path, required=True)
    parser.add_argument('--subject', type=Path, required=True)
    parser.add_argument('--claim-line', type=int, required=True, help='One-based physical line, counting blank lines.')
    parser.add_argument('--reference-document', required=True, help='Existing opaque corpus document ID.')
    parser.add_argument('--reference-line', type=int, required=True, help='One-based physical line, counting blank lines.')
    parser.add_argument('--output', type=Path, required=True, help='New folder in an existing owner-private directory outside this checkout.')
    args = parser.parse_args(argv)
    try:
        record = corpus.parse(source(args.corpus, ROOT, corpus.MAX_STORE_BYTES))
        subject = source(args.subject, ROOT, 8000).decode('utf-8', 'strict')
        selection = selected.bind(record, subject, args.claim_line, args.reference_document, args.reference_line)
        create(args.output, ROOT, {'selection.json': corpus.encoded(selection)})
        print(json.dumps({'state': 'caller_selected_pair_prepared', 'pairs_selected': 1,
            'retrieval_performed': False, 'model_evaluation_obtained': False,
            'truth_established': False, 'tag_asserted': False}))
        return 0
    except (ValueError, OSError, TypeError, KeyError, UnicodeError, RecursionError, PacketError):
        print(json.dumps({'state': 'UNAVAILABLE', 'reason': 'private_reference_selection_refused',
            'next_step': 'Use current private inputs, supported nonempty line numbers and a new private output folder.',
            'tag_asserted': False}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
