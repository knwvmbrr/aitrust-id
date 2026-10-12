import copy
import importlib.util
import json
from pathlib import Path
import platform
import os
import subprocess
import sys

import pytest
from protocol import corpus
from research.nli import references
from research.nli.backend import expected_identity
from research.nli.pairs import analyze,PairError

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('reference_cli',ROOT/'scripts/check-nli-references.py')
cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)
CONTROL={'Darwin':'macos_sandbox_deny_network','Linux':'linux_worker_seccomp_network_denial'}[platform.system()]

@pytest.fixture
def packet(tmp_path):
    tmp_path.chmod(0o700)
    text=tmp_path/'manual.txt';text.write_text('The room is empty.\nThe door was closed yesterday.\n')
    path=tmp_path/'corpus.json';corpus.create([('manual',text)],path)
    query=tmp_path/'query.txt';query.write_text('There are people in the room.');query.chmod(0o600)
    cache=tmp_path/'cache';cache.mkdir(mode=0o700)
    return tmp_path,corpus.load(path),path,query,cache

def observation(request):
    result=analyze(request,lambda a,b:([4.,-2.,-1.],15),expected_identity())
    result['network_control']=CONTROL
    return result

def fake_runner(tamper=None,seen=None):
    def run(command,**kwargs):
        input_path=Path(command[2]);base=input_path.parent.parent
        if seen is not None:seen.append(base)
        assert kwargs['timeout']==55 and kwargs['close_fds'] and kwargs['check'] is False
        assert kwargs['env']['HOME']==str(base) and kwargs['env']['HF_HUB_OFFLINE']=='1'
        assert set(kwargs['env'])=={'PATH','HOME','HF_HUB_OFFLINE','TOKENIZERS_PARALLELISM','OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','PYTHONDONTWRITEBYTECODE'}
        request=json.loads(input_path.read_text());result=observation(request)
        if tamper:tamper(result)
        cli.create(base/'result',ROOT,{'observations.json':json.dumps(result).encode()})
        return subprocess.CompletedProcess(command,0,b'{}',b'')
    return run

def test_separate_reference_observation_binds_original_offsets(packet):
    _,record,_,_,cache=packet;seen=[]
    result=cli.check(record,'There are people in the room.',cache,.4,runner=fake_runner(seen=seen))
    assert result['profile']=='retrieved-passage-nli-observation/1.0.0'
    row=result['observations'][0]
    assert row['claim_span']==[0,29] and row['reference']['source_span']==[0,18]
    assert result['model_identity']==expected_identity() and result['network_control']==CONTROL
    assert all(not folder.exists() for folder in seen)
    summary=cli.summary(result,False)
    assert 'subject_sha256' not in summary and 'manifest_sha256' not in summary and 'observations' not in summary
    assert 'There are' not in str(summary) and not summary['truth_established'] and not summary['tag_asserted']

def test_selection_miss_does_not_require_model_cache(packet):
    _,record,_,_,_=packet
    def forbid(*a,**k):pytest.fail('No-match invoked model')
    result=cli.check(record,'There are people in the room.',runner=forbid)
    assert result['model_identity'] is None and result['network_control']=='model_not_invoked'
    assert result['state']=='no_similar_passage' and not result['model_evaluation_obtained']
    assert not result['absence_proves_false']

def test_virtual_premise_and_hypothesis_are_exact(packet):
    _,record,_,_,_=packet
    request=references.prepare(record,'There are people in the room.',.4)
    pair=request['pairs'][0];text=request['text']
    assert text[slice(*pair['first'])]=='The room is empty.'
    assert text[slice(*pair['second'])]=='There are people in the room.'
    assert pair['id']=='candidate-000'

@pytest.mark.parametrize('maximum',[True,0,6,10,1.,None])
def test_reference_candidate_limit_before_model(packet,maximum):
    with pytest.raises(PairError):references.prepare(packet[1],'The room is empty.',maximum=maximum)

@pytest.mark.parametrize('field',['profile','subject_sha256','span_units','model_identity','network_control','tag_asserted','truth_established','extra'])
def test_corrupted_handoff_has_no_result_and_cleans_temp(packet,field):
    _,record,_,_,cache=packet;seen=[]
    def tamper(result):result[field]='synthetic-private-path-canary'
    with pytest.raises(ValueError):cli.check(record,'The room is empty.',cache,runner=fake_runner(tamper,seen))
    assert all(not path.exists() for path in seen)

@pytest.mark.parametrize('field',['first_span','second_span','pair_direction','logits','token_count','normalized_model_scores','top_model_labels'])
def test_corrupted_model_rows_refuse(packet,field):
    def tamper(result):result['pairs'][0][field]='changed'
    with pytest.raises((ValueError,KeyError,TypeError)):cli.check(packet[1],'The room is empty.',packet[4],runner=fake_runner(tamper))

def test_worker_failure_output_is_not_forwarded(packet,capsys,monkeypatch):
    def refuse(*a,**k):return subprocess.CompletedProcess(a[0],2,b'private-canary',b'/secret/private-canary')
    monkeypatch.setattr(cli,'check',lambda *a,**k:(_ for _ in ()).throw(cli.ReferenceFailure('model_unavailable','Check pinned assets and sandbox.')))
    assert cli.main(['--corpus',str(packet[2]),'--subject',str(packet[3])])==2
    out=capsys.readouterr();assert not out.out and 'private-canary' not in out.err and str(packet[0]) not in out.err

