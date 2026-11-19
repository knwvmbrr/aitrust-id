"""Literal local citation associations, private files, and actual CLI controls."""
import json
import os
from pathlib import Path
import stat
import subprocess
import sys

import pytest
from protocol import corpus
from protocol.normalization import normalize_nfc
from tools import citation_resolution as c

ROOT = Path(__file__).absolute().parents[1]
CLI = ROOT / 'scripts/citation-resolution.py'


def attached(documents=None):
    documents = documents or {'first': 'An invented source.', 'second': 'Cafe\u0301 source.'}
    value = {'format': corpus.VERSION, 'documents': [
        {'id': name, 'sha256': c.sha(text.encode()), 'text': text}
        for name, text in sorted(documents.items())]}
    return corpus.encoded({**value, 'manifest_sha256': c.sha(corpus.encoded(value))})


def setup_files(tmp_path, text='Cafe\u0301 details [1], other [2].'):
    private = tmp_path / 'private'
    private.mkdir(mode=0o700)
    subject = private / 'subject.txt'
    subject.write_text(text)
    source = private / 'corpus.json'
    source.write_bytes(attached())
    for path in (subject, source):
        path.chmod(0o600)
    return private, subject, source


def cli(*args):
    return subprocess.run([sys.executable, '-I', '-S', '-B', str(CLI), *map(str, args)],
                          capture_output=True, timeout=5,
                          env={'PATH': os.defpath, 'PYTHONIOENCODING': 'utf-8'})


def refuse(result):
    assert result.returncode == 2 and not result.stderr
    assert json.loads(result.stdout) == {'state': 'UNAVAILABLE',
        'reason': 'invalid_or_unsupported_local_citation_request', 'tags': []}


def test_resolved_unresolved_unsupported_repeated_and_exact_nfc_bindings():
    raw = 'Cafe\u0301 [1] [2] and [1]. Bad [01].'.encode()
    store = attached()
    side = c.prepare(store, raw, [(1, 'second')])
    brief, detail = c.check(store, raw, c.encoded(side))
    assert brief['counts'] == {'resolved-in-attached-corpus': 2,
        'unresolved-in-attached-corpus': 1, 'unsupported': 1}
    normalized = normalize_nfc(raw.decode())
    assert [normalized[slice(*r['span'])] for r in detail['markers']] == ['[1]', '[2]', '[1]', '[01]']
    assert side['raw_subject_sha256'] == c.sha(raw)
    assert side['subject_sha256'] == c.sha(normalized.encode())
    assert side['subject_characters'] == len(normalized)
    assert side['corpus_file_sha256'] == c.sha(store)
    row = side['mappings'][0]
    assert row['document_sha256'] == c.sha('Cafe\u0301 source.'.encode())
    assert row['normalized_document_sha256'] == c.sha('Café source.'.encode())
    assert detail['markers'][0]['declaration'] == row
    assert set(side['source_sha256']) == set(c.SOURCES)
    assert raw.decode() not in json.dumps(detail)
    assert 'An invented source.' not in json.dumps(detail)
    assert all(key not in brief for key in ('bindings', 'markers', 'subject_sha256'))
    assert brief['tags'] == [] and brief['truth_established'] is False


@pytest.mark.parametrize('text', ['[0]', '[01]', '[10000]', '[1,2]', '[1-3]', '[ 1 ]',
    '[[1]]', '\\[1]', '[1](https://example.invalid)', '[1]: reference',
    '[1][ref]', '[1](https://example.invalid/[2])', '[1][2]', '[1', ']'])
def test_unknown_syntax_never_salvages_inner_supported_number(text):
    rows = c.markers(text)
    assert rows and all(r['unsupported_reason'] and r['number'] is None for r in rows)


