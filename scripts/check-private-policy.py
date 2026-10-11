#!/usr/bin/env python3
"""Apply a reviewed local literal policy to selected text; no upload or public tag changes."""
import argparse
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import private_policy
from tools.blind_review_io import source, create, PacketError


class Parser(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, 'Policy command refused; use --help for the required private packet and review choice.\n')


def main(argv=None):
    p = Parser(description=__doc__)
    p.add_argument('--packet', type=Path, required=True)
    p.add_argument('--reviewed-policy', action='store_true', help='Run only after you inspect the selected policy.')
    p.add_argument('--details', type=Path, help='Optional new private folder; never overwrite.')
    a = p.parse_args(argv)
    try:
        if a.reviewed_policy is not True:
            raise ValueError('Review and deliberate invocation required')
        subject = source(a.packet / 'subject.txt', ROOT, 80_000).decode('utf-8', 'strict')
        raw = source(a.packet / 'policy.json', ROOT, 65_536)
        context = private_policy.parse(source(a.packet / 'selection.json', ROOT, 4096))
        result = private_policy.observe(subject, raw, context, reviewed=True)
        if a.details:
            create(a.details, ROOT, {'private-policy-observations.json':
                                    (json.dumps(result, indent=2, allow_nan=False) + '\n').encode()})
        print(json.dumps({'profile': result['profile'], 'state': result['state'],
                          'literal_occurrences': result['total_observations'],
                          'result': 'Selected literal terms occur in this text. Review the context; this is not a policy-violation verdict.'
                          if result['total_observations'] else 'No selected literal term matched. This does not establish compliance.',
                          'detailed_output_saved': a.details is not None,
                          'public_assertions_processed': False, 'public_tag_asserted': False,
                          'standard_namespace_adopted': False, 'compliance_established': False}))
        return 0
    except (ValueError, OSError, KeyError, TypeError, RuntimeError, RecursionError, PacketError):
        print(json.dumps({'state': 'UNAVAILABLE', 'reason': 'invalid_private_policy_or_bound_selection',
                          'next_step': 'Check the policy, private file permissions, selection fingerprints and limits.',
                          'public_tag_asserted': False}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
