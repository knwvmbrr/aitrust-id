#!/usr/bin/env python3
"""Attach and inspect private local reference text without a service or account."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from protocol import corpus


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    create = commands.add_parser('create')
    create.add_argument('--output', type=Path, required=True)
    create.add_argument('--source', action='append', required=True, metavar='ID=FILE')
    for name in ('inspect', 'query'):
        sub = commands.add_parser(name)
        sub.add_argument('--corpus', type=Path, required=True)
        if name == 'query':
            choice = sub.add_mutually_exclusive_group(required=True)
            choice.add_argument('--text', help='Literal phrase; avoid private text in shell history.')
            choice.add_argument('--stdin', action='store_true', help='Read a private phrase from standard input.')
    args = parser.parse_args(argv)
    try:
        if args.command == 'create':
            sources = []
            for item in args.source:
                if '=' not in item:
                    raise corpus.CorpusError('Specify each source as ID=FILE.')
                sources.append(item.split('=', 1))
            result = corpus.create(sources, args.output)
        else:
            record = corpus.load(args.corpus)
            if args.command == 'inspect':
                result = corpus.summary(record)
            else:
                phrase = sys.stdin.read(corpus.MAX_QUERY_CHARACTERS + 1) if args.stdin else args.text
                result = corpus.query(record, phrase)
        # Escape control sequences so hostile source passages remain terminal text.
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0
    except (corpus.CorpusError, OSError, UnicodeError):
        print('Local corpus request failed: ' + (str(sys.exc_info()[1]) if isinstance(sys.exc_info()[1], corpus.CorpusError) else 'Private storage is unavailable.'), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
