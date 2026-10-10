#!/usr/bin/env python3
"""Bounded offline conformance check; never prints submitted assertion content."""
import argparse
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
LIMIT = 2 * 1024 * 1024
SUPPORTED = '0.1.0'


def pairs(items):
    value = {}
    for key, item in items:
        if key in value:
            raise ValueError('Duplicate key')
        value[key] = item
    return value


def reject_constant(_):
    raise ValueError('Non-finite number')


def finite(value):
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError('Non-finite number')
    if isinstance(value, dict):
        for item in value.values():
            finite(item)
    elif isinstance(value, list):
        for item in value:
            finite(item)
    elif isinstance(value, str) and any(0xD800 <= ord(c) <= 0xDFFF for c in value):
        raise ValueError('Non-scalar string')


def check(raw, profile):
    if len(raw) > LIMIT:
        return 'invalid', 'input_limit'
    try:
        value = json.loads(raw.decode('utf-8', errors='strict'), object_pairs_hook=pairs,
                           parse_constant=reject_constant)
        finite(value)
    except (UnicodeError, ValueError, RecursionError):
        return 'invalid', 'invalid_json'
    if not isinstance(value, dict):
        return 'invalid', 'invalid_schema'
    version=value.get('spec_version')
    if not isinstance(version,str) or len(version)>32 or not re.fullmatch(r'\d+\.\d+\.\d+',version,flags=re.ASCII):
        return 'invalid','invalid_version'
    # A future wire layout cannot be judged using today's schema. Preserve and
    # refuse it before touching its unknown fields or optional dependencies.
    if version != SUPPORTED:
        return 'unsupported','unsupported_version'
    try:
        from protocol.assertions import validator
        if not validator().is_valid(value):
            return 'invalid', 'invalid_schema'
    except ImportError:
        return 'unavailable', 'missing_dependencies'
    except (RuntimeError, ValueError):
        return 'unavailable', 'validator_configuration'
    except RecursionError:
        return 'invalid', 'input_depth'
    if profile == 'extension':
        node = shutil.which('node')
        if node is None:
            return 'unavailable', 'missing_node'
        program = "const fs=require('fs'),vm=require('vm');vm.runInThisContext(fs.readFileSync(process.argv[1],'utf8'));process.stdout.write(JSON.stringify(AITrustContract.inspect(JSON.parse(fs.readFileSync(0,'utf8')))));"
        try:
            result = subprocess.run([node, '-e', program, str(ROOT/'extension/src/shared/contract.js')],
                                    input=raw, capture_output=True, timeout=10, check=True)
            inspected = json.loads(result.stdout)
            if inspected.get('status') not in ('accepted', 'invalid', 'unsupported'):
                return 'unavailable', 'profile_failure'
            return inspected['status'], 'extension_profile'
        except (OSError, ValueError, subprocess.SubprocessError):
            return 'unavailable', 'profile_failure'
    return 'accepted', 'schema_only'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('file', nargs='?', help='Regular UTF-8 JSON file; omit for stdin')
    parser.add_argument('--profile', choices=('schema', 'extension'), default='schema')
    args = parser.parse_args()
    try:
        if args.file:
            path = Path(args.file)
            if path.is_symlink() or not path.is_file():
                raise OSError('Not a regular file')
            with path.open('rb') as stream:
                raw = stream.read(LIMIT + 1)
        else:
            raw = sys.stdin.buffer.read(LIMIT + 1)
        status, reason = check(raw, args.profile)
    except OSError:
        status, reason = 'unavailable', 'input_unavailable'
    print(json.dumps({'status': status, 'reason': reason, 'profile': args.profile,
                      'supported_version': SUPPORTED, 'offline': True,
                      'signature_verified': False, 'independent_accuracy_verified': False,
                      'certification': False}, separators=(',', ':')))
    return {'accepted': 0, 'invalid': 1, 'unsupported': 2, 'unavailable': 3}[status]


if __name__ == '__main__':
    raise SystemExit(main())
