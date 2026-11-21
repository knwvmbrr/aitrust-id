"""Actual canonical private practice and bounded owned-I/O failure controls."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

import pytest
from tools import citation_resolution as tool

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('citation_practice',ROOT/'scripts/prepare-citation-demo.py')
demo=importlib.util.module_from_spec(spec);spec.loader.exec_module(demo)

@pytest.fixture
def private(tmp_path):
    root=tmp_path.resolve();root.chmod(0o700);return root


def invoke(script,args):
    return subprocess.run([sys.executable,'-I','-S','-B',str(ROOT/script),*map(str,args)],capture_output=True,timeout=15)


def test_actual_two_commands_match_current_canonical_counts_bindings_and_privacy(private):
    out=private/'demo';made=invoke('scripts/prepare-citation-demo.py',['--output',out])
    assert made.returncode==0;brief=json.loads(made.stdout)
    assert brief['synthetic_only']and not brief['user_example_read']and not brief['network_used']and brief['tags']==[]
    assert set(p.name for p in out.iterdir())=={'subject.txt','corpus.json','citations.json'}
    assert out.stat().st_mode&0o777==0o700 and all(p.stat().st_mode&0o777==0o600 for p in out.iterdir())
    args=['check','--subject',out/'subject.txt','--corpus',out/'corpus.json','--sidecar',out/'citations.json']
    checked=invoke('scripts/citation-resolution.py',args);assert checked.returncode==0
    observed=json.loads(checked.stdout);assert observed['state']=='COMPLETE'
    assert observed['counts']=={'resolved-in-attached-corpus':1,'unresolved-in-attached-corpus':1,'unsupported':1}
    assert not observed['truth_established']and not observed['source_support_established']and observed['tags']==[]
    summary,detail=tool.check((out/'corpus.json').read_bytes(),(out/'subject.txt').read_bytes(),(out/'citations.json').read_bytes())
    assert observed==summary and detail['bindings']['source_sha256'].keys()==set(tool.SOURCES)
    for result in(made,checked):
        assert str(private).encode()not in result.stdout+result.stderr
        assert(out/'subject.txt').read_bytes()not in result.stdout+result.stderr
        assert b'source_sha256'not in result.stdout and b'subject_sha256'not in result.stdout


@pytest.mark.parametrize('kind',['directory','empty-directory','file','dangling-link','link','fifo'])
def test_every_existing_destination_is_preserved(private,capsys,kind):
    out=private/'demo'
    if kind in ('directory','empty-directory'):out.mkdir(mode=0o700)
    if kind=='directory':(out/'owner-file').write_text('OWNER_CANARY')
    if kind=='file':out.write_text('OWNER_CANARY')
    if kind=='dangling-link':out.symlink_to(private/'missing')
    if kind=='link':out.symlink_to(private,target_is_directory=True)
    if kind=='fifo':os.mkfifo(out)
    before=out.lstat()
    assert demo.main(['--output',str(out)])==2
    after=out.lstat();assert(before.st_dev,before.st_ino,before.st_mode)==(after.st_dev,after.st_ino,after.st_mode)
    output=capsys.readouterr();assert json.loads(output.out)['reason']=='citation_practice_unavailable'
    assert str(private)not in output.out+output.err and 'OWNER_CANARY'not in output.out+output.err


@pytest.mark.parametrize('kind',['public-parent','linked-parent','inside-checkout','missing-parent'])
def test_unsafe_destination_refuses_without_creation(private,capsys,kind):
    out=private/'demo'
    if kind=='public-parent':private.chmod(0o755)
    if kind=='linked-parent':
        link=private/'link';link.symlink_to(private,target_is_directory=True);out=link/'demo'
    if kind=='inside-checkout':out=ROOT/'citation-private-must-not-exist'
    if kind=='missing-parent':out=private/'absent'/'demo'
    assert demo.main(['--output',str(out)])==2 and not out.exists()
    captured=capsys.readouterr();assert str(out)not in captured.out+captured.err


def test_second_invocation_never_overwrites_and_checker_survives_optional_failure(private,capsys):
    out=private/'demo';assert demo.main(['--output',str(out)])==0
    before={p.name:p.read_bytes()for p in out.iterdir()}
    assert demo.main(['--output',str(out)])==2
    assert before=={p.name:p.read_bytes()for p in out.iterdir()}
    with patch.object(demo,'practice_files',side_effect=ValueError('PRIVATE_EXCEPTION')):
        assert demo.main(['--output',str(private/'failure')])==2
    summary,_=tool.check(before['corpus.json'],before['subject.txt'],before['citations.json'])
    assert summary['state']=='COMPLETE'and not(private/'failure').exists()
    captured=capsys.readouterr();assert 'PRIVATE_EXCEPTION'not in captured.out+captured.err


@pytest.mark.parametrize('when',['before','after'])
def test_source_drift_refuses_and_cleans_only_new_packet(private,capsys,when):
    out=private/'demo';check=tool.Capture.check
    def drift(capture):
        if (when=='after')==out.exists():raise tool.CitationError('PRIVATE_DRIFT')
        return check(capture)
    with patch.object(tool.Capture,'check',drift):assert demo.main(['--output',str(out)])==2
    assert not out.exists();captured=capsys.readouterr();assert 'PRIVATE_DRIFT'not in captured.out+captured.err


def test_fdopen_construction_failure_closes_raw_and_removes_packet(private,capsys):
    raw=[]
    def fail(fd,*a,**kw):raw.append(fd);raise OSError('PRIVATE_FDOPEN')
    with patch.object(os,'fdopen',side_effect=fail):assert demo.main(['--output',str(private/'demo')])==2
    assert len(raw)==1 and not(private/'demo').exists()
    with pytest.raises(OSError):os.fstat(raw[0])
    assert 'PRIVATE_FDOPEN'not in capsys.readouterr().out


def test_failed_cleanup_is_uncertain_not_rolled_back(private,capsys):
    out=private/'demo';unlink=os.unlink
    def refuse(name,*a,**kw):
        if name=='subject.txt':raise PermissionError('PRIVATE_UNLINK')
        return unlink(name,*a,**kw)
    with patch.object(os,'fdopen',side_effect=OSError('PRIVATE_WRITE')),patch.object(os,'unlink',side_effect=refuse):
        assert demo.main(['--output',str(out)])==2
    result=json.loads(capsys.readouterr().out);assert result['reason']=='output_commit_uncertain'and result['output_may_exist']is True
    assert out.is_dir()and(out/'subject.txt').is_file()


def test_postsuccess_close_failure_retains_complete_private_packet_and_attempts_all_closes(private,capsys):
    out=private/'demo';close=os.close;calls=[];raised=False
    def fail_after_close(fd):
        nonlocal raised
        calls.append(fd);close(fd)
        if not raised:raised=True;raise OSError('PRIVATE_CLOSE')
    with patch.object(os,'close',side_effect=fail_after_close):assert demo.main(['--output',str(out)])==2
    result=json.loads(capsys.readouterr().out);assert result['reason']=='output_commit_uncertain'and result['output_may_exist']is True
    assert len(calls)==len(set(calls))and len(calls)>10
    assert set(p.name for p in out.iterdir())=={'subject.txt','corpus.json','citations.json'}


def test_malformed_argument_and_missing_engine_have_fixed_errors(private,capsys):
    assert demo.main(['--PRIVATE_CANARY',str(private)])==2
    import builtins
    original=builtins.__import__
    def missing(name,globals=None,locals=None,fromlist=(),level=0):
        if name=='tools' and 'citation_resolution'in fromlist:raise ImportError('PRIVATE_IMPORT')
        return original(name,globals,locals,fromlist,level)
    with patch.object(builtins,'__import__',side_effect=missing):
        assert demo.main(['--output',str(private/'absent')])==2
    assert not(private/'absent').exists()
    captured=capsys.readouterr();assert 'PRIVATE_CANARY'not in captured.out+captured.err and str(private)not in captured.out+captured.err