def test_quotes_code_and_array_meaning_not_inferred_and_no_brackets_not_global_absence():
    text = '"[1]" `x[1]` https://example.invalid Author (2020)'
    assert len(c.markers(text)) == 2
    side = c.prepare(attached(), text.encode(), [(1, 'first')])
    brief, detail = c.check(attached(), text.encode(), c.encoded(side))
    assert brief['counts']['resolved-in-attached-corpus'] == 2
    assert detail['quote_code_or_assertion_context_interpreted'] is False
    assert detail['other_citation_forms_evaluated'] is False
    empty = b'No brackets, author-year citations are not evaluated (2020).'
    brief, _ = c.check(attached(), empty, c.encoded(c.prepare(attached(), empty, [])))
    assert brief['marker_occurrences'] == 0


@pytest.mark.parametrize('pairs', [[(True, 'first')], [(0, 'first')], [(10000, 'first')],
    [(1, 'missing')], [(1, 'first'), (1, 'second')], [('1', 'first')], [(1, '../private')],
    [(n, 'first') for n in range(1, 130)]])
def test_declarations_refuse_missing_ambiguous_or_oversized_mappings(pairs):
    with pytest.raises(ValueError):
        c.prepare(attached(), b'Example [1].', pairs)


@pytest.mark.parametrize('field', ['raw_subject_sha256', 'subject_sha256', 'subject_characters',
    'normalization_id', 'offset_unit', 'corpus_file_sha256', 'corpus_manifest_sha256',
    'format', 'method', 'marker_profile', 'source_sha256'])
def test_binding_tampering_refuses(field):
    raw = b'Example [1].'
    side = c.prepare(attached(), raw, [(1, 'first')])
    side[field] = 0 if field == 'subject_characters' else 'changed'
    with pytest.raises(ValueError):
        c.check(attached(), raw, c.encoded(side))


@pytest.mark.parametrize('field', ['number', 'document_id', 'document_sha256', 'normalized_document_sha256'])
def test_document_declaration_tampering_refuses(field):
    side = c.prepare(attached(), b'[1]', [(1, 'first')])
    side['mappings'][0][field] = 2 if field == 'number' else 'changed'
    # Changing only the number to another valid declaration is a NEW explicit
    # sidecar, not a signature forgery: sidecars do not authenticate the caller.
    if field == 'number':
        brief, _ = c.check(attached(), b'[1]', c.encoded(side))
        assert brief['counts']['unresolved-in-attached-corpus'] == 1
    else:
        with pytest.raises(ValueError):
            c.check(attached(), b'[1]', c.encoded(side))


def test_no_freshness_authenticity_claim_and_corpus_v1_bytes_unchanged():
    raw = attached()
    side = c.prepare(raw, b'[1]', [(1, 'first')])
    _, report = c.check(raw, b'[1]', c.encoded(side))
    assert report['source_authenticity_or_freshness_established'] is False
    assert report['source_support_established'] is False
    assert corpus.parse(raw)['format'] == 'local-reference-corpus/v1'
    assert raw == attached()
    for changed_subject, changed_corpus in [(b'[1] edited', raw), (b'[1]', attached({'first': 'Other'}))]:
        with pytest.raises(ValueError):
            c.check(changed_corpus, changed_subject, c.encoded(side))
    # Even NFC-equivalent raw replacement requires a new explicit sidecar.
    side = c.prepare(raw, 'Cafe\u0301 [1]'.encode(), [])
    with pytest.raises(ValueError):
        c.check(raw, 'Café [1]'.encode(), c.encoded(side))


@pytest.mark.parametrize('raw', [b'{', b'{}', b'{"x":1,"x":2}', b'[]',
    b'{"x":NaN}', b'{"x":1.5}', b'{"x":123456789}', b'[' * 2000, b'x' * 65537])
def test_malformed_sidecar_has_no_partial_observation(raw):
    with pytest.raises((ValueError, RecursionError)):
        c.check(attached(), b'[1]', raw)


