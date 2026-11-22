#!/usr/bin/env python3
"""Read local JPEG credential details without uploads, fetching or tag issuance."""
import argparse
import json
from pathlib import Path
import signal
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import jpeg_provenance as jpeg
from tools.jpeg_provenance_io import Refused


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise Refused('invalid_request')


def main():
    if sys.argv[1:] == ['--worker']:
        try:
            jpeg.worker(); return 0
        except Refused as error:
            sys.stdout.buffer.write(jpeg.encoded({'kind': 'unavailable', 'reason': error.reason if error.reason in jpeg.actions.REASONS else 'worker_unavailable'})); return 0
        except BaseException:
            return 2
    output_json = '--json' in sys.argv[1:]
    try:
        parser = Parser(description=__doc__)
        parser.add_argument('--image', required=True)
        parser.add_argument('--json', action='store_true', help='Include linkable encoded-file hashes; never raw metadata.')
        parser.add_argument('--trust-anchors', help='Optional local public CA certificates; no private keys or network access.')
        args = parser.parse_args()
        def stop(signum, frame):
            raise Refused('worker_unavailable')
        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)
        value = jpeg.inspect(args.image, trust_anchors=args.trust_anchors)
        code = 0
    except Refused as error:
        value, code = jpeg.actions.unavailable(error.reason), 2
    except (OSError, ValueError, TypeError, RuntimeError, RecursionError, ImportError):
        value, code = jpeg.actions.unavailable('worker_unavailable'), 2
    print(json.dumps(value, ensure_ascii=True, allow_nan=False, sort_keys=True) if output_json else jpeg.text_result(value))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
