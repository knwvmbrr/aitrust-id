#!/usr/bin/env python3
"""Choose an installed runtime that explicitly supports the declared test phone."""
import json
import re
import sys

PHONE = 'com.apple.CoreSimulator.SimDeviceType.iPhone-14-Plus'


def select(value):
    if not isinstance(value, dict) or not isinstance(value.get('runtimes'), list):
        raise ValueError('Runtime inventory required')
    compatible = []
    for row in value['runtimes']:
        if not isinstance(row, dict) or row.get('isAvailable') is not True:
            continue
        identity, version = row.get('identifier'), row.get('version')
        if (not isinstance(identity, str) or len(identity) > 160
                or not re.fullmatch(r'com\.apple\.CoreSimulator\.SimRuntime\.iOS-[A-Za-z0-9-]+', identity)
                or not isinstance(version, str) or not re.fullmatch(r'\d{1,3}(?:\.\d{1,3}){1,2}', version)):
            continue
        types = row.get('supportedDeviceTypes')
        if not isinstance(types, list) or not any(isinstance(t, dict) and t.get('identifier') == PHONE for t in types):
            continue
        numbers = tuple(map(int, version.split('.')))
        if numbers[0] >= 18:
            compatible.append((numbers, identity))
    if not compatible:
        raise ValueError('No compatible installed runtime')
    return max(compatible)[1]


if __name__ == '__main__':
    try:
        raw = sys.stdin.buffer.read(1_048_577)
        if len(raw) > 1_048_576: raise ValueError('Runtime inventory exceeds limit')
        print(select(json.loads(raw)))
    except (ValueError, TypeError, OSError):
        print('No available iOS runtime advertises iPhone 14 Plus support.', file=sys.stderr)
        raise SystemExit(2)
