#!/usr/bin/env python3
"""Inspect an explicitly selected PNG; raw metadata requires private export."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from protocol.corpus import CorpusError
from tools import manifest_inspection as tool
DECLARATION_PROFILE = 'attached-png-action-declarations/1.0.0'


def load_text_formatter():
    # An optional view must not become a dependency of the JSON/worker routes.
    try:
        from tools.manifest_presentation import text_result
        if not callable(text_result):
            raise AttributeError('Unsupported formatter')
        return text_result
    except (ImportError, SyntaxError, AttributeError):
        raise CorpusError('Text presentation unavailable.') from None


def unavailable_text():
    # Never ask an unavailable or failed presentation module to render its error.
    return '\n'.join(['AI TRUST ID - PNG evidence check',
        'Method: ' + tool.METHOD + ' (PNG only).',
        'No valid inspection result was obtained.',
        'Check the supported PNG input and optional pinned SDK installation.',
        'AI origin: Unknown. This method does not determine whether AI made or edited the image.',
        'No tag issued. Image contents and authorship are not verified.'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', help='Selected local PNG, at most 10 MiB')
    parser.add_argument('--private-report', help='New file in an existing 0700 directory outside source; may contain names/GPS')
    parser.add_argument('--format', choices=('json', 'text'), default='json', help='Output format; JSON remains the default')
    parser.add_argument('--profile', choices=('inspection', 'action-declarations-v1'), default='inspection',
                        help='Optional bounded recorded-action declaration profile; never an AI-origin verdict')
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    declarations = None
    try:
        if args.worker:
            if args.image or args.private_report or args.format != 'json' or args.profile != 'inspection':
                raise CorpusError('Unsupported worker invocation.')
            tool.worker()
            return 0
        if not args.image:
            parser.error('--image is required')
        if args.profile == 'action-declarations-v1':
            from tools import manifest_declarations as declarations
            if declarations.PROFILE != DECLARATION_PROFILE:
                raise CorpusError('Unsupported declaration profile version.')
        formatter = load_text_formatter() if args.format == 'text' else None
        if formatter is not None and declarations is not None:
            formatter = declarations.text_result
        result, report = tool.inspect(args.image)
        if declarations is not None:
            result = declarations.from_inspection(result, report)
        # Reject an unsupported text-view envelope before any requested export.
        if args.format == 'text':
            formatter(result)
        if args.private_report:
            if report is None:
                raise CorpusError('No attached raw report is available.')
            tool.save_private(report, args.private_report)
            result['private_report_saved'] = True
        result['method_sha256'] = __import__('hashlib').sha256(Path(tool.__file__).read_bytes()).hexdigest()
        print(formatter(result) if formatter is not None else json.dumps(result, ensure_ascii=True, indent=2))
        return 0
    except (CorpusError, OSError, ValueError, RecursionError, ImportError, SyntaxError, AttributeError):
        if not args.worker:
            result = {'state': 'UNAVAILABLE', 'reason': 'inspection_unavailable_or_unsupported',
                'method': tool.METHOD, 'tags': [], 'content_truth_established': False, 'author_identity_established': False}
            if args.profile == 'action-declarations-v1':
                # Never call a failed optional interpreter or renderer again.
                result.update(profile=DECLARATION_PROFILE, declaration_state='UNAVAILABLE',
                              ai_origin='unknown', production_assertion=False)
                print('AI TRUST ID - PNG action declarations\nNo valid declaration inspection result was obtained.\nAI origin: Unknown.\nNo tag issued.'
                      if args.format == 'text' else json.dumps(result))
            else:
                print(unavailable_text() if args.format == 'text' else json.dumps(result))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
