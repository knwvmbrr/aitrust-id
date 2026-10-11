#!/usr/bin/env python3
"""Check one independently selected language observation using private stdin."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from protocol.corpus import CorpusError, read_regular, unique_pairs
from tools import language_observations as observations


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('kind', choices=['hedge', 'urgency', 'authority'])
    parser.add_argument('--language', required=True, choices=['en'])
    parser.add_argument('--annotations', type=Path)
    parser.add_argument('--minimum-density', type=float, default=.5)
    args = parser.parse_args(argv)
    try:
        context = None
        if args.annotations:
            context = json.loads(read_regular(args.annotations, 16384, private=True),
                                 object_pairs_hook=unique_pairs,
                                 parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        output = observations.observe(args.kind, sys.stdin.read(observations.MAX_CHARACTERS+1),
                                      args.language, context, args.minimum_density)
        print(json.dumps(output, ensure_ascii=True, indent=2))
        return 0
    except (CorpusError, OSError, UnicodeError, ValueError, TypeError, RecursionError):
        print(json.dumps({'state': 'UNAVAILABLE', 'reason': 'invalid_or_unsupported_subject_context_or_parameters',
                          'tags': [], 'intent_established': False, 'truth_established': False}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
