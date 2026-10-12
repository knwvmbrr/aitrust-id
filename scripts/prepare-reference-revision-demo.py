#!/usr/bin/env python3
"""Create invented, private reference changes to practice the review command."""
import argparse
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from protocol import corpus, corpus_support
from tools.reference_revision import POLICY
from tools.blind_review_io import PacketError, create


def envelope(documents):
    content = {'format': corpus.VERSION, 'documents': [
        {'id': identity, 'sha256': corpus.sha(text.encode()), 'text': text} for identity, text in sorted(documents.items())]}
    return dict(content, manifest_sha256=corpus.sha(corpus.encoded(content)))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        old = envelope({'manual': 'The fee is 25 dollars.\n', 'policy': 'Use a blue bicycle.\n'})
        current = envelope({'manual': 'The fee is 26 dollars.\n', 'policy': 'Use a blue bicycle.\n'})
        subject = 'The fee is 25 dollars.\nUse a blue bicycle.'
        windows = {'profile': POLICY, 'manifest_sha256': current['manifest_sha256'], 'documents': [
            {'document_id': d['id'], 'document_sha256': d['sha256'], 'opens_at': '2026-10-01T00:00:00Z',
             'expires_at': '2026-11-01T00:00:00Z'} for d in current['documents']]}
        files = {'old.json': corpus.encoded(old), 'new.json': corpus.encoded(current),
                 'subject.txt': subject.encode(), 'observation.json': corpus.encoded(corpus_support.observe(old, subject, 1)),
                 'windows.json': corpus.encoded(windows),
                 'README.txt': b'Invented practice data only. One document changes and the other stays the same.\nUse the explicit invented evaluation time 2026-10-12T12:00:00Z.\nNo NF/FI tag, independent accuracy or actual freshness is established.\n'}
        create(args.output, ROOT, files)
        print(json.dumps({'state': 'synthetic_practice_created', 'files': len(files), 'tag_asserted': False}))
        return 0
    except (ValueError, OSError, PacketError):
        print('Practice creation refused. Choose a new folder in an existing private directory outside the checkout.', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
