#!/usr/bin/env python3
"""Prepare and verify complete selected website JavaScript notices, offline."""
import argparse
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import web_distribution as web


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise web.NoticeError('Website notice arguments refused')


def main():
    try:
        parser = Parser(description=__doc__)
        parser.add_argument('action', choices=('prepare', 'check-built', 'replay-archives', 'release-check'))
        parser.add_argument('--archive-dir', type=Path)
        parser.add_argument('--artifact-dir', type=Path)
        args = parser.parse_args()
        if args.action == 'replay-archives':
            web.require(args.archive_dir is not None and args.artifact_dir is None)
            result = web.replay_archives(args.archive_dir)
        elif args.action == 'prepare':
            web.require(args.archive_dir is None and args.artifact_dir is None)
            result = web.prepare()
        else:
            web.require(args.archive_dir is None)
            result = {'check-built':web.check_built, 'release-check':web.release_check}[args.action](artifact_dir=args.artifact_dir)
        print(json.dumps(result, sort_keys=True))
        return 0 if result['pass'] else 1
    except (OSError, ValueError, TypeError, KeyError, AttributeError, OverflowError, RecursionError, UnicodeError,
            EOFError, __import__('tarfile').TarError):
        print(json.dumps({'profile':web.PROFILE, 'pass':False, 'reason':'website_notice_check_refused',
                          'legal_clearance':False, 'release_approved':False}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