def test_model_subprocess_failure_and_timeout_cleanup(packet):
    seen=[]
    def refuse(command,**kw):
        seen.append(Path(command[2]).parent.parent)
        return subprocess.CompletedProcess(command,2,b'private-canary',b'private-path')
    with pytest.raises(cli.ReferenceFailure) as failure:cli.check(packet[1],'The room is empty.',packet[4],runner=refuse)
    assert failure.value.category=='model_unavailable' and 'private' not in str(failure.value)
    def timeout(command,**kw):
        seen.append(Path(command[2]).parent.parent);raise subprocess.TimeoutExpired(command,55,output=b'private-canary')
    with pytest.raises(cli.ReferenceFailure) as failure:cli.check(packet[1],'The room is empty.',packet[4],runner=timeout)
    assert failure.value.category=='model_deadline' and all(not path.exists() for path in seen)

def test_no_match_cli_private_details_and_no_overwrite(packet,capsys):
    folder,_,path,query,_=packet;target=folder/'details'
    args=['--corpus',str(path),'--subject',str(query),'--details',str(target)]
    assert cli.main(args)==0
    output=capsys.readouterr();summary=json.loads(output.out)
    assert summary['state']=='no_similar_passage' and not summary['model_evaluation_obtained']
    artifact=target/'reference-observations.json';before=artifact.read_bytes()
    assert not target.stat().st_mode&0o077 and not artifact.stat().st_mode&0o077
    assert cli.main(args)==2 and artifact.read_bytes()==before
    assert 'There are' not in output.out and str(folder) not in output.out

@pytest.mark.parametrize('kind',['query-public','corpus-public','query-symlink','corpus-symlink','query-hardlink','corrupt-corpus','invalid-utf8','too-long','non-ascii'])
def test_private_input_refusals_have_no_echo(packet,capsys,kind):
    folder,_,path,query,_=packet
    if kind=='query-public':query.chmod(0o644)
    if kind=='corpus-public':path.chmod(0o644)
    if kind=='query-symlink':link=folder/'link';link.symlink_to(query);query=link
    if kind=='corpus-symlink':link=folder/'link';link.symlink_to(path);path=link
    if kind=='query-hardlink':(folder/'link').hardlink_to(query)
    if kind=='corrupt-corpus':path.write_text('{"private-canary":"corrupt"}')
    if kind=='invalid-utf8':query.write_bytes(b'private-canary\xff')
    if kind=='too-long':query.write_text('private-canary '*160)
    if kind=='non-ascii':query.write_text('private-canary é')
    assert cli.main(['--corpus',str(path),'--subject',str(query)])==2
    out=capsys.readouterr();assert not out.out and 'private-canary' not in out.err and str(folder) not in out.err

def test_prepared_request_bound_is_not_silently_truncated(packet):
    record=copy.deepcopy(packet[1]);value='a'*1999
    record['documents']=[{'id':f'doc{i}','text':value,'sha256':corpus.sha(value.encode())} for i in range(5)]
    record['manifest_sha256']=corpus.sha(corpus.encoded({'format':record['format'],'documents':record['documents']}))
    request=references.prepare(record,value)
    assert len(request['text'])==20000
    assert len(request['pairs'])==5
    value+='a'
    for row in record['documents']:row['text']=value;row['sha256']=corpus.sha(value.encode())
    record['manifest_sha256']=corpus.sha(corpus.encoded({'format':record['format'],'documents':record['documents']}))
    with pytest.raises(PairError):references.prepare(record,value)

def assert_owned_descendant_stopped(child):
    # Read directly: init can reap a killed child between exists() and read().
    # Only a disappeared process or a zombie is accepted, never an unknown or
    # running state. Permission/read failures still fail the check.
    try:
        stat = Path(f'/proc/{child}/stat').read_text()
    except (FileNotFoundError, ProcessLookupError):
        with pytest.raises(ProcessLookupError):
            os.kill(child, 0)
    else:
        assert stat.rsplit(')', 1)[1].split()[0] == 'Z'


@pytest.mark.parametrize("disappeared", [FileNotFoundError, ProcessLookupError])
def test_reaped_descendant_between_observation_and_read_is_accepted(monkeypatch, disappeared):
    def gone(*args, **kwargs): raise disappeared()
    def absent(*args, **kwargs): raise ProcessLookupError()
    monkeypatch.setattr(Path, 'read_text', gone)
    monkeypatch.setattr(os, 'kill', absent)
    assert_owned_descendant_stopped(123)


def test_running_descendant_is_still_rejected(monkeypatch):
    monkeypatch.setattr(Path, 'read_text', lambda *a, **k: '123 (synthetic python) S 1')
    with pytest.raises(AssertionError): assert_owned_descendant_stopped(123)


def test_unknown_descendant_read_failure_is_not_a_pass(monkeypatch):
    def refused(*args, **kwargs): raise PermissionError()
    monkeypatch.setattr(Path, 'read_text', refused)
    with pytest.raises(PermissionError): assert_owned_descendant_stopped(123)


def test_outer_deadline_ends_nested_worker_session(tmp_path):
    pid_file=tmp_path/'pid'
    child_code='import time; time.sleep(60)'
    parent_code=('import subprocess,sys,time,pathlib; p=subprocess.Popen([sys.executable,"-c",'+repr(child_code)+']); '
        'pathlib.Path(sys.argv[1]).write_text(str(p.pid)); time.sleep(60)')
    with pytest.raises(subprocess.TimeoutExpired) as failure:
        cli.run_owned([sys.executable,'-c',parent_code,str(pid_file)],capture_output=True,
            check=False,close_fds=True,timeout=1)
    assert str(tmp_path) not in str(failure.value)
    child=int(pid_file.read_text())
    # A killed descendant may briefly be a zombie awaiting init reaping. It must
    # never remain a running process. This is a synthetic process, not a model.
    assert_owned_descendant_stopped(child)
