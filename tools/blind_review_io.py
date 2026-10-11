"""Bounded owner-only offline packet files. No network or detector execution."""
from contextlib import contextmanager
import os
from pathlib import Path
import stat

class PacketError(ValueError):
    """Fixed diagnostics do not include private paths or example values."""


def _platform():
    if (not hasattr(os, 'O_NOFOLLOW') or not hasattr(os, 'O_DIRECTORY')
            or os.open not in os.supports_dir_fd or os.stat not in os.supports_dir_fd
            or os.unlink not in os.supports_dir_fd or os.mkdir not in os.supports_dir_fd
            or os.rmdir not in os.supports_dir_fd):
        raise PacketError('Private packet file safety is unavailable on this platform.')


def _private_directory(info):
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise PacketError('Use an owner-held private directory with mode 0700.')


def _identity(info):
    return info.st_dev, info.st_ino


@contextmanager
def directory(path, root):
    _platform()
    path = Path(path).expanduser().absolute()
    try:
        if path.is_symlink():
            raise PacketError('Private packet directory symlinks are refused.')
        resolved = path.resolve(strict=True)
        if resolved.is_relative_to(Path(root).resolve()):
            raise PacketError('Keep private review material outside the source checkout.')
        expected = resolved.stat(follow_symlinks=False)
        fd = os.open(resolved, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    except (OSError, RuntimeError):
        raise PacketError('Cannot open the private review directory.') from None
    try:
        info = os.fstat(fd)
        _private_directory(info)
        if _identity(info) != _identity(expected):
            raise PacketError('Private directory changed during access.')
        yield fd
    finally:
        os.close(fd)


def member(fd, name, limit):
    if not isinstance(name, str) or Path(name).name != name or name in ('', '.', '..'):
        raise PacketError('Only a fixed private packet member is supported.')
    try:
        file_fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
    except OSError:
        raise PacketError('Cannot open the private packet member.') from None
    try:
        info = os.fstat(file_fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or info.st_mode & 0o077 or info.st_nlink != 1):
            raise PacketError('Packet members must be private owner-held regular files with one link.')
        if info.st_size > limit:
            raise PacketError('Review input exceeds its byte limit.')
    except BaseException:
        os.close(file_fd)
        raise
    try:
        stream = os.fdopen(file_fd, 'rb')
    except BaseException:
        os.close(file_fd)
        raise
    with stream:
        raw = stream.read(limit + 1)
        after = os.fstat(stream.fileno())
        if len(raw) > limit:
            raise PacketError('Review input exceeds its byte limit.')
        if (info.st_size, info.st_mtime_ns, info.st_ctime_ns) != (after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            raise PacketError('Private input changed during access.')
    return raw


def source(path, root, limit):
    path = Path(path).expanduser().absolute()
    with directory(path.parent, root) as fd:
        return member(fd, path.name, limit)


def create(path, root, files):
    if not isinstance(files, dict) or not files or any(not isinstance(name, str) or Path(name).name != name or name in ('', '.', '..') or not isinstance(raw, bytes) for name, raw in files.items()):
        raise PacketError('Only fixed packet members can be created.')
    path = Path(path).expanduser().absolute()
    if path.resolve().is_relative_to(Path(root).resolve()):
        raise PacketError('Keep private review material outside the source checkout.')
    with directory(path.parent, root) as parent:
        # Existing destinations, including links, are never opened or modified.
        os.mkdir(path.name, mode=0o700, dir_fd=parent)
        original = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
        fd = None
        owned = {}
        try:
            fd = os.open(path.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            _private_directory(os.fstat(fd))
            if _identity(os.fstat(fd)) != _identity(original):
                raise PacketError('New private packet directory changed.')
            for name, raw in files.items():
                if Path(name).name != name or name in ('', '.', '..') or not isinstance(raw, bytes):
                    raise PacketError('Only fixed packet members can be created.')
                output = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                                 0o600, dir_fd=fd)
                owned[name] = _identity(os.fstat(output))
                with os.fdopen(output, 'wb') as handle:
                    handle.write(raw)
                    handle.flush()
                    os.fsync(handle.fileno())
            if set(os.listdir(fd)) != set(files):
                raise PacketError('New private packet contains an unexpected member.')
            for name, identity in owned.items():
                if _identity(os.stat(name, dir_fd=fd, follow_symlinks=False)) != identity or member(fd, name, len(files[name])) != files[name]:
                    raise PacketError('New private packet member changed.')
            _private_directory(os.fstat(fd))
            if _identity(os.stat(path.name, dir_fd=parent, follow_symlinks=False)) != _identity(original):
                raise PacketError('New private packet directory changed.')
            os.fsync(fd)
            os.fsync(parent)
        except BaseException:
            if fd is not None:
                for name, identity in owned.items():
                    try:
                        if _identity(os.stat(name, dir_fd=fd, follow_symlinks=False)) == identity:
                            os.unlink(name, dir_fd=fd)
                    except OSError:
                        pass
            try:
                if _identity(os.stat(path.name, dir_fd=parent, follow_symlinks=False)) == _identity(original):
                    os.rmdir(path.name, dir_fd=parent)
            except OSError:
                pass
            raise
        finally:
            if fd is not None:
                os.close(fd)
