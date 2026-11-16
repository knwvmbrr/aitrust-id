"""Bound selected reference comparison; injected scores are not real inference."""
import copy
from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import platform
import subprocess
import sys

import pytest
from protocol import corpus
from protocol.normalization import normalize_nfc
from research.nli import references, selected_references as selected
from research.nli.backend import expected_identity
from research.nli.pairs import analyze, PairError
from tools import reference_revision

ROOT = Path(__file__).resolve().parents[1]

def load(name, relative):
    spec=importlib.util.spec_from_file_location(name, ROOT/relative)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

cli=load('selected_reference_cli', 'scripts/check-nli-references.py')
preparer=load('reference_selection_preparer', 'scripts/prepare-reference-selection.py')
CONTROL={'Darwin':'macos_sandbox_deny_network','Linux':'linux_worker_seccomp_network_denial'}[platform.system()]


@pytest.fixture
def packet(tmp_path):
    tmp_path.chmod(0o700)
    reference=tmp_path/'reference.txt';reference.write_bytes(b'  The room is empty.  \r\nThe door is closed.\n')
    path=tmp_path/'corpus.json';corpus.create([('manual', reference)], path)
    query=tmp_path/'claim.txt';query.write_text('There are people in the room.');query.chmod(0o600)
    record=corpus.load(path);text=query.read_text()
    selection=selected.bind(record,text,1,'manual',1)
    folder=tmp_path/'selected';folder.mkdir(mode=0o700)
    selection_path=folder/'selection.json';selection_path.write_bytes(corpus.encoded(selection));selection_path.chmod(0o600)
    cache=tmp_path/'cache';cache.mkdir(mode=0o700)
    return {'base':tmp_path,'record':record,'corpus':path,'query':query,'text':text,
            'selection':selection,'selection_path':selection_path,'cache':cache}


def fake_runner(seen=None, tamper=None):
    def run(command, **kwargs):
        input_path=Path(command[2]);base=input_path.parent.parent
        if seen is not None:seen.append(base)
        assert command[1]==str(ROOT/'scripts/check-nli-pairs.py')
        assert kwargs['timeout']==55 and kwargs['close_fds'] and kwargs['env']['HF_HUB_OFFLINE']=='1'
        assert kwargs['env']['HOME']==str(base)
        request=json.loads(input_path.read_bytes())
        result=analyze(request,lambda a,b:([4.,-2.,-1.],15),expected_identity())
        result['network_control']=CONTROL
        if tamper:tamper(result)
        cli.create(base/'result',ROOT,{'observations.json':corpus.encoded(result)})
        return subprocess.CompletedProcess(command,0,b'{}',b'')
    return run


def argv(packet):
    return ['--corpus',str(packet['corpus']),'--subject',str(packet['query']),
            '--selection',str(packet['selection_path'])]


def test_explicit_pair_reaches_existing_worker_without_lowering_retrieval(packet):
    assert references.prepare(packet['record'],packet['text']) is None
    request=selected.prepare(packet['record'],packet['text'],packet['selection'])
    pair=request['pairs'][0]
    assert request['text'][slice(*pair['first'])]=='The room is empty.'
    assert request['text'][slice(*pair['second'])]=='There are people in the room.'
    seen=[]
    result=cli.check(packet['record'],packet['text'],packet['cache'],runner=fake_runner(seen),selection=packet['selection'])
    assert result['profile']==selected.RESULT_PROFILE and result['state']=='observed_model_outputs'
    assert result['retrieval_evaluation_obtained'] is False and result['retrieval'] is None
    assert 'retrieval_score' not in result['observations'][0]
    assert result['selection']==packet['selection']
    row=result['observations'][0]
    assert row['reference']['source_span']==[2,20] and row['claim_span']==[0,29]
    assert row['direction']=='reference_is_premise_claim_is_hypothesis'
    assert row['top_model_labels']==['contradiction']
    assert result['model_identity']==expected_identity() and result['network_control']==CONTROL
    assert not result['truth_established'] and not result['independent_corroboration'] and not result['tag_asserted']
    assert all(not base.exists() for base in seen)
    console=cli.summary(result,False)
    assert console['retrieval_evaluation_obtained'] is False
    assert all(field not in console for field in ['selection','subject_sha256','manifest_sha256','observations'])