@pytest.mark.parametrize('mode', ['extra', 'nested_extra', 'boolean_number', 'boolean_count', 'duplicate', 'reverse'])
def test_closed_sidecar_schema_refuses_ambiguous_identity(mode):
    side = c.prepare(attached(), b'[1] [2]', [(1, 'first'), (2, 'second')])
    if mode == 'extra': side['raw_input'] = 'SYNTHETIC_PRIVATE_CANARY'
    elif mode == 'nested_extra': side['mappings'][0]['raw_input'] = 'SYNTHETIC_PRIVATE_CANARY'
    elif mode == 'boolean_number': side['mappings'][0]['number'] = True
    elif mode == 'boolean_count': side['subject_characters'] = True
    elif mode == 'duplicate': side['mappings'].append(side['mappings'][0])
    else: side['mappings'].reverse()
    with pytest.raises(ValueError):
        c.check(attached(), b'[1] [2]', c.encoded(side))


@pytest.mark.parametrize('raw', [b'', b' ', b'\xff', b'a\0b', b'x' * 8001, b'x' * 32001,
    ('[1] ' * 257).encode()])
def test_input_and_occurrence_caps_refuse_without_clipping(raw):
    with pytest.raises((ValueError, UnicodeError)):
        c.prepare(attached(), raw, [])


def test_real_cli_prepare_check_private_details_and_no_overwrite(tmp_path):
    private, subject, store = setup_files(tmp_path)
    before = store.read_bytes()
    side = private / 'sidecar.json'
    result = cli('prepare', '--subject', subject, '--corpus', store, '--map', '1=second', '--output', side)
    assert result.returncode == 0 and not result.stderr
    assert json.loads(result.stdout)['state'] == 'SIDECAR_SAVED'
    report = private / 'details.json'
    args = ('check', '--subject', subject, '--corpus', store, '--sidecar', side)
    result = cli(*args, '--private-report', report)
    assert result.returncode == 0 and not result.stderr
    brief = json.loads(result.stdout)
    assert brief['counts']['resolved-in-attached-corpus'] == brief['counts']['unresolved-in-attached-corpus'] == 1
    assert (side.stat().st_mode & 0o777) == (report.stat().st_mode & 0o777) == 0o600
    assert store.read_bytes() == before
    for data in (result.stdout, report.read_bytes(), side.read_bytes()):
        assert subject.read_bytes() not in data and b'An invented source.' not in data
    assert str(private).encode() not in result.stdout
    saved = report.read_bytes()
    refuse(cli(*args, '--private-report', report))
    assert report.read_bytes() == saved
    saved_side = side.read_bytes()
    refuse(cli('prepare', '--subject', subject, '--corpus', store, '--output', side))
    assert side.read_bytes() == saved_side


@pytest.mark.parametrize('mode', ['symlink', 'parent_symlink', 'fifo', 'hardlink', 'public', 'oversize'])
def test_real_cli_unsafe_inputs_refuse_and_create_no_outputs(tmp_path, mode):
    private, subject, store = setup_files(tmp_path)
    selected = subject
    if mode == 'symlink':
        selected = private / 'link'; selected.symlink_to(subject)
    elif mode == 'parent_symlink':
        alias = tmp_path / 'alias'; alias.symlink_to(private, target_is_directory=True); selected = alias / subject.name
    elif mode == 'fifo':
        subject.unlink(); os.mkfifo(subject, 0o600)
    elif mode == 'hardlink':
        os.link(subject, private / 'another')
    elif mode == 'public':
        subject.chmod(0o644)
    else:
        with subject.open('wb') as stream: stream.truncate(c.MAX_SUBJECT_BYTES + 1)
    output = private / 'sidecar.json'
    refuse(cli('prepare', '--subject', selected, '--corpus', store, '--output', output))
    assert not output.exists() and not list(private.glob('.citation-*'))


