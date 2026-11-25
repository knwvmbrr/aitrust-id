#!/usr/bin/env python3
"""Private operator command. Never processes or asserts a customer payment."""
import argparse
import json
from pathlib import Path
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import history_entitlements as access


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('init', 'status', 'grant', 'revoke', 'forget'))
    parser.add_argument('--directory', required=True, type=Path)
    parser.add_argument('--account')
    parser.add_argument('--event', help='Canonical random UUIDv4; reuse only for exact command retries.')
    parser.add_argument('--until', type=int, help='Unix expiry, at most 31 days from now.')
    parser.add_argument('--confirm-delete', action='store_true')
    args = parser.parse_args(); now = int(time.time())
    try:
        if args.operation == 'init':
            access.initialize(args.directory)
            result = {'initialized': True}
        else:
            store = access.HistoryEntitlements(args.directory, clock=lambda: int(time.time()))
            if args.operation == 'status': result = store.assess(args.account, now)
            elif args.operation == 'grant': result = store.grant(args.account, args.event, args.until, now)
            elif args.operation == 'revoke': result = store.revoke(args.account, args.event, now)
            else:
                access.need(args.confirm_delete)
                result = store.forget(args.account, now)
        print(json.dumps({'result': result, 'access_source': 'operator_grant', 'payment_processed': False}, sort_keys=True))
        return 2 if result.get('state') == 'UNAVAILABLE' else 0
    except access.EntitlementUncertain:
        print(json.dumps({'state': 'UNCERTAIN', 'error': 'Inspect current access before submitting another event.', 'payment_processed': False}))
        return 3
    except access.EntitlementInterrupted:
        print(json.dumps({'state': 'UNCERTAIN', 'error': 'Interrupted update may have committed.', 'payment_processed': False}))
        return 130
    except access.EntitlementError:
        print(json.dumps({'error': 'History access operation unavailable.', 'payment_processed': False}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