def test_physical_blank_lines_trimmed_spans_and_normalized_subject_binding(packet):
    text='Cafe\u0301 context.\r\n\n  There are people in the room. \r\n'
    selection=selected.bind(packet['record'],text,3,'manual',1)
    assert normalize_nfc(text)[slice(*selection['claim']['span'])]=='There are people in the room.'
    assert selection['claim']['line']==3
    assert selection['original_subject_sha256']!=selection['subject_sha256']
    with pytest.raises(PairError):selected.checked(packet['record'],normalize_nfc(text),selection)
    with pytest.raises(PairError):selected.bind(packet['record'],text,2,'manual',1)


@pytest.mark.parametrize('part,field',[
    (None,'profile'),(None,'language'),(None,'normalization_id'),(None,'original_subject_sha256'),
    (None,'subject_sha256'),(None,'manifest_sha256'),(None,'selection_sha256'),
    ('claim','line'),('claim','span'),('reference','document_id'),('reference','document_sha256'),
    ('reference','normalized_source_sha256'),('reference','line'),('reference','source_span')])
def test_changed_bindings_refuse_before_any_model(packet,part,field):
    selection=copy.deepcopy(packet['selection']);target=selection if part is None else selection[part]
    target[field]='altered'
    def forbid(*args,**kwargs):pytest.fail('Changed selection reached worker')
    with pytest.raises((ValueError,KeyError,TypeError)):
        cli.check(packet['record'],packet['text'],packet['cache'],runner=forbid,selection=selection)


def test_rehashing_forged_span_does_not_make_it_current(packet):
    selection=copy.deepcopy(packet['selection']);selection['reference']['source_span']=[0,18]
    selection['selection_sha256']=corpus.sha(corpus.encoded({k:v for k,v in selection.items() if k!='selection_sha256'}))
    with pytest.raises(PairError):selected.checked(packet['record'],packet['text'],selection)


@pytest.mark.parametrize('number',[True,False,0,-1,1.0,None,10**100])
def test_line_numbers_require_actual_in_range_integers(packet,number):
    with pytest.raises(PairError):selected.bind(packet['record'],packet['text'],number,'manual',1)
    with pytest.raises(PairError):selected.bind(packet['record'],packet['text'],1,'manual',number)


@pytest.mark.parametrize('subject',['',' ','\x00','\ud800','x'*2001,'word '*513,'a '*513,'é','Only\rstandalone'])
def test_invalid_or_unsupported_selected_line_refused(packet,subject):
    with pytest.raises(ValueError):selected.bind(packet['record'],subject,1,'manual',1)


def test_changed_corpus_unselected_content_and_claim_refuse(packet):
    record=copy.deepcopy(packet['record']);record['documents'][0]['text']+='A new line.\n'
    record['documents'][0]['sha256']=corpus.sha(record['documents'][0]['text'].encode())
    record['manifest_sha256']=corpus.sha(corpus.encoded({'format':record['format'],'documents':record['documents']}))
    with pytest.raises(PairError):selected.checked(record,packet['text'],packet['selection'])
    with pytest.raises(PairError):selected.checked(packet['record'],packet['text']+' ',packet['selection'])


@pytest.mark.parametrize('value',[lambda s:s.update(extra=True),lambda s:s['claim'].update(extra=True),
    lambda s:s['reference'].update(extra=True),lambda s:s['claim'].update(line=True),
    lambda s:s['claim'].update(span=[0,29.0])])
def test_unknown_fields_and_json_type_changes_refused(packet,value):
    selection=copy.deepcopy(packet['selection']);value(selection)
    with pytest.raises(PairError):selected.checked(packet['record'],packet['text'],selection)


@pytest.mark.parametrize('raw',[b'[]',b'null',b'{"a":1,"a":2}',b'{"a":NaN}',b'\xff',b' '*(selected.MAX_SELECTION_BYTES+1)])
def test_selection_decoder_is_bounded_and_duplicate_refusing(raw):
    with pytest.raises(ValueError):selected.capture(raw)


