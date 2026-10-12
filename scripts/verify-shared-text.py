#!/usr/bin/env python3
"""Run the native provider-copy refusal checks on macOS, without device or accuracy credit."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.blind_review_io import create, PacketError


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    names = ['mobile/ios/Source/SharedText.swift', 'mobile/ios/Tests/SharedTextChecks.swift',
             'scripts/verify-shared-text.py']
    report = {'pass': False, 'captured_at': datetime.now(timezone.utc).isoformat(),
              'physical_device': False, 'share_sheet_integration': False,
              'independent_accuracy': False, 'host': 'macOS'}
    created = False
    try:
        if sys.platform != 'darwin' or shutil.disk_usage(args.output.parent).free < 1_000_000_000:
            raise ValueError('macOS SDK and build capacity required')
        sources = {n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest() for n in names}
        create(args.output, ROOT, {'context.json': (json.dumps(report) + '\n').encode()})
        created = True
        binary = args.output / 'SharedTextChecks'
        with (args.output / 'compile.log').open('xb') as log:
            subprocess.run(['xcrun', '--sdk', 'macosx', 'swiftc', '-swift-version', '5',
                            '-module-cache-path', str(args.output / 'CompilerCache'),
                            str(ROOT / names[0]), str(ROOT / names[1]), '-o', str(binary)],
                           cwd=ROOT, stdout=log, stderr=log, check=True, timeout=90)
        measured = json.loads(subprocess.check_output([str(binary)], timeout=15))
        if measured != {'pass': True, 'accepted_utf8': True, 'refusals': 10, 'physical_device': False}:
            raise ValueError('Provider-copy controls failed')
        if sources != {n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest() for n in names}:
            raise ValueError('Sources changed during execution')
        report.update(measured, sources=sources, source_unchanged_during_execution=True)
    except (ValueError, OSError, subprocess.SubprocessError, PacketError):
        report['pass'] = False
        print('Native file checks unavailable; inspect the private build and SDK prerequisites.', file=sys.stderr)
    finally:
        if created:
            with (args.output / 'proof.json').open('x') as f:
                json.dump(report, f, indent=2); f.write('\n')
    print(json.dumps({k: report[k] for k in ['pass', 'physical_device', 'independent_accuracy']}))
    return 0 if report['pass'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
