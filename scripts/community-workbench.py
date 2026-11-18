#!/usr/bin/env python3
"""Run invented moderation cases locally. No public posting, service or research intake."""
import argparse
import json
import sys
import subprocess
import time
from pathlib import Path
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from tools import community_core as core
from tools import community_store as storage


class Parser(argparse.ArgumentParser):
    def error(self, message): self.exit(2, 'Community workbench refused; use --help.\n')


def main(argv=None):
    p = Parser(description=__doc__); sub = p.add_subparsers(dest='command', required=True)
    for name in ('init', 'apply', 'public', 'replay', 'private', 'audit', 'export', 'remove'):
        q = sub.add_parser(name); place = q.add_mutually_exclusive_group(required=True)
        place.add_argument('--root'); place.add_argument('--sandbox-dir', help='Existing disposable synthetic PostgreSQL18 cluster only; never production.')
        if name == 'init': q.add_argument('--synthetic-only', action='store_true')
        if name in ('apply', 'private', 'audit'): q.add_argument('--actor', choices=sorted(core.ACTORS), required=True)
        if name in ('public', 'replay'): q.add_argument('--after', type=int, default=0); q.add_argument('--limit', type=int, default=20)
        if name == 'export': q.add_argument('--output', required=True); q.add_argument('--html', action='store_true')
        if name == 'remove': q.add_argument('--confirm-synthetic-removal', action='store_true')
    a = p.parse_args(argv)
    try:
        if a.sandbox_dir:
            from tools.community_postgres import Postgres
            store = Postgres(a.sandbox_dir)
        else:
            store = storage.Store(a.root)
        if a.command == 'init':
            value = store.install(synthetic_only=a.synthetic_only) if a.sandbox_dir else storage.initialize(a.root, synthetic_only=a.synthetic_only)
        else:
            if a.command == 'apply':
                raw = sys.stdin.buffer.read(16385); request = core.parse(raw)
                value = store.apply(a.actor, request, int(time.time()))
            elif a.command in ('public', 'replay'): value = store.view(a.command, after=a.after, limit=a.limit)
            elif a.command in ('private', 'audit'): value = store.view(a.command, actor=a.actor)
            elif a.command == 'export':
                projection = store.view('public')
                # A single export is deliberately bounded; never silently truncate.
                while projection['next_page'] is not None:
                    page = store.view('public', after=projection['next_page'])
                    core.require(page['sequence'] == projection['sequence'])
                    projection['items'] += page['items']; projection['next_page'] = page['next_page']
                storage.export(a.output, core.render(projection).encode() if a.html else core.encode(projection))
                value = {'exported': True, 'synthetic_only': True, 'public_projection_only': True, 'saved_copies_recallable': False}
            else:
                core.require(not a.sandbox_dir)
                value = store.remove(confirm=a.confirm_synthetic_removal)
        print(json.dumps(value, ensure_ascii=True, allow_nan=False)); return 0
    except (ValueError, OSError, TypeError, KeyError, RuntimeError, RecursionError, ImportError, SyntaxError, subprocess.SubprocessError, __import__('sqlite3').Error):
        print('{"state":"Unavailable","synthetic_only":true,"public_service_enabled":false}', file=sys.stderr); return 2


if __name__ == '__main__': raise SystemExit(main())
