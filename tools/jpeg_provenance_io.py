"""JPEG-only bounded descriptor snapshots; no input/result storage or sibling import."""
import hashlib
import os
from pathlib import Path
import stat


class Refused(ValueError):
    def __init__(self, reason='unavailable'):
        self.reason = reason
        super().__init__('JPEG credential inspection unavailable.')


def need(value, reason='unavailable'):
    if not value:
        raise Refused(reason)


def identity(info):
    return info.st_dev, info.st_ino, info.st_mode


def snapshot(info):
    return identity(info)+(info.st_nlink, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


class Source:
    """One regular file plus no-follow ancestors, rechecked after native work."""
    def __init__(self, path, limit):
        self.fds, self.parents, self.file = [], [], None
        self.path, self.limit = Path(path).absolute(), limit
        need(type(limit) is int and 0 < limit <= 40*1024*1024 and '..' not in self.path.parts
             and 1 < len(self.path.parts) <= 128 and len(str(self.path)) <= 4096
             and '://' not in str(path), 'input_unavailable')

    def __enter__(self):
        try:
            flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_NONBLOCK
            parent = os.open(self.path.anchor, flags)
            self.fds.append(parent)
            for part in self.path.parts[1:-1]:
                child = os.open(part, flags, dir_fd=parent)
                self.fds.append(child)
                info = os.fstat(child)
                need(stat.S_ISDIR(info.st_mode), 'input_unavailable')
                self.parents.append((parent, part, child, identity(info)))
                parent = child
            fd = os.open(self.path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
            self.fds.append(fd)
            info = os.fstat(fd)
            need(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, 'input_unavailable')
            need(0 < info.st_size <= self.limit, 'input_limit')
            raw = bytearray()
            while len(raw) <= self.limit:
                block = os.read(fd, min(65536, self.limit+1-len(raw)))
                if not block:
                    break
                raw.extend(block)
            need(len(raw) == info.st_size <= self.limit and snapshot(info) == snapshot(os.fstat(fd)), 'input_changed')
            self.file = parent, self.path.name, fd, snapshot(info)
            self.raw = bytes(raw)
            self.sha256 = hashlib.sha256(self.raw).hexdigest()
            self.check()
            return self
        except BaseException:
            self.close()
            raise

    def check(self):
        for parent, name, fd, expected in self.parents:
            need(identity(os.fstat(fd)) == expected == identity(os.stat(name, dir_fd=parent, follow_symlinks=False)), 'input_changed')
        if self.file:
            parent, name, fd, expected = self.file
            need(snapshot(os.fstat(fd)) == expected == snapshot(os.stat(name, dir_fd=parent, follow_symlinks=False)), 'input_changed')

    def close(self):
        owned, self.fds = self.fds, []
        failure = False
        for fd in reversed(owned):
            try:
                os.close(fd)
            except BaseException:
                failure = True
        need(not failure, 'input_unavailable')

    def __exit__(self, kind, value, trace):
        try:
            if kind is None:
                self.check()
        finally:
            self.close()
