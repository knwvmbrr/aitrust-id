"""Organization-owned private I/O adapted from the audited descriptor primitive.

Provenance: tools/nf_private_io.py at e828705 (SHA256 a45b077bccb618c891b0ad88133dc1644781d0146dc046fc6c4fe01d71834902).
No sibling tag import. Retains raw-fd ownership, all-close attempts, no-overwrite
publication and explicit post-publication uncertainty. Private paths deny every
Git ancestor and require the immediate owner-private parent.
"""
import hashlib
import json
import os
from pathlib import Path
import secrets
import stat
from protocol import corpus

ROOT = Path(__file__).absolute().parents[1]


class PrivateInputError(ValueError):
    """Refusals never include caller-controlled values."""


class OutputCommitUncertain(PrivateInputError):
    """A complete final output may exist; inspect it before attempting another write."""
    output_may_exist = True

    def __init__(self):
        super().__init__('Organization policy output commit uncertain.')


def need(condition):
    if not condition:
        raise PrivateInputError('Organization policy unavailable.')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':'),
                      allow_nan=False).encode('ascii')


def snapshot(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink, info.st_size,
            info.st_mtime_ns, info.st_ctime_ns)


def identity(info):
    return info.st_dev, info.st_ino, info.st_mode


class Capture:
    """Retain no-follow directory/file handles and recheck before publication."""
    def __init__(self):
        self.fds = []
        self.directories = []
        self.files = []
        self.output_may_exist = False
        self.directory_cache = {}
        self.closed = False

    def parent(self, path, private=True):
        need(not self.closed)
        path = Path(path).absolute()
        need('..' not in path.parts and path.name not in ('', '.', '..'))
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_NONBLOCK
        key = (path.anchor,)
        if key not in self.directory_cache:
            fd = os.open(path.anchor, flags)
            self.fds.append(fd)
            self.directory_cache[key] = (fd, identity(os.fstat(fd)))
        fd, expected = self.directory_cache[key]
        need(identity(os.fstat(fd)) == expected)
        for part in path.parts[1:-1]:
            key = (*key, part)
            if key not in self.directory_cache:
                child = os.open(part, flags, dir_fd=fd)
                self.fds.append(child)
                info = os.fstat(child)
                need(stat.S_ISDIR(info.st_mode))
                self.directory_cache[key] = (child, identity(info))
                self.directories.append((fd, part, child, identity(info)))
            child, expected = self.directory_cache[key]
            need(identity(os.fstat(child)) == expected == identity(os.stat(part, dir_fd=fd, follow_symlinks=False)))
            fd = child
            if private:
                try:
                    os.stat('.git', dir_fd=fd, follow_symlinks=False)
                except FileNotFoundError:
                    pass
                else:
                    raise PrivateInputError('Organization policy unavailable.')
        if private:
            info = os.fstat(fd)
            need(info.st_uid == os.getuid() and stat.S_IMODE(info.st_mode) == 0o700)
        return fd, path.name

    def read(self, path, limit, private=True):
        need(type(limit) is int and 0 < limit <= corpus.MAX_STORE_BYTES)
        if private:
            need(not Path(path).absolute().is_relative_to(ROOT))
        parent, name = self.parent(path, private=private)
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        self.fds.append(fd)
        before = os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and 0 < before.st_size <= limit)
        if private:
            need(before.st_uid == os.getuid() and stat.S_IMODE(before.st_mode) == 0o600)
        raw = bytearray()
        while len(raw) <= limit:
            chunk = os.read(fd, min(65536, limit + 1 - len(raw)))
            if not chunk:
                break
            raw.extend(chunk)
        need(len(raw) == before.st_size and snapshot(before) == snapshot(os.fstat(fd)))
        self.files.append((parent, name, fd, snapshot(before)))
        return bytes(raw)

    def directory(self, path):
        path = Path(path).absolute()
        parent, name = self.parent(path)
        key = path.parts
        if key not in self.directory_cache:
            fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_NONBLOCK,
                         dir_fd=parent)
            self.fds.append(fd)
            self.directory_cache[key] = (fd, identity(os.fstat(fd)))
            self.directories.append((parent, name, fd, identity(os.fstat(fd))))
        fd, expected = self.directory_cache[key]
        info = os.fstat(fd)
        need(identity(info) == expected == identity(os.stat(name, dir_fd=parent, follow_symlinks=False)))
        need(stat.S_ISDIR(info.st_mode) and info.st_uid == os.getuid()
             and stat.S_IMODE(info.st_mode) == 0o700)
        try:
            os.stat('.git', dir_fd=fd, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise PrivateInputError('Organization policy unavailable.')
        return fd

    def check(self):
        for parent, name, fd, expected in self.directories:
            need(identity(os.fstat(fd)) == expected == identity(os.stat(name, dir_fd=parent, follow_symlinks=False)))
        for parent, name, fd, expected in self.files:
            need(snapshot(os.fstat(fd)) == expected == snapshot(os.stat(name, dir_fd=parent, follow_symlinks=False)))

    def save(self, output, value, limit):
        path = Path(output).absolute()
        need(not path.is_relative_to(ROOT))
        raw = encoded(value) + b'\n'
        need(len(raw) <= limit)
        parent, name = self.parent(path)
        info = os.fstat(parent)
        need(info.st_uid == os.getuid() and stat.S_IMODE(info.st_mode) == 0o700)
        # Never follow or replace even a dangling existing destination.
        try:
            os.stat(name, dir_fd=parent, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise PrivateInputError('Organization policy evidence unavailable.')
        temporary = '.org-policy-' + secrets.token_hex(16)
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o600, dir_fd=parent)
        self.fds.append(fd)
        error = None
        may_exist = False
        try:
            # Capture alone owns the raw handle, including construction failure.
            with os.fdopen(fd, 'wb', closefd=False) as stream:
                os.fchmod(stream.fileno(), 0o600)
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            self.check()
            # Atomic no-replace publication of complete bytes. An unexpected
            # link error can itself have an uncertain filesystem outcome.
            try:
                os.link(temporary, name, src_dir_fd=parent, dst_dir_fd=parent, follow_symlinks=False)
            except FileExistsError:
                raise
            except BaseException:
                may_exist = self.output_may_exist = True
                raise
            may_exist = self.output_may_exist = True
        except BaseException as failure:
            error = failure
        # Attempt temporary cleanup exactly once. Never remove a final file or
        # assert rollback after crossing the publication boundary.
        try:
            os.unlink(temporary, dir_fd=parent)
        except BaseException as failure:
            if error is None:
                error = failure
        if error is None and may_exist:
            try:
                os.fsync(parent)
            except BaseException as failure:
                error = failure
        if error is not None:
            if may_exist:
                raise OutputCommitUncertain() from None
            raise error

    def close(self):
        self.closed = True
        self.directory_cache = {}
        owned = self.fds
        self.fds = []
        error = None
        for fd in reversed(owned):
            try:
                os.close(fd)
            except BaseException as failure:
                if error is None:
                    error = failure
        if error is not None:
            if self.output_may_exist:
                raise OutputCommitUncertain() from None
            raise PrivateInputError('Organization policy evidence unavailable.') from None

    def __enter__(self):
        return self

    def __exit__(self, kind, value, traceback):
        try:
            self.close()
        except BaseException:
            if self.output_may_exist:
                raise OutputCommitUncertain() from None
            if kind is None:
                raise
            # Keep a primary pre-publication refusal. All closes were attempted.
            return False
        if kind is not None and self.output_may_exist:
            raise OutputCommitUncertain() from None