@pytest.mark.parametrize('mode', ['symlink', 'parent_symlink', 'public', 'existing', 'in_checkout'])
def test_output_scope_and_no_replace(tmp_path, mode):
    private, subject, store = setup_files(tmp_path)
    output = private / 'new.json'
    if mode == 'symlink': output.symlink_to(private / 'missing')
    elif mode == 'parent_symlink':
        alias = tmp_path / 'alias'; alias.symlink_to(private, target_is_directory=True); output = alias / output.name
    elif mode == 'public': private.chmod(0o755)
    elif mode == 'existing': output.write_text('SYNTHETIC_PRIVATE_CANARY')
    else: output = ROOT / 'runs' / 'not-created-citation-control.json'
    refuse(cli('prepare', '--subject', subject, '--corpus', store, '--output', output))
    if mode == 'existing': assert output.read_text() == 'SYNTHETIC_PRIVATE_CANARY'
    elif mode == 'symlink': assert output.is_symlink() and not output.exists()
    else: assert not output.exists()


@pytest.mark.parametrize('mode', ['content', 'replace', 'parent', 'after_staging'])
def test_captured_input_drift_refuses_before_atomic_publication(tmp_path, monkeypatch, mode):
    private, subject, _ = setup_files(tmp_path)
    output = private / 'new.json'
    with c.Capture() as capture:
        capture.read(subject, c.MAX_SUBJECT_BYTES)
        def mutate():
            if mode in ('content', 'after_staging'): subject.write_text('SYNTHETIC_PRIVATE_CANARY')
            elif mode == 'replace': subject.unlink(); subject.write_text('replacement')
            else: private.rename(tmp_path / 'moved'); private.mkdir(mode=0o700)
        if mode == 'after_staging':
            original = capture.check
            def check(): mutate(); original()
            monkeypatch.setattr(capture, 'check', check)
        else: mutate()
        with pytest.raises((ValueError, OSError)):
            capture.save(output, {'text_included': False}, 1000)
    assert not output.exists()
    assert not list(tmp_path.rglob('.citation-*'))


def test_oversize_refused_before_any_read(tmp_path, monkeypatch):
    private, subject, _ = setup_files(tmp_path)
    with subject.open('wb') as stream: stream.truncate(c.MAX_SUBJECT_BYTES + 1)
    def never_read(*args): raise AssertionError('Oversized input was read')
    monkeypatch.setattr(c.os, 'read', never_read)
    with c.Capture() as capture, pytest.raises(ValueError):
        capture.read(subject, c.MAX_SUBJECT_BYTES)


def test_failed_directory_durability_check_reports_uncertainty_with_complete_output(tmp_path, monkeypatch):
    private, _, _ = setup_files(tmp_path)
    output = private / 'new.json'
    original = os.fsync
    def fsync(fd):
        if stat.S_ISDIR(os.fstat(fd).st_mode):
            raise OSError('inert directory durability failure')
        return original(fd)
    monkeypatch.setattr(os, 'fsync', fsync)
    with c.Capture() as capture, pytest.raises(c.OutputCommitUncertain) as caught:
        capture.save(output, {'subject_text_included': False}, 1000)
    assert caught.value.output_may_exist is True
    assert str(caught.value) == 'Local citation output commit uncertain.'
    assert json.loads(output.read_bytes()) == {'subject_text_included': False}
    assert not list(private.glob('.citation-*'))


