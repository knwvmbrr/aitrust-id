"""Private synthetic SQLite workbench, never a production collection destination."""
from contextlib import contextmanager
import fcntl
import os
from pathlib import Path
import sqlite3
import stat
from urllib.parse import quote
from tools.blind_review_io import directory, member, create
from tools import community_core as core

ROOT = Path(__file__).resolve().parents[1]
MAX_DB = 8 * 1024 * 1024
TABLE = 'CREATE TABLE community(singleton INTEGER PRIMARY KEY CHECK(singleton=1),payload BLOB NOT NULL) STRICT'
SENSITIVE = {'.git', '.ssh', '.gnupg', '.aws', '.config', 'library', '.password-store'}


def scope(path):
    p = Path(path).expanduser().absolute()
    core.require(os.geteuid() != 0 and not any(q.is_symlink() for q in (p, *p.parents)))
    real = p.resolve(strict=True)
    core.require(not any(x.lower() in SENSITIVE for x in real.parts))
    core.require(not any((q / '.git').exists() for q in (real, *real.parents)))
    with directory(p, ROOT): pass
    return p


def initialize(path, *, synthetic_only=False):
    core.require(synthetic_only is True); p = Path(path).expanduser().absolute(); scope(p.parent)
    core.require(p.name.lower() not in SENSITIVE)
    db = sqlite3.connect(':memory:')
    try:
        db.execute(TABLE); db.execute('INSERT INTO community VALUES(1,?)', (core.encode(core.initial()),)); db.commit()
        raw = db.serialize()
    finally: db.close()
    create(p, ROOT, {'community.sqlite': raw, 'access.lock': b''})
    return {'initialized': True, 'synthetic_only': True, 'public_service_enabled': False, 'research_collection_enabled': False}


class Store:
    def __init__(self, path): self.path = Path(path).expanduser().absolute()

    @contextmanager
    def transaction(self):
        scope(self.path)
        with directory(self.path, ROOT) as fd:
            lock = os.open('access.lock', os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
            db = None
            try:
                info = os.fstat(lock)
                core.require(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid() and info.st_nlink == 1 and not info.st_mode & 0o077 and info.st_size == 0)
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                core.require(set(os.listdir(fd)) <= {'access.lock', 'community.sqlite', 'community.sqlite-journal'} and 'community.sqlite' in os.listdir(fd))
                for name in os.listdir(fd): member(fd, name, MAX_DB)
                held = os.fstat(fd); current = self.path.stat(follow_symlinks=False)
                core.require((held.st_dev, held.st_ino) == (current.st_dev, current.st_ino))
                db = sqlite3.connect('file:' + quote(str(self.path / 'community.sqlite'), safe='/') + '?mode=rw', uri=True, timeout=1)
                db.execute('PRAGMA trusted_schema=OFF'); db.execute('PRAGMA temp_store=MEMORY'); db.execute('PRAGMA secure_delete=ON')
                db.execute('PRAGMA max_page_count=2048')
                core.require(db.execute('PRAGMA journal_mode=DELETE').fetchone()[0] == 'delete')
                db.execute('BEGIN IMMEDIATE')
                schema = db.execute("SELECT type,name,sql FROM sqlite_schema WHERE name NOT GLOB 'sqlite_*'").fetchall()
                core.require(schema == [('table', 'community', TABLE)])
                rows = db.execute('SELECT singleton,payload FROM community').fetchall()
                core.require(len(rows) == 1 and rows[0][0] == 1 and type(rows[0][1]) is bytes)
                engine = core.Community(core.parse(rows[0][1], MAX_DB))
                yield engine
                raw = core.encode(core.validate(engine.state)); core.require(len(raw) < MAX_DB // 2)
                db.execute('UPDATE community SET payload=? WHERE singleton=1', (raw,))
                current = self.path.stat(follow_symlinks=False)
                core.require((held.st_dev, held.st_ino) == (current.st_dev, current.st_ino)); db.commit()
            except BaseException:
                if db is not None: db.rollback()
                raise
            finally:
                if db is not None: db.close()
                os.close(lock)

    def apply(self, actor, request, now):
        with self.transaction() as engine: return engine.apply(actor, request, now)

    def view(self, operation, **kwargs):
        core.require(operation in ('public', 'replay', 'private', 'audit'))
        with self.transaction() as engine: return getattr(engine, operation)(**kwargs)

    def remove(self, *, confirm=False):
        core.require(confirm is True)
        with self.transaction(): pass
        with directory(self.path, ROOT) as fd:
            lock = os.open('access.lock', os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                core.require(set(os.listdir(fd)) == {'access.lock', 'community.sqlite'})
                for name in os.listdir(fd): member(fd, name, MAX_DB)
                held = os.fstat(fd); current = self.path.stat(follow_symlinks=False)
                core.require((held.st_dev, held.st_ino) == (current.st_dev, current.st_ino))
                os.unlink('community.sqlite', dir_fd=fd); os.unlink('access.lock', dir_fd=fd); os.fsync(fd); self.path.rmdir()
            finally: os.close(lock)
        return {'removed': True, 'synthetic_only': True, 'external_copies_removed': False}


def export(path, raw):
    p = Path(path).expanduser().absolute(); scope(p.parent)
    core.require(type(raw) is bytes and len(raw) <= MAX_DB)
    with directory(p.parent, ROOT) as fd:
        output = os.open(p.name, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600, dir_fd=fd)
        with os.fdopen(output, 'wb') as stream: stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        os.fsync(fd)
