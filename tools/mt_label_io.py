"""MT-owned private packet IO, adapted from foundational migration Capture.

No sibling tag import. Exact raw descriptor ownership, no overwrite and honest
post-publication uncertainty; this is not crash-atomic directory publication.
"""
import os
from pathlib import Path
import stat

ROOT=Path(__file__).absolute().parents[1]
MAX_BYTES=8*1024*1024


class Refused(ValueError):
    def __init__(self):super().__init__('MT label preparation unavailable.')


class OutputUncertain(Refused):
    output_may_exist=True
    def __init__(self):ValueError.__init__(self,'Private output may remain; do not use it as accepted evidence.')


def need(ok):
    if not ok:raise Refused()


def identity(s):return s.st_dev,s.st_ino,s.st_mode

def snapshot(s):return (*identity(s),s.st_nlink,s.st_size,s.st_mtime_ns,s.st_ctime_ns)


class Capture:
    def __init__(self):
        self.fds=[];self.directories=[];self.files=[];self.private_directories=[];self.output_may_exist=False

    def opened(self,*args,**kwargs):
        need(len(self.fds)<256)
        fd=os.open(*args,**kwargs);self.fds.append(fd);return fd

    def parent(self,path,private):
        need(all(hasattr(os,n) for n in ('O_DIRECTORY','O_NOFOLLOW','O_NONBLOCK','getuid')))
        path=Path(path).absolute()
        need('..' not in path.parts and 1<len(path.parts)<=128 and len(str(path))<=4096)
        flags=os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_NONBLOCK
        fd=self.opened(path.anchor,flags)
        def outside(directory):
            if private:
                try:os.stat('.git',dir_fd=directory,follow_symlinks=False)
                except FileNotFoundError:return
                raise Refused()
        outside(fd)
        if private:self.private_directories.append(fd)
        for part in path.parts[1:-1]:
            child=self.opened(part,flags,dir_fd=fd)
            info=os.fstat(child);need(stat.S_ISDIR(info.st_mode));outside(child)
            if private:self.private_directories.append(child)
            self.directories.append((fd,part,child,identity(info)));fd=child
        if private:
            info=os.fstat(fd);need(info.st_uid==os.getuid() and stat.S_IMODE(info.st_mode)==0o700)
        if private:need(path.name.casefold()!='.git')
        return fd,path.name

    def read(self,path,limit,private=True):
        need(type(limit) is int and 0<limit<=MAX_BYTES)
        parent,name=self.parent(path,private)
        fd=self.opened(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=parent)
        before=os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and before.st_nlink==1 and 0<before.st_size<=limit)
        if private:need(before.st_uid==os.getuid() and stat.S_IMODE(before.st_mode)==0o600)
        raw=bytearray()
        while len(raw)<=limit:
            block=os.read(fd,min(65536,limit+1-len(raw)))
            if not block:break
            raw.extend(block)
        need(len(raw)==before.st_size and snapshot(before)==snapshot(os.fstat(fd)))
        self.files.append((parent,name,fd,snapshot(before)));return bytes(raw)

    def check(self):
        for fd in self.private_directories:
            try:os.stat('.git',dir_fd=fd,follow_symlinks=False)
            except FileNotFoundError:pass
            else:raise Refused()
        for parent,name,fd,expected in self.directories:
            need(identity(os.fstat(fd))==expected==identity(os.stat(name,dir_fd=parent,follow_symlinks=False)))
        for parent,name,fd,expected in self.files:
            need(snapshot(os.fstat(fd))==expected==snapshot(os.stat(name,dir_fd=parent,follow_symlinks=False)))

    @staticmethod
    def members(fd,expected):
        found=set()
        with os.scandir(fd) as entries:
            for entry in entries:
                need(len(found)<len(expected) and entry.name in expected)
                found.add(entry.name)
        need(found==set(expected))

    def packet_members(self,path,expected):
        parent,name=self.parent(path,True)
        fd=self.opened(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=parent)
        info=os.fstat(fd)
        need(info.st_uid==os.getuid() and stat.S_IMODE(info.st_mode)==0o700)
        self.directories.append((parent,name,fd,identity(info)));self.private_directories.append(fd)
        self.members(fd,expected)

    def create(self,path,files):
        need(type(files) is dict and 1<=len(files)<=8 and sum(map(len,files.values()))<=MAX_BYTES)
        need(all(type(n) is str and n not in ('','.','..') and Path(n).name==n and type(raw) is bytes
                 and 0<len(raw)<=MAX_BYTES for n,raw in files.items()))
        parent,name=self.parent(path,True);self.check()
        # Existing names (including links) are never opened or replaced.
        try:os.mkdir(name,0o700,dir_fd=parent)
        except FileExistsError:raise
        except BaseException:
            self.output_may_exist=True;raise OutputUncertain() from None
        self.output_may_exist=True
        original=os.stat(name,dir_fd=parent,follow_symlinks=False)
        owned={};directory=None
        try:
            directory=self.opened(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=parent)
            self.private_directories.append(directory)
            need(identity(os.fstat(directory))==identity(original) and stat.S_IMODE(original.st_mode)==0o700)
            self.directories.append((parent,name,directory,identity(original)))
            for member,raw in files.items():
                fd=self.opened(member,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=directory)
                owned[member]=identity(os.fstat(fd))
                with os.fdopen(fd,'wb',closefd=False) as stream:
                    stream.write(raw);stream.flush();os.fsync(fd)
                info=os.fstat(fd)
                need(info.st_uid==os.getuid() and stat.S_IMODE(info.st_mode)==0o600 and info.st_nlink==1)
                self.files.append((directory,member,fd,snapshot(info)))
            self.members(directory,files);self.check()
            os.fsync(directory);os.fsync(parent)
        except BaseException:
            if directory is not None:
                for member,expected in owned.items():
                    try:
                        if identity(os.stat(member,dir_fd=directory,follow_symlinks=False))==expected:
                            os.unlink(member,dir_fd=directory)
                    except OSError:pass
            try:
                if identity(os.stat(name,dir_fd=parent,follow_symlinks=False))==identity(original):
                    os.rmdir(name,dir_fd=parent)
            except OSError:pass
            # Conservative even if cleanup appeared successful: do not assert
            # rollback across arbitrary close/unlink/fsync failure semantics.
            raise OutputUncertain() from None

    def close(self):
        owned,self.fds=self.fds,[];failed=False
        self.files=[];self.directories=[];self.private_directories=[]
        for fd in reversed(owned):
            try:os.close(fd)
            except BaseException:failed=True
        if failed:
            if self.output_may_exist:raise OutputUncertain()
            raise Refused()

    def __enter__(self):return self
    def __exit__(self,kind,value,trace):
        error=None
        if kind is None:
            try:self.check()
            except BaseException as failure:error=failure
        try:self.close()
        except BaseException as failure:
            if error is None:error=failure
        if (kind is not None or error is not None) and self.output_may_exist:
            raise OutputUncertain() from None
        if error is not None and kind is None:raise error
        return False
