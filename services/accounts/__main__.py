"""Loopback development/review runner; no provider setup or production activation."""
import argparse
import json
import sys
import time
from pathlib import Path

from services.accounts.app import create_app
from tools.account_store import AccountStore, initialize


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--store', type=Path, required=True)
    parser.add_argument('--origin', required=True)
    parser.add_argument('--port', type=int, default=8791)
    parser.add_argument('--init', action='store_true')
    parser.add_argument('--dev-http', action='store_true', help='Explicit loopback-only HTTP cookie mode.')
    parser.add_argument('--entitlements', type=Path)
    parser.add_argument('--asset-directory', type=Path, help='Trusted operator-only account UI source directory.')
    parser.add_argument('--retry-entitlement-cleanup', action='store_true')
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error('Invalid review port.')
    try:
        store = initialize(args.store) if args.init else AccountStore(args.store)
        def unavailable(account_id, now):
            return {'format': 'account-history-entitlement/v1', 'account_id': account_id,
                    'state': 'UNAVAILABLE', 'valid_until': None, 'revision': 0}
        assess, forget = unavailable, None
        if args.entitlements is not None:
            from tools.history_entitlements import HistoryEntitlements
            engine = HistoryEntitlements(args.entitlements, clock=lambda: int(time.time()))
            assess, forget = engine.assess, engine.forget
        if args.retry_entitlement_cleanup:
            result = store.retry_cleanup(forget, lambda: int(time.time()))
            print(json.dumps(result, sort_keys=True))
            return 0
        app = create_app(store, origin=args.origin, host='127.0.0.1:' + str(args.port),
                         entitlement=assess, entitlement_forget=forget, secure_cookie=not args.dev_http,
                         asset_directory=args.asset_directory)
        import uvicorn
        uvicorn.run(app, host='127.0.0.1', port=args.port, access_log=False,
                    log_level='warning', proxy_headers=False, server_header=False,
                    limit_concurrency=32, timeout_keep_alive=5, timeout_graceful_shutdown=5)
        return 0
    except Exception:
        print('Account development service unavailable; private state may remain.', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
