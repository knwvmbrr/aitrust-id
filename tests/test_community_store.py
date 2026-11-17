import copy
import json
from pathlib import Path
import sqlite3
import pytest
from tools import community_core as c
from tools import community_store as s
from tools.blind_review_io import PacketError
from tests.test_community_core import request


def root(tmp_path):
    tmp_path.chmod(0o700); p = tmp_path/'workbench'
    s.initialize(p, synthetic_only=True); return p


def test_store_atomic_role_and_private_namespace_roundtrip(tmp_path):
    p = root(tmp_path); store = s.Store(p)
    a = store.apply('user-one', request('submit', {'body': 'Invented message', 'consent_public': True}), 1000)
    assert store.view('public')['items'] == []
    store.apply('mod-one', request('approve', {'post_id': a['id'], 'version': 1}), 1000)
    assert store.view('public')['items'][0]['body'] == 'Invented message'
    assert p.stat().st_mode & 0o777 == 0o700
    assert all(x.stat().st_mode & 0o777 == 0o600 for x in p.iterdir())
    before = (p/'community.sqlite').read_bytes()
    with pytest.raises(c.Refused): store.apply('user-two', request('edit', {'post_id': a['id'], 'version': 2, 'body': 'PRIVATE_CANARY', 'consent_public': True}), 1000)
    assert (p/'community.sqlite').read_bytes() == before
    assert store.remove(confirm=True)['removed'] and not p.exists()


def test_init_existing_destination_and_missing_consent_refused(tmp_path):
    p = root(tmp_path)
    with pytest.raises((c.Refused, FileExistsError)): s.initialize(p, synthetic_only=True)
    with pytest.raises(c.Refused): s.initialize(tmp_path/'other')
    assert not (tmp_path/'other').exists()


@pytest.mark.parametrize('kind', ['symlink', 'hardlink', 'public_file', 'foreign_member', 'corrupt_schema', 'corrupt_state'])
def test_storage_refuses_links_public_permissions_foreign_files_and_damage(tmp_path, kind):
    p = root(tmp_path); db = p/'community.sqlite'
    if kind == 'symlink':
        db.rename(tmp_path/'actual'); db.symlink_to(tmp_path/'actual')
    elif kind == 'hardlink': __import__('os').link(db, tmp_path/'other')
    elif kind == 'public_file': db.chmod(0o644)
    elif kind == 'foreign_member': (p/'foreign').write_text('PRIVATE_CANARY')
    else:
        connection = sqlite3.connect(db)
        if kind == 'corrupt_schema': connection.execute('CREATE TABLE extra(x TEXT)')
        else: connection.execute('UPDATE community SET payload=?', (b'{"PRIVATE_CANARY":true}',))
        connection.commit(); connection.close()
    with pytest.raises((c.Refused, PacketError, OSError)) as error: s.Store(p).view('public')
    assert 'PRIVATE_CANARY' not in str(error.value)


def test_export_new_private_file_only_never_overwrites(tmp_path):
    tmp_path.chmod(0o700); out = tmp_path/'view.json'; s.export(out, b'{}')
    assert out.stat().st_mode & 0o777 == 0o600
    with pytest.raises(FileExistsError): s.export(out, b'bad')
    assert out.read_bytes() == b'{}'


def test_held_storage_lock_returns_busy_instead_of_hanging(tmp_path):
    import fcntl
    p = root(tmp_path)
    with (p/'access.lock').open('r+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(BlockingIOError): s.Store(p).view('public')


def test_sqlite_capacity_preserves_pause_and_retraction(tmp_path, monkeypatch):
    # Exercise actual overflow pages and a real rollback at a smaller data budget.
    monkeypatch.setattr(s, 'MAX_DB', 64 * 4096)
    p = root(tmp_path)
    store = s.Store(p)
    short = store.apply('user-one', request('submit', {'body': 'x', 'consent_public': True}), 1000)
    store.apply('mod-one', request('approve', {'post_id': short['id'], 'version': 1}), 1000)
    large = {'body': '💬' * 2000, 'consent_public': True}
    db = p / 'community.sqlite'
    for i in range(7):
        before = db.read_bytes()
        try:
            store.apply('user-one', request('submit', large), 1100 + 61 * i)
        except c.Refused:
            assert i >= 4
            assert db.read_bytes() == before
            break
    else:
        pytest.fail('Admitted ordinary writes after reaching the storage reserve')

    with sqlite3.connect(db) as connection:
        raw_before = connection.execute('SELECT length(payload) FROM community').fetchone()[0]
    store.apply('admin-one', request('pause', {'paused': True}), 1500)
    store.apply('mod-one', request('retract', {'post_id': short['id'], 'version': 2, 'reason': 'privacy'}), 1500)
    with sqlite3.connect(db) as connection:
        raw_after = connection.execute('SELECT length(payload) FROM community').fetchone()[0]
    assert raw_after > raw_before
    assert next(row for row in store.view('public')['items'] if row['id'] == short['id'])['body'] is None
    assert db.stat().st_size <= s.MAX_DB


def test_legacy_sqlite_store_over_admission_budget_still_allows_removal(tmp_path, monkeypatch):
    p = root(tmp_path)
    store = s.Store(p)
    short = store.apply('user-one', request('submit', {'body': 'x', 'consent_public': True}), 1000)
    store.apply('mod-one', request('approve', {'post_id': short['id'], 'version': 1}), 1000)
    large = {'body': '💬' * 2000, 'consent_public': True}
    for i in range(5):
        store.apply('user-one', request('submit', large), 1100 + 61 * i)

    # Choose a limit where the existing document fits without its safety reserve.
    db = p / 'community.sqlite'
    with sqlite3.connect(db) as connection:
        packed = connection.execute('SELECT payload FROM community').fetchone()[0]
    limit = len(packed) + 256
    assert len(packed) < limit < len(packed) + s.safety_reserve(c.parse(packed, s.MAX_DB))
    monkeypatch.setattr(s, 'MAX_DB', limit * 2)
    with pytest.raises(c.Refused):
        store.apply('mod-one', request('warn', {'post_id': short['id'], 'version': 2, 'reason': 'conduct'}), 1500)
    store.apply('admin-one', request('pause', {'paused': True}), 1500)
    store.apply('mod-one', request('retract', {'post_id': short['id'], 'version': 2, 'reason': 'privacy'}), 1500)
    assert store.view('public')['items'][0]['state'] == 'retracted'
