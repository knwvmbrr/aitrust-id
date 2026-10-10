#!/usr/bin/env python3
"""Request or verify optional independent digest timestamps. No authorship verdict."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import urllib.error
from independent_timestamp import issue, verify


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='operation', required=True)
    for name in ('request', 'verify'):
        command = sub.add_parser(name)
        command.add_argument('artifact', type=Path)
        command.add_argument('--ca-file', required=True, type=Path)
        command.add_argument('--tsa-file', required=True, type=Path)
        if name == 'request':
            command.add_argument('--output-dir', required=True, type=Path)
            command.add_argument('--send-digest', action='store_true',
                                 help='Explicitly share SHA-256 and nonce with FreeTSA; provider sees requester IP')
        else:
            command.add_argument('--query', required=True, type=Path)
            command.add_argument('--response', required=True, type=Path)
    a = p.parse_args()
    if a.operation == 'request':
        result = issue(a.artifact, a.output_dir, a.ca_file, a.tsa_file, a.send_digest)
    else:
        result = verify(a.artifact, a.query, a.response, a.ca_file, a.tsa_file)
    print(json.dumps(result))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, UnicodeError, subprocess.SubprocessError, urllib.error.URLError):
        print('Timestamp refused: invalid inputs, untrusted authority, signature failure or unavailable prerequisites. No valid verdict issued.', file=sys.stderr)
        raise SystemExit(2)
