#!/usr/bin/env python3
"""Check selected asset/notice consistency offline; never grant legal clearance."""
import argparse
import json
from pathlib import Path
import sys
import tarfile
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.asset_notices import verify
from protocol.reports import write_report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepared-runtime', action='store_true')
    parser.add_argument('--runtime-archive', type=Path)
    parser.add_argument('--require-clearance', action='store_true')
    parser.add_argument('--output')
    args = parser.parse_args()
    record = verify(prepared_runtime=args.prepared_runtime, runtime_archive=args.runtime_archive)
    if args.output:
        write_report(args.output, record, root=ROOT)
    print(json.dumps(record, indent=2))
    return 1 if args.require_clearance else 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, OSError, KeyError, TypeError, tarfile.TarError):
        # Paths and archive diagnostics can reveal private local locations.
        print('Selected asset/notice verification refused.', file=sys.stderr)
        raise SystemExit(2)