def test_actual_preparer_creates_private_bound_record_without_echo(packet):
    output=packet['base']/'prepared'
    command=[sys.executable,str(ROOT/'scripts/prepare-reference-selection.py'),
        '--corpus',str(packet['corpus']),'--subject',str(packet['query']),
        '--claim-line','1','--reference-document','manual','--reference-line','1','--output',str(output)]
    result=subprocess.run(command,capture_output=True,timeout=5)
    assert result.returncode==0 and json.loads(result.stdout)['pairs_selected']==1
    path=output/'selection.json';before=path.read_bytes()
    assert json.loads(before)==packet['selection']
    assert not output.stat().st_mode&0o077 and not path.stat().st_mode&0o077
    assert packet['text'].encode() not in result.stdout+result.stderr and str(packet['base']).encode() not in result.stdout+result.stderr
    result=subprocess.run(command,capture_output=True,timeout=5)
    assert result.returncode==2 and path.read_bytes()==before


@pytest.mark.parametrize('flag',['--threshold','--maximum'])
def test_explicit_selection_does_not_ignore_retrieval_flags(packet,flag,capsys,monkeypatch):
    monkeypatch.setattr(cli,'check',lambda *a,**k:pytest.fail('Conflicting options invoked model'))
    assert cli.main(argv(packet)+[flag,'.75' if flag=='--threshold' else '5'])==2
    assert json.loads(capsys.readouterr().err)['state']=='UNAVAILABLE'