@pytest.mark.parametrize('mode', ['unlink', 'link_before', 'link_after'])
def test_library_uncertain_publication_never_promises_rollback(tmp_path, monkeypatch, mode):
    private, _, _ = setup_files(tmp_path)
    output = private / 'new.json'
    link, unlink = os.link, os.unlink
    linked = False
    def maybe_link(*args, **kwargs):
        nonlocal linked
        if mode == 'link_before': raise OSError('SYNTHETIC_PRIVATE_CANARY')
        result = link(*args, **kwargs)
        linked = True
        if mode == 'link_after': raise OSError('SYNTHETIC_PRIVATE_CANARY')
        return result
    def maybe_unlink(*args, **kwargs):
        if mode == 'unlink' and linked: raise OSError('SYNTHETIC_PRIVATE_CANARY')
        return unlink(*args, **kwargs)
    monkeypatch.setattr(os, 'link', maybe_link)
    monkeypatch.setattr(os, 'unlink', maybe_unlink)
    with c.Capture() as capture, pytest.raises(c.OutputCommitUncertain) as caught:
        capture.save(output, {'synthetic': True}, 1000)
    assert str(caught.value) == 'Local citation output commit uncertain.'
    assert caught.value.output_may_exist is True
    assert output.exists() is (mode != 'link_before')
    if output.exists(): assert json.loads(output.read_bytes()) == {'synthetic': True}


@pytest.mark.parametrize('published', [False, True])
def test_close_attempts_every_owned_handle_and_classifies_postcommit_failure(tmp_path, monkeypatch, published):
    private, _, _ = setup_files(tmp_path)
    capture = c.Capture()
    output = private / 'new.json'
    if published: capture.save(output, {'synthetic': True}, 1000)
    else: capture.parent(output)
    owned = list(capture.fds)
    close = os.close
    seen = []
    def fail_once(fd):
        close(fd)
        seen.append(fd)
        if len(seen) == 1: raise OSError('SYNTHETIC_PRIVATE_CANARY')
    monkeypatch.setattr(os, 'close', fail_once)
    expected = c.OutputCommitUncertain if published else c.CitationError
    with pytest.raises(expected) as caught: capture.close()
    assert isinstance(caught.value, c.OutputCommitUncertain) is published
    assert seen == list(reversed(owned)) and capture.fds == []
    capture.close()
    assert seen == list(reversed(owned))  # Never retry possibly closed/reused descriptors.
    for fd in owned:
        with pytest.raises(OSError): os.fstat(fd)
    assert output.exists() is published


FAULT_DRIVER = r'''
import importlib.abc,json,os,pathlib,runpy,stat,sys
root,mode=sys.argv[1:3];sys.path.insert(0,root)
if mode=='import':
 class Fail(importlib.abc.MetaPathFinder):
  def find_spec(self,fullname,path=None,target=None):
   if fullname=='tools.citation_resolution':raise ImportError('SYNTHETIC_PRIVATE_CANARY')
 sys.meta_path.insert(0,Fail())
else:
 from tools import citation_resolution as c
 link,unlink,fsync,close=os.link,os.unlink,os.fsync,os.close
 linked=False;closed=False;drifted=False
 original_check=c.Capture.check
 def check_fault(self):
  global drifted
  if mode=='drift' and not drifted:
   drifted=True;pathlib.Path(sys.argv[sys.argv.index('--subject')+1]).write_bytes(b'SYNTHETIC_PRIVATE_CANARY')
  return original_check(self)
 def link_fault(*args,**kwargs):
  global linked
  if mode=='link_before':raise OSError('SYNTHETIC_PRIVATE_CANARY')
  if mode=='race':
   fd=os.open(args[1],os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600,dir_fd=kwargs['dst_dir_fd'])
   with os.fdopen(fd,'wb') as stream:stream.write(b'EXISTING_DESTINATION')
  result=link(*args,**kwargs);linked=True
  if mode=='link_after':raise OSError('SYNTHETIC_PRIVATE_CANARY')
  return result
 def unlink_fault(*args,**kwargs):
  if mode=='unlink' and linked:raise OSError('SYNTHETIC_PRIVATE_CANARY')
  return unlink(*args,**kwargs)
 def fsync_fault(fd):
  if (mode=='fsync' and linked and stat.S_ISDIR(os.fstat(fd).st_mode)) or (mode=='pre_fsync' and not linked):raise OSError('SYNTHETIC_PRIVATE_CANARY')
  return fsync(fd)
 def close_fault(fd):
  global closed
  close(fd)
  if mode=='close' and linked and not closed:
   closed=True;raise OSError('SYNTHETIC_PRIVATE_CANARY')
 os.link=link_fault;os.unlink=unlink_fault;os.fsync=fsync_fault;os.close=close_fault;c.Capture.check=check_fault
sys.argv=[str(pathlib.Path(root)/'scripts/citation-resolution.py'),*sys.argv[3:]]
runpy.run_path(sys.argv[0],run_name='__main__')
'''


