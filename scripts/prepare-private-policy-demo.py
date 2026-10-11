#!/usr/bin/env python3
"""Prepare an invented optional policy example; never read an owner's messages."""
import argparse
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import private_policy
from tools.blind_review_io import create, PacketError


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--output', type=Path, required=True)
    a = p.parse_args(argv)
    try:
        text = 'A fictional team writes: confidential draft.'
        record = {'format': private_policy.POLICY, 'namespace': 'example-team', 'policy_id': 'draft-terms',
                  'revision': 1, 'claim': 'literal_term_occurrence_only', 'limits_visible': True,
                  'receipts_optional': True, 'personal_checks_separate': True,
                  'rules': [{'code': 'DRAFT', 'terms': ['confidential draft']}]}
        raw = (json.dumps(record, indent=2) + '\n').encode()
        selection = {'format': private_policy.CONTEXT, 'namespace': record['namespace'],
                     'policy_sha256': private_policy.sha(raw),
                     'subject_sha256': private_policy.sha(text.encode())}
        private_policy.observe(text, raw, selection, reviewed=True)
        create(a.output, ROOT, {'subject.txt': text.encode(), 'policy.json': raw,
                               'selection.json': (json.dumps(selection, indent=2) + '\n').encode()})
        print(json.dumps({'created': True, 'synthetic_only': True, 'user_example_read': False,
                          'next_step': 'Read policy.json; if you agree to this local practice check, run check-private-policy.py with --packet and --reviewed-policy.',
                          'public_tag_asserted': False, 'standard_namespace_adopted': False}))
        return 0
    except (ValueError, OSError, TypeError, KeyError, RuntimeError, PacketError):
        print('Practice preparation unavailable; choose a new owner-private folder outside the checkout.', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