@pytest.mark.parametrize('kind',['public','symlink','hardlink','oversize','duplicate'])
def test_selection_private_input_refusal_no_echo(packet,kind,capsys,monkeypatch):
    args=argv(packet);path=packet['selection_path']
    if kind=='public':path.chmod(0o644)
    if kind=='symlink':link=path.with_name('link');link.symlink_to(path);args[-1]=str(link)
    if kind=='hardlink':path.with_name('hard').hardlink_to(path)
    if kind=='oversize':path.write_bytes(b'canary-private'*(selected.MAX_SELECTION_BYTES//10))
    if kind=='duplicate':path.write_bytes(b'{"profile":"canary-private","profile":"duplicate"}')
    monkeypatch.setattr(cli,'check',lambda *a,**k:pytest.fail('Refused selection invoked model'))
    assert cli.main(args)==2
    output=capsys.readouterr();assert not output.out and 'canary-private' not in output.err and str(packet['base']) not in output.err


def test_missing_cache_is_unavailable_not_no_match(packet,capsys):
    assert cli.main(argv(packet))==2
    error=json.loads(capsys.readouterr().err)
    assert error['state']=='UNAVAILABLE' and error['reason']=='model_cache_required'


@pytest.mark.parametrize('field',['subject_sha256','model_identity','network_control','tag_asserted'])
def test_selected_route_retains_worker_output_validator_and_cleanup(packet,field):
    seen=[]
    def tamper(result):result[field]='altered'
    with pytest.raises(ValueError):cli.check(packet['record'],packet['text'],packet['cache'],runner=fake_runner(seen,tamper),selection=packet['selection'])
    assert seen and all(not base.exists() for base in seen)


def test_selected_route_timeout_cleans_private_input(packet):
    seen=[]
    def timeout(command,**kwargs):
        seen.append(Path(command[2]).parent.parent);raise subprocess.TimeoutExpired(command,55)
    with pytest.raises(cli.ReferenceFailure) as error:
        cli.check(packet['record'],packet['text'],packet['cache'],runner=timeout,selection=packet['selection'])
    assert error.value.category=='model_deadline' and all(not base.exists() for base in seen)


def test_selected_cli_details_and_no_overwrite(packet,monkeypatch,capsys):
    target=packet['base']/'details';actual=cli.check
    monkeypatch.setattr(cli,'check',lambda *a,**k:actual(*a,**k,runner=fake_runner()))
    args=argv(packet)+['--model-cache',str(packet['cache']),'--details',str(target)]
    assert cli.main(args)==0
    console=json.loads(capsys.readouterr().out)
    assert console['retrieval_evaluation_obtained'] is False and console['passages_evaluated']==1
    path=target/'reference-observations.json';before=path.read_bytes()
    assert not path.stat().st_mode&0o077 and not target.stat().st_mode&0o077
    assert packet['text'] not in before.decode()
    assert cli.main(args)==2 and path.read_bytes()==before


def test_tied_scores_remain_explicit_and_not_calibrated(packet):
    result=selected.observe(packet['record'],packet['text'],packet['selection'],lambda a,b:([1.,1.,1.],10),{})
    assert result['observations'][0]['top_model_labels']==['contradiction','entailment','neutral']
    assert result['observations'][0]['calibrated_probability'] is False


@pytest.mark.parametrize('when',['expired_before','expired_after','backwards'])
def test_selected_route_keeps_review_window_pre_and_post_checks(packet,when,monkeypatch,capsys):
    now=datetime(2026,11,16,12,tzinfo=timezone.utc)
    start=now-timedelta(days=1);end=now+timedelta(days=1)
    policy={'profile':reference_revision.POLICY,'manifest_sha256':packet['record']['manifest_sha256'],
        'documents':[{'document_id':'manual','document_sha256':packet['record']['documents'][0]['sha256'],
                      'opens_at':start.strftime('%Y-%m-%dT%H:%M:%SZ'),'expires_at':end.strftime('%Y-%m-%dT%H:%M:%SZ')}]}
    path=packet['base']/'windows.json';path.write_bytes(corpus.encoded(policy));path.chmod(0o600)
    times=iter([end] if when=='expired_before' else [now,end if when=='expired_after' else now-timedelta(seconds=1)])
    monkeypatch.setattr(cli.review_window,'utc_now',lambda:next(times))
    actual=cli.check;calls=[]
    def compare(*a,**k):calls.append(True);return actual(*a,**k,runner=fake_runner())
    monkeypatch.setattr(cli,'check',compare)
    target=packet['base']/'details'
    assert cli.main(argv(packet)+['--model-cache',str(packet['cache']),'--review-windows',str(path),'--details',str(target)])==2
    error=json.loads(capsys.readouterr().err)
    assert error['reason']==('review_clock_changed' if when=='backwards' else 'review_window_expired')
    assert calls==([] if when=='expired_before' else [True]) and not target.exists()


def test_automatic_route_never_imports_optional_selection_component(packet,monkeypatch,capsys):
    import builtins
    original=builtins.__import__
    def importing(name,globals=None,locals=None,fromlist=(),level=0):
        if name=='research.nli' and 'selected_references' in fromlist:
            pytest.fail('Automatic route imported the optional selection component')
        return original(name,globals,locals,fromlist,level)
    monkeypatch.setattr(builtins,'__import__',importing)
    assert cli.main(['--corpus',str(packet['corpus']),'--subject',str(packet['query'])])==0
    result=json.loads(capsys.readouterr().out)
    assert result['profile']=='retrieved-passage-nli-observation/1.0.0'
    assert result['state']=='no_similar_passage' and not result['model_evaluation_obtained']


@pytest.mark.parametrize('error',[ImportError,SyntaxError])
def test_optional_component_import_failure_is_fixed_selected_route_unavailable(packet,monkeypatch,capsys,error):
    import builtins
    original=builtins.__import__
    def importing(name,globals=None,locals=None,fromlist=(),level=0):
        if name=='research.nli' and 'selected_references' in fromlist:
            raise error('PRIVATE_IMPORT_CANARY /private/path')
        return original(name,globals,locals,fromlist,level)
    monkeypatch.setattr(builtins,'__import__',importing)
    assert cli.main(argv(packet))==2
    output=capsys.readouterr()
    assert not output.out and 'PRIVATE_IMPORT_CANARY' not in output.err and '/private/path' not in output.err
    result=json.loads(output.err)
    assert result['state']=='UNAVAILABLE' and result['reason']=='selection_component_unavailable'
