#!/usr/bin/env python3
"""Build a development snapshot from one exact Git commit, never the working tree."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tarfile
from source_snapshot import build, inspect


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    raw = build(root, args.commit)
    # No overwrite, including dangling links. Output is supplied by the owner/job.
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if any(p.is_symlink() for p in (args.output.parent, *args.output.parent.parents)):
        raise ValueError('Symlinked output path')
    with args.output.open('xb') as stream:
        stream.write(raw)
    print(json.dumps({'pass': True, **inspect(raw, args.commit)}))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, EOFError, RecursionError, tarfile.TarError,
            subprocess.SubprocessError) as error:
        print('Source snapshot refused: ' + str(error), file=sys.stderr)
        raise SystemExit(2)
