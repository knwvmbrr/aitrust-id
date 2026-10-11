#!/usr/bin/env python3
"""Check preserved dependency notices offline; --require-clearance refuses this unreviewed profile."""
import argparse
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.license_notices import verify
from protocol.reports import write_report

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive-dir', type=Path)
    p.add_argument('--require-clearance', action='store_true')
    p.add_argument('--output')
    args = p.parse_args()
    record = verify(archive_dir=args.archive_dir)
    if args.output: write_report(args.output, record, root=ROOT)
    print(json.dumps(record, indent=2))
    return 1 if args.require_clearance and not record['license_release_pass'] else 0

if __name__ == '__main__':
    try: raise SystemExit(main())
    except (ValueError, OSError, KeyError, TypeError) as error:
        print('Dependency notice verification refused: ' + type(error).__name__, file=sys.stderr)
        raise SystemExit(2)
