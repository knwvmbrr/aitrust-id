#!/usr/bin/env python3
"""Verify finite retained runtime facts or all selected received artifact bytes."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import web_runtime_obligations as runtime
from tools import artifact_evidence_io as evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    operation = parser.add_mutually_exclusive_group()
    operation.add_argument('--artifact-dir', type=Path, help='Check the complete fixed19-file received layout.')
    operation.add_argument('--prepare', type=Path, help='Create14 companions in a new private directory; runtime is not copied.')
    parser.add_argument('--output', type=Path, help='Optional new0600 JSON receipt outside Git.')
    args = parser.parse_args()
    try:
        if args.artifact_dir: result = runtime.check_built(args.artifact_dir)
        elif args.prepare: result = runtime.prepare(args.prepare)
        else: result = runtime.verify()
        result['captured_at'] = datetime.now(timezone.utc).isoformat()
        if args.output:
            captured = evidence.Capture()
            try: captured.save(args.output, result, 512_000); captured.close()
            finally: captured.close()
        print(json.dumps(result, sort_keys=True, separators=(',', ':')))
        return 0
    except (runtime.OutputUncertain, evidence.OutputCommitUncertain):
        print(json.dumps({'pass': False, 'status': 'Unavailable', 'output_may_exist': True,
                          'diagnostic': 'Private runtime outputs may exist; inspect before retrying.'}))
        return 2
    except Exception:
        print(json.dumps({'pass': False, 'status': 'Unavailable',
                          'diagnostic': 'Selected runtime obligations unavailable.'}))
        return 2


if __name__ == '__main__': raise SystemExit(main())
