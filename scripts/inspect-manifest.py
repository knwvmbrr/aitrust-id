#!/usr/bin/env python3
"""Inspect an explicitly selected PNG; raw metadata requires private export."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from protocol.corpus import CorpusError
from tools import manifest_inspection as tool


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', help='Selected local PNG, at most 10 MiB')
    parser.add_argument('--private-report', help='New file in an existing 0700 directory outside source; may contain names/GPS')
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    try:
        if args.worker:
            if args.image or args.private_report:
                raise CorpusError('Unsupported worker invocation.')
            tool.worker()
            return 0
        if not args.image:
            parser.error('--image is required')
        result, report = tool.inspect(args.image)
        if args.private_report:
            if report is None:
                raise CorpusError('No attached raw report is available.')
            tool.save_private(report, args.private_report)
            result['private_report_saved'] = True
        result['method_sha256'] = __import__('hashlib').sha256(Path(tool.__file__).read_bytes()).hexdigest()
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0
    except (CorpusError, OSError, ValueError, RecursionError):
        if not args.worker:
            print(json.dumps({'state': 'UNAVAILABLE', 'reason': 'inspection_unavailable_or_unsupported',
                'method': tool.METHOD, 'tags': [], 'content_truth_established': False, 'author_identity_established': False}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
