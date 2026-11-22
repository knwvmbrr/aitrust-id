#!/usr/bin/env python3
"""Create one private fixed citation practice packet; no real example is read."""
import argparse
import json
import os
from pathlib import Path
import stat
import sys

ROOT=Path(__file__).absolute().parents[1]
sys.path.insert(0,str(ROOT))


class Refusal(ValueError):
    pass


class Parser(argparse.ArgumentParser):
    def error(self,message):
        raise Refusal('Citation practice command refused.')


def practice_files(tool,sources):
    """Use the actual current canonical corpus and sidecar implementations."""
    subject=b'A menu note [1]. Another note [2]. A list [1,2].'
    reference='Water and tea are listed.'
    content={'format':tool.corpus.VERSION,'documents':[{'id':'menu','text':reference,
             'sha256':tool.sha(reference.encode('utf-8'))}]}
    record={**content,'manifest_sha256':tool.sha(tool.corpus.encoded(content))}
    corpus_raw=tool.corpus.encoded(record)+b'\n'
    sidecar=tool._prepare(corpus_raw,subject,[(1,'menu')],sources)
    sidecar_raw=tool.encoded(sidecar)+b'\n'
    summary,_=tool._check(corpus_raw,subject,sidecar_raw,sources)
    tool.need(summary['counts']=={'resolved-in-attached-corpus':1,
        'unresolved-in-attached-corpus':1,'unsupported':1})
    return {'subject.txt':subject,'corpus.json':corpus_raw,'citations.json':sidecar_raw}


def cleanup(tool,parent,name,fd,directory_identity,owned):
    """Attempt only this invocation's identity-confirmed entries, once each."""
    clean=True
    if fd is not None:
        for leaf,expected in reversed(owned):
            try:
                info=os.stat(leaf,dir_fd=fd,follow_symlinks=False)
                if expected is None or tool.identity(info)!=expected:
                    clean=False
                    continue
                os.unlink(leaf,dir_fd=fd)
            except FileNotFoundError:
                pass
            except BaseException:
                clean=False
    try:
        current=os.stat(name,dir_fd=parent,follow_symlinks=False)
        if directory_identity is None or tool.identity(current)!=directory_identity:
            return False
        os.rmdir(name,dir_fd=parent)
        os.fsync(parent)
    except BaseException:
        return False
    return clean


def create_packet(tool,output):
    path=Path(output).absolute()
    tool.need(not path.is_relative_to(ROOT))
    with tool.Capture() as capture:
        # Retain exact engine, CLI, corpus, normalizer and own producer bytes.
        sources=tool.current_sources(capture)
        capture.read(Path(__file__).absolute(),1000000,private=False)
        files=practice_files(tool,sources)
        parent,name=capture.parent(path)
        parent_info=os.fstat(parent)
        tool.need(stat.S_ISDIR(parent_info.st_mode) and parent_info.st_uid==os.getuid()
                  and stat.S_IMODE(parent_info.st_mode)==0o700)
        capture.check()
        try:
            os.mkdir(name,mode=0o700,dir_fd=parent)
        except FileExistsError:
            # A known existing name was not created or modified by this call.
            raise
        except BaseException:
            # An unexpected filesystem result does not establish non-creation.
            capture.output_may_exist=True
            raise
        capture.output_may_exist=True
        fd=None;directory_identity=None;owned=[]
        try:
            directory_identity=tool.identity(os.stat(name,dir_fd=parent,follow_symlinks=False))
            fd=os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=parent)
            capture.fds.append(fd)
            info=os.fstat(fd)
            tool.need(stat.S_ISDIR(info.st_mode) and info.st_uid==os.getuid()
                      and stat.S_IMODE(info.st_mode)==0o700 and tool.identity(info)==directory_identity)
            capture.directories.append((parent,name,fd,directory_identity))
            for leaf,raw in files.items():
                raw_fd=os.open(leaf,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,
                               0o600,dir_fd=fd)
                capture.fds.append(raw_fd)
                owned.append((leaf,None))
                owned[-1]=(leaf,tool.identity(os.fstat(raw_fd)))
                with os.fdopen(raw_fd,'wb',closefd=False) as stream:
                    stream.write(raw);stream.flush();os.fsync(stream.fileno())
                info=os.fstat(raw_fd)
                tool.need(stat.S_ISREG(info.st_mode) and info.st_uid==os.getuid()
                          and stat.S_IMODE(info.st_mode)==0o600 and info.st_nlink==1
                          and info.st_size==len(raw))
                capture.files.append((fd,leaf,raw_fd,tool.snapshot(info)))
            tool.need(set(os.listdir(fd))==set(files))
            capture.check()
            os.fsync(fd);os.fsync(parent)
        except BaseException:
            if cleanup(tool,parent,name,fd,directory_identity,owned):
                capture.output_may_exist=False
            raise
    return {'state':'PRACTICE_SAVED','profile':'local-citation-practice/v1',
            'synthetic_only':True,'user_example_read':False,'network_used':False,
            'tags':[],'next_step':'Run the existing citation-resolution.py check with the three files in your selected packet.'}


def main(argv=None):
    uncertainty=()
    try:
        from tools import citation_resolution as tool
        uncertainty=(tool.OutputCommitUncertain,)
        parser=Parser(description=__doc__,allow_abbrev=False)
        parser.add_argument('--output',required=True,help='New packet directory in an existing private0700 parent outside the checkout.')
        args=parser.parse_args(argv)
        result=create_packet(tool,args.output)
        print(json.dumps(result,sort_keys=True));return 0
    except uncertainty:
        print('{"state":"UNAVAILABLE","reason":"output_commit_uncertain","output_may_exist":true,"tags":[]}');return 2
    except (ValueError,OSError,UnicodeError,TypeError,RecursionError,RuntimeError,ImportError,SyntaxError,KeyboardInterrupt):
        print('{"state":"UNAVAILABLE","reason":"citation_practice_unavailable","tags":[]}');return 2


if __name__=='__main__':
    raise SystemExit(main())
