"""Explicitly download pinned public research assets; never read user examples."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.blind_review_io import create, PacketError


def fetch(row, opener=urllib.request.urlopen):
    request = urllib.request.Request(row['url'], headers={'User-Agent': 'AITrust-ID-pinned-research/1'})
    with opener(request, timeout=30) as response:
        if response.status != 200:
            raise ValueError('Asset download refused')
        content = bytearray()
        while len(content) <= row['bytes']:
            chunk = response.read(min(1_048_576, row['bytes'] + 1 - len(content)))
            if not chunk:
                break
            content.extend(chunk)
    if len(content) != row['bytes'] or hashlib.sha256(content).hexdigest() != row['sha256']:
        raise ValueError('Pinned asset identity mismatch')
    return bytes(content)


class Parser(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, 'Asset command refused; use --help for required arguments.\n')


def main():
    parser = Parser(description=__doc__)
    parser.add_argument('--cache', required=True, type=Path,
                        help='New directory under an existing owner-private directory outside the checkout')
    args = parser.parse_args()
    if args.cache.exists() or args.cache.is_symlink():
        raise ValueError('Existing destination refused')
    manifest = json.loads((ROOT / 'research/nli/assets.json').read_text())
    # Reviewed source controls these public URLs and expected identities.
    files = {row['name']: fetch(row) for row in manifest['files']}
    create(args.cache, ROOT, files)
    print(json.dumps({'downloaded_pinned_public_assets': len(files),
                      'model_executed': False, 'user_examples_read': False}))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, KeyError, TypeError, PacketError):
        print('Pinned research assets unavailable; no model was executed.', file=sys.stderr)
        raise SystemExit(2)
