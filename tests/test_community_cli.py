import json
import os
from pathlib import Path
import subprocess
import sys
import uuid
import pytest
from tools import community_core as c

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT/'scripts/community-workbench.py'


def call(*args, payload=None, good=True):
    proc = subprocess.run([sys.executable, str(CLI), *map(str, args)], input=payload, capture_output=True, timeout=6)
    assert proc.returncode == (0 if good else 2)
    if good: assert not proc.stderr; return json.loads(proc.stdout)
    assert not proc.stdout and b'PRIVATE_CANARY' not in proc.stderr and b'Traceback' not in proc.stderr
    return None


def req(op, data):
    return c.encode({'format': c.REQUEST, 'synthetic_only': True, 'request_id': str(uuid.uuid4()), 'operation': op, 'data': data})


def test_actual_cli_two_users_moderation_private_report_retraction_export_and_removal(tmp_path):
    tmp_path.chmod(0o700); store = tmp_path/'community'
    call('init', '--root', store, '--synthetic-only')
    a = call('apply', '--root', store, '--actor', 'user-one', payload=req('submit', {'body': '<script>PUBLIC_CANARY</script>', 'consent_public': True}))
    b = call('apply', '--root', store, '--actor', 'user-two', payload=req('submit', {'body': 'SECOND_PRIVATE_CANARY', 'consent_public': True}))
    assert call('public', '--root', store)['items'] == []
    a = call('apply', '--root', store, '--actor', 'mod-one', payload=req('approve', {'post_id': a['id'], 'version': 1}))
    private_report = call('apply', '--root', store, '--actor', 'user-two', payload=req('report', {'target_id': b['id'], 'category': 'privacy', 'consent_private_metadata': True}))
    public = call('public', '--root', store)
    assert b['id'] not in json.dumps(public) and private_report['id'] not in json.dumps(public)
    assert 'SECOND_PRIVATE_CANARY' not in json.dumps(call('replay', '--root', store))
    out = tmp_path/'public.html'; call('export', '--root', store, '--output', out, '--html')
    assert '&lt;script&gt;' in out.read_text() and '<script>' not in out.read_text()
    a = call('apply', '--root', store, '--actor', 'mod-one', payload=req('retract', {'post_id': a['id'], 'version': a['version'], 'reason': 'privacy'}))
    assert 'PUBLIC_CANARY' not in json.dumps(call('replay', '--root', store))
    newer = tmp_path/'current.json'; call('export', '--root', store, '--output', newer)
    assert 'PUBLIC_CANARY' not in newer.read_text()
    call('export', '--root', store, '--output', newer, good=False)
    call('remove', '--root', store, '--confirm-synthetic-removal')
    assert not store.exists() and out.exists() and newer.exists()


def test_cli_fixed_errors_do_not_echo_bad_request_or_database_path(tmp_path):
    tmp_path.chmod(0o700); store = tmp_path/'community'; call('init', '--root', store, '--synthetic-only')
    for raw in [b'{"PRIVATE_CANARY":true}', b'\xff', b' '*16385]:
        call('apply', '--root', store, '--actor', 'user-one', payload=raw, good=False)
    call('public', '--root', tmp_path/'PRIVATE_CANARY-missing', good=False)


def test_no_network_import_or_tag_service_is_needed_for_cli(tmp_path):
    tmp_path.chmod(0o700); store = tmp_path/'community'
    # Execute through the real entry point while every attempted socket is fatal.
    command = 'import socket,runpy,sys; socket.socket=lambda *a,**k: (_ for _ in ()).throw(RuntimeError("NETWORK_FORBIDDEN")); sys.argv='+repr([str(CLI),'init','--root',str(store),'--synthetic-only'])+'; runpy.run_path('+repr(str(CLI))+',run_name="__main__")'
    proc = subprocess.run([sys.executable,'-c',command],capture_output=True,timeout=6)
    assert proc.returncode == 0 and not proc.stderr and json.loads(proc.stdout)['public_service_enabled'] is False