def fault_cli(mode, *args):
    return subprocess.run([sys.executable, '-I', '-S', '-B', '-c', FAULT_DRIVER,
        str(ROOT), mode, *map(str, args)], capture_output=True, timeout=5,
        env={'PATH': os.defpath, 'PYTHONIOENCODING': 'utf-8'})


@pytest.mark.parametrize('mode', ['unlink', 'fsync', 'close', 'link_before', 'link_after'])
@pytest.mark.parametrize('command', ['prepare', 'check'])
def test_actual_cli_postpublication_failures_are_fixed_uncertainty(tmp_path, mode, command):
    private, subject, store = setup_files(tmp_path)
    side = private / 'sidecar.json'
    if command == 'prepare':
        output = side
        args = ('prepare', '--subject', subject, '--corpus', store, '--map', '1=first', '--output', output)
    else:
        result = cli('prepare', '--subject', subject, '--corpus', store, '--map', '1=first', '--output', side)
        assert result.returncode == 0
        output = private / 'report.json'
        args = ('check', '--subject', subject, '--corpus', store, '--sidecar', side, '--private-report', output)
    result = fault_cli(mode, *args)
    assert result.returncode == 2 and not result.stderr
    assert json.loads(result.stdout) == {'state': 'UNAVAILABLE', 'reason': 'output_commit_uncertain',
                                       'output_may_exist': True, 'tags': []}
    assert output.exists() is (mode != 'link_before')
    if output.exists():
        value = json.loads(output.read_bytes())
        assert value['format'] == ('local-citation-sidecar/v1' if command == 'prepare' else 'local-citation-evidence/v1')
        assert output.stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize('mode', ['pre_fsync', 'import', 'race', 'drift'])
def test_actual_cli_precommit_and_import_refusals_stay_generic_and_private(tmp_path, mode):
    private, subject, store = setup_files(tmp_path)
    output = private / 'new.json'
    result = fault_cli(mode, 'prepare', '--subject', subject, '--corpus', store, '--output', output)
    refuse(result)
    if mode == 'race': assert output.read_bytes() == b'EXISTING_DESTINATION'
    else: assert not output.exists()


@pytest.mark.parametrize('args', [('SYNTHETIC_PRIVATE_CANARY',), ('--unknown=SYNTHETIC_PRIVATE_CANARY',),
    ('prepare', '--subject'), ('check', '--private-report', 'SYNTHETIC_PRIVATE_CANARY')])
def test_actual_cli_bad_arguments_use_fixed_no_echo_diagnostic(args):
    refuse(cli(*args))


def test_optional_module_failure_does_not_disable_quantitative_or_corpus_route():
    code = '''import importlib.abc,sys
class Refuse(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname=='tools.citation_resolution':raise SyntaxError('SYNTHETIC_PRIVATE_CANARY')
sys.meta_path.insert(0,Refuse())
try:from tools import citation_resolution
except SyntaxError:pass
else:raise AssertionError('Optional failure not exercised')
from tools.quantitative_observations import observe
assert observe('There are 12 entries.','en')[0]['supported_detail_count']==1
from protocol import corpus
assert corpus.query({'manifest_sha256':'synthetic','documents':[]},'needle')['state']=='NO_REFERENCE_MATCH'
'''
    result = subprocess.run([sys.executable, '-B', '-c', code], cwd=ROOT, capture_output=True, timeout=5)
    assert result.returncode == 0 and not result.stdout and not result.stderr
