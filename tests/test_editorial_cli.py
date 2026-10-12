"""Executed private CLI lifecycle and failure controls, using invented data only."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import pytest
from test_assertion_replay import assertion
from test_newsroom import device_record, TEXT
from tools import newsroom

ROOT = Path(__file__).resolve().parents[1]


def call(name, *args):
    return subprocess.run([sys.executable, str(ROOT/'scripts'/name), *map(str,args)],
                          capture_output=True, text=True, timeout=15)


def inputs(tmp_path, row):
    tmp_path.chmod(0o700)
    a=tmp_path/'selected-source.json';a.write_bytes(newsroom.encode(row));a.chmod(0o600)
    t=tmp_path/'selected-subject.txt';t.write_bytes(TEXT);t.chmod(0o600)
    return a,t


def prepare(tmp_path, a, t, **kw):
    args=['--source',a,'--subject',t,'--reviewer','editor-one','--decision',kw.pop('decision','needs_review'),
          '--reason',kw.pop('reason','needs_context'),'--output',kw.pop('output',tmp_path/'packet'),'--reviewed-record']
    if 'previous' in kw:args.extend(['--previous',kw['previous']])
    return call('prepare-editorial-review.py',*args)


@pytest.mark.parametrize('kind',['gateway','device'])
def test_two_actual_supported_producers_install_use_correct_and_remove(tmp_path,assertion,device_record,kind):
    source=assertion if kind=='gateway' else device_record
    a,t=inputs(tmp_path,source);original=(a.read_bytes(),t.read_bytes())
    assert prepare(tmp_path,a,t).returncode==0
    packet=tmp_path/'packet';output=tmp_path/'first'
    r=call('editorial-review.py','--packet',packet,'--output',output,'--reviewed-record')
    assert r.returncode==0 and TEXT.decode() not in r.stdout+r.stderr
    record=json.loads((output/'editorial-review.json').read_bytes())
    assert record['decision']=='needs_review' and record['source_tags']==source.get('tags',source.get('candidates'))
    assert TEXT not in (output/'editorial-review.html').read_bytes()
    assert output.stat().st_mode&0o777==0o700
    assert all(p.stat().st_mode&0o777==0o600 for p in output.iterdir())
    first=(output/'editorial-review.json').read_bytes()
    assert prepare(tmp_path,a,t,previous=output/'editorial-review.json',output=tmp_path/'correction',decision='withheld',reason='disagreed').returncode==0
    corrected=tmp_path/'second'
    r=call('editorial-review.py','--packet',tmp_path/'correction','--output',corrected,'--reviewed-record','--supersede','--include-subject')
    assert r.returncode==0
    row=json.loads((corrected/'editorial-review.json').read_bytes())
    assert row['previous_record_sha256']==newsroom.sha(first) and row['decision']=='withheld'
    assert TEXT in (corrected/'editorial-review.html').read_bytes()
    assert (output/'editorial-review.json').read_bytes()==first
    assert (a.read_bytes(),t.read_bytes())==original
    for folder in [packet,output,tmp_path/'correction',corrected]:
        for file in folder.iterdir():file.unlink()
        folder.rmdir()
        assert not folder.exists()
    assert (a.read_bytes(),t.read_bytes())==original


def test_explicit_review_is_required_before_reading_private_paths(tmp_path):
    for name,args in [('editorial-review.py',['--packet',tmp_path/'missing','--output',tmp_path/'new']),
                      ('prepare-editorial-review.py',['--source',tmp_path/'missing','--subject',tmp_path/'missing','--reviewer','editor-one','--decision','reviewed','--reason','source_checked','--output',tmp_path/'new'])]:
        r=call(name,*args);assert r.returncode==2 and str(tmp_path) not in r.stdout+r.stderr
    assert not (tmp_path/'new').exists()


@pytest.mark.parametrize('kind',['source_link','source_hardlink','source_fifo','public_source','public_parent','wrong_subject','source_change','extra_packet','missing_packet','output_exists','output_link','packet_link','public_packet','supersede_missing','supersede_not_selected'])
def test_private_cli_refusals_do_not_publish_or_change_selected_input(tmp_path,assertion,kind):
    a,t=inputs(tmp_path,assertion)
    if kind=='source_link':
        p=tmp_path/'linked';p.symlink_to(a);a=p
    elif kind=='source_hardlink':os.link(a,tmp_path/'hardlink')
    elif kind=='source_fifo':
        a.unlink();os.mkfifo(a,0o600)
    elif kind=='public_source':a.chmod(0o644)
    elif kind=='public_parent':tmp_path.chmod(0o755)
    elif kind=='wrong_subject':t.write_bytes(b'PRIVATE_EDITORIAL_CANARY')
    r=prepare(tmp_path,a,t)
    source_failure=kind in {'source_link','source_hardlink','source_fifo','public_source','public_parent','wrong_subject'}
    if source_failure:
        assert r.returncode==2 and not (tmp_path/'packet').exists()
    else:
        assert r.returncode==0
        packet=tmp_path/'packet';output=tmp_path/'result';extra=[]
        if kind=='source_change':(packet/'source.json').write_bytes(b'PRIVATE_EDITORIAL_CANARY')
        elif kind=='extra_packet':(packet/'extra').write_bytes(b'PRIVATE_EDITORIAL_CANARY')
        elif kind=='missing_packet':(packet/'review.json').unlink()
        elif kind=='output_exists':output.mkdir(mode=0o700);(output/'owner-file').write_bytes(b'PRIVATE_EDITORIAL_CANARY')
        elif kind=='output_link':output.symlink_to(packet,target_is_directory=True)
        elif kind=='packet_link':p=tmp_path/'packet-link';p.symlink_to(packet,target_is_directory=True);packet=p
        elif kind=='public_packet':packet.chmod(0o755)
        elif kind=='supersede_missing':extra=['--supersede']
        elif kind=='supersede_not_selected':(packet/'previous.json').write_bytes(b'PRIVATE_EDITORIAL_CANARY');(packet/'previous.json').chmod(0o600)
        before={p.name:p.read_bytes() for p in packet.iterdir() if p.is_file()}
        r=call('editorial-review.py','--packet',packet,'--output',output,'--reviewed-record',*extra)
        assert r.returncode==2
        assert before=={p.name:p.read_bytes() for p in packet.iterdir() if p.is_file()}
        if kind=='output_exists':assert (output/'owner-file').read_bytes()==b'PRIVATE_EDITORIAL_CANARY'
        elif kind!='output_link':assert not output.exists()
    assert 'PRIVATE_EDITORIAL_CANARY' not in r.stdout+r.stderr and str(tmp_path) not in r.stdout+r.stderr


def test_bad_command_arguments_have_fixed_private_diagnostics(tmp_path):
    r=call('editorial-review.py','--packet',tmp_path,'--private-secret=PRIVATE_EDITORIAL_CANARY')
    assert r.returncode==2 and 'PRIVATE_EDITORIAL_CANARY' not in r.stderr and str(tmp_path) not in r.stderr


@pytest.mark.parametrize('malformed',[None,[],False,'PRIVATE_EDITORIAL_CANARY'])
def test_malformed_evaluator_metadata_has_no_traceback_or_private_diagnostic(tmp_path,malformed):
    a,t=inputs(tmp_path,{'evaluator':malformed})
    r=prepare(tmp_path,a,t)
    assert r.returncode==2 and not (tmp_path/'packet').exists()
    assert 'Traceback' not in r.stderr and 'PRIVATE_EDITORIAL_CANARY' not in r.stdout+r.stderr
    assert str(tmp_path) not in r.stdout+r.stderr
