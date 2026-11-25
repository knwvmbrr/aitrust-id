"""Owned loopback PostgreSQL review runner using the same approved account app."""
import argparse
import json
from pathlib import Path
import sys
import time

from tools import account_core as c
from tools.account_postgres import PostgresAccountStore
from services.accounts.app import create_app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', type=Path, required=True)
    parser.add_argument('--origin', default='http://127.0.0.1:18791')
    parser.add_argument('--port', type=int, default=18791)
    parser.add_argument('--review-http', action='store_true', help='Explicit loopback-only synthetic review; never public collection.')
    parser.add_argument('--entitlements', type=Path)
    parser.add_argument('--retry-entitlement-cleanup', action='store_true', help='Bounded operator retry; does not serve HTTP or grant access.')
    args = parser.parse_args()
    try:
        c.need(args.port == 18791 and args.review_http and args.origin == 'http://127.0.0.1:18791')
        store = PostgresAccountStore(args.profile)
        def unavailable(account_id, now):
            return {'format': 'account-history-entitlement/v1', 'account_id': account_id,
                    'state': 'UNAVAILABLE', 'valid_until': None, 'revision': 0}
        assess, forget = unavailable, None
        if args.entitlements is not None:
            from tools.history_entitlements import HistoryEntitlements
            access = HistoryEntitlements(args.entitlements, clock=lambda: int(time.time()))
            assess, forget = access.assess, access.forget
        if args.retry_entitlement_cleanup:
            result = store.retry_cleanup(forget, lambda: int(time.time()))
            print(json.dumps(result, sort_keys=True))
            return 0
        app = create_app(store, origin=args.origin, host='127.0.0.1:18791', entitlement=assess,
                         entitlement_forget=forget, secure_cookie=False)
        import uvicorn
        uvicorn.run(app, host='127.0.0.1', port=args.port, loop='asyncio', http='h11', ws='none',
                    access_log=False, log_level='error', proxy_headers=False, server_header=False,
                    limit_concurrency=32, timeout_keep_alive=5, timeout_graceful_shutdown=5)
        return 0
    except Exception:
        print(json.dumps({'state': 'UNAVAILABLE', 'public_service_enabled': False}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
