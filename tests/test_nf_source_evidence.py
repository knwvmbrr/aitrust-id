"""Selected pair composition, containment and actual standalone privacy controls."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest
from protocol import corpus
from protocol.normalization import normalize_nfc
from tools import nf_source_evidence as nf

ROOT = Path(__file__).absolute().parents[1]
CLI = ROOT / 'scripts/check-nf-source-evidence.py'


def fixture(subject='Prefix Water is safe. End.', source='Before\nWater is not safe.\nAfter'):
    body = {'format': corpus.VERSION, 'documents': [
        {'id': 'manual', 'sha256': nf.sha(source.encode()), 'text': source}]}
    raw = corpus.encoded({**body, 'manifest_sha256': nf.sha(corpus.encoded(body))})
    text, document = normalize_nfc(subject), normalize_nfc(source)
    claim, passage = text[7:-5], document[7:-6]
    selection = {'format': 'nf-pair-selections/v1', 'pairs': [
        {'claim_span': [7, 7 + len(claim)], 'document_id': 'manual', 'source_span': [7, 7 + len(passage)]}]}
    return raw, subject.encode(), selection


def bound(raw=None, text=None, selection=None, checks=None):
    default = fixture()
    raw, text, selection = [v if v is not None else d for v, d in zip((raw, text, selection), default)]
    with nf.io.Capture() as capture:
        return nf.bind(raw, text, selection, checks or ['literal', 'cosine'], capture)


def execute(raw, text, side):
    with nf.io.Capture() as capture:
        return nf.check(raw, text, nf.io.encoded(side), capture)


def files(tmp_path, data=None):
    p = tmp_path / 'private'; p.mkdir(mode=0o700)
    raw, text, selection = data or fixture()
    for name, value in [('corpus.json', raw), ('subject.txt', text), ('selection.json', nf.io.encoded(selection))]:
        (p / name).write_bytes(value); (p / name).chmod(0o600)
    return p


def cli(*args, root=ROOT):
    return subprocess.run([sys.executable, '-I', '-S', '-B', str(root / 'scripts/check-nf-source-evidence.py'),
        *map(str, args)], capture_output=True, timeout=25,
        env={'PATH': os.defpath, 'PYTHONIOENCODING': 'utf-8'})


def prepare_args(p):
    return ('prepare', '--subject', p / 'subject.txt', '--corpus', p / 'corpus.json',
            '--selections', p / 'selection.json', '--check', 'literal', '--check', 'cosine', '--output', p / 'sidecar.json')


def check_args(p):
    return ('check', '--subject', p / 'subject.txt', '--corpus', p / 'corpus.json', '--sidecar', p / 'sidecar.json')


def test_actual_workers_separate_misleading_similarity_from_literal_absence_and_rebase():
    raw, text, selection = fixture()
    result = execute(raw, text, bound())
    assert result['state'] == 'COMPLETE'
    literal, cosine = result['checks']
    assert literal['observation']['rows'][0]['matches'] == []
    match = cosine['observation']['rows'][0]['matches'][0]
    assert text.decode()[slice(*match['claim_span'])] == 'Water is safe.'
    assert json.loads(raw)['documents'][0]['text'][slice(*match['source_span'])] == 'Water is not safe.'
    assert .75 <= match['cosine'] < 1 and result['truth_established'] is False
    assert result['tags'] == [] and result['semantic_support_established'] is False
    for row in result['checks']:
        assert row['observation']['ipv4_ipv6_denied'] is True
        assert row['observation']['network_control'] in ('macos_sandbox_deny_network', 'linux_seccomp_deny_network')
    assert text.decode() not in json.dumps(result) and 'Water is not safe.' not in json.dumps(result)


def test_unicode_exact_completes_when_cosine_unavailable_and_raw_nfc_identity_distinct():
    raw, text, selection = fixture('Prefix Cafe\u0301 details. End.', 'Before\nCafe\u0301 details.\nAfter')
    side = bound(raw, text, selection)
    result = execute(raw, text, side)
    assert result['state'] == 'PARTIAL'
    literal, cosine = result['checks']
    assert literal['state'] == 'COMPLETE' and cosine['state'] == 'UNAVAILABLE'
    match = literal['observation']['rows'][0]['matches'][0]
    assert normalize_nfc(text.decode())[slice(*match['claim_span'])] == 'Café details.'
    assert match['source_span'] == selection['pairs'][0]['source_span']
    assert side['raw_subject_sha256'] != side['subject_sha256']
    assert side['pairs'][0]['document_sha256'] != side['pairs'][0]['normalized_document_sha256']


def test_exact_cap_and_projection_identity_are_explicit():
    pairs = [{'claim': 'A', 'passage': 'A ' * 20}]
    row = nf.evaluate('literal', pairs)[0]
    assert len(row['matches']) == 10 and row['limit_reached'] is True
    assert row['projection_document_sha256'] == nf.sha(pairs[0]['passage'].encode())


@pytest.mark.parametrize('field', ['format', 'normalization_id', 'offset_unit', 'raw_subject_sha256',
    'subject_sha256', 'subject_characters', 'corpus_file_sha256', 'corpus_manifest_sha256', 'source_sha256'])
def test_sidecar_common_binding_tamper_refuses(field):
    side = bound(); side[field] = True if field == 'subject_characters' else 'corrupt'
    with nf.io.Capture() as capture, pytest.raises((ValueError, TypeError)):
        nf.validate_sidecar(*fixture()[:2], nf.io.encoded(side), capture)


@pytest.mark.parametrize('field', ['claim_sha256', 'document_sha256', 'normalized_document_sha256', 'passage_sha256'])
def test_pair_digest_tamper_refuses(field):
    side = bound(); side['pairs'][0][field] = '0' * 64
    with nf.io.Capture() as capture, pytest.raises(ValueError):
        nf.validate_sidecar(*fixture()[:2], nf.io.encoded(side), capture)


@pytest.mark.parametrize('span', [[True, 9], [-1, 4], [2, 2], [7, 99999], [7, 2010], [7.0, 9]])
def test_bad_span_selection_refuses(span):
    raw, text, selection = fixture(); selection['pairs'][0]['claim_span'] = span
    with pytest.raises(ValueError): bound(raw, text, selection)


@pytest.mark.parametrize('mode', ['extra', 'nested_extra', 'missing_document', 'duplicate', 'too_many', 'empty', 'unknown_check', 'duplicate_check'])
def test_closed_selection_and_component_caps(mode):
    raw, text, selection = fixture(); checks = ['literal', 'cosine']
    if mode == 'extra': selection['raw_input'] = 'SYNTHETIC_PRIVATE_CANARY'
    elif mode == 'nested_extra': selection['pairs'][0]['raw_input'] = 'SYNTHETIC_PRIVATE_CANARY'
    elif mode == 'missing_document': selection['pairs'][0]['document_id'] = 'absent'
    elif mode == 'duplicate': selection['pairs'] *= 2
    elif mode == 'too_many': selection['pairs'] *= 9
    elif mode == 'empty': selection['pairs'] = []
    elif mode == 'unknown_check': checks = ['FI']
    else: checks = ['literal', 'literal']
    with nf.io.Capture() as capture, pytest.raises(ValueError): nf.bind(raw, text, selection, checks, capture)


@pytest.mark.parametrize('raw', [b'{}', b'{"x":1,"x":2}', b'[]', b'{"x":NaN}', b'[' * 1000, b'x' * 65537])
def test_bad_json_has_no_observation(raw):
    with nf.io.Capture() as capture, pytest.raises((ValueError, RecursionError)):
        nf.validate_sidecar(*fixture()[:2], raw, capture)


@pytest.mark.parametrize('kind', ['literal', 'cosine'])
def test_worker_failure_isolated_and_not_a_negative_observation(monkeypatch, kind):
    original = nf.run_check
    def run(check, *args):
        return {'component': check, 'state': 'UNAVAILABLE', 'reason': 'selected_check_unavailable'} if check == kind else original(check, *args)
    monkeypatch.setattr(nf, 'run_check', run)
    result = execute(*fixture()[:2], bound())
    assert result['state'] == 'PARTIAL'
    assert [r['state'] for r in result['checks']] == (['UNAVAILABLE', 'COMPLETE'] if kind == 'literal' else ['COMPLETE', 'UNAVAILABLE'])


def test_real_cli_private_exports_no_overwrite_and_rebinding_refusal(tmp_path):
    p = files(tmp_path)
    assert cli(*prepare_args(p)).returncode == 0
    original = (p / 'sidecar.json').read_bytes()
    report = p / 'report.json'
    result = cli(*check_args(p), '--private-report', report)
    assert result.returncode == 0 and not result.stderr
    assert json.loads(result.stdout)['state'] == 'COMPLETE'
    assert report.stat().st_mode & 0o777 == 0o600
    assert (p / 'subject.txt').read_bytes() not in report.read_bytes() + result.stdout
    assert str(p).encode() not in result.stdout and b'claim_span' not in result.stdout
    saved = report.read_bytes()
    assert cli(*check_args(p), '--private-report', report).returncode == 2
    assert report.read_bytes() == saved
    assert cli(*prepare_args(p)).returncode == 2 and (p / 'sidecar.json').read_bytes() == original
    (p / 'subject.txt').write_text('Changed selected subject.')
    refused = cli(*check_args(p), '--private-report', p / 'absent.json')
    assert refused.returncode == 2 and not refused.stderr and not (p / 'absent.json').exists()


@pytest.mark.parametrize('mode', ['symlink', 'parent_link', 'fifo', 'hardlink', 'public', 'oversize'])
def test_actual_cli_unsafe_input_no_new_output(tmp_path, mode):
    p = files(tmp_path); subject = p / 'subject.txt'
    if mode == 'symlink': subject.rename(p / 'moved'); subject.symlink_to(p / 'moved')
    elif mode == 'parent_link':
        original = p; p = tmp_path / 'alias'; p.symlink_to(original, target_is_directory=True)
    elif mode == 'fifo': subject.unlink(); os.mkfifo(subject, 0o600)
    elif mode == 'hardlink': os.link(subject, p / 'duplicate')
    elif mode == 'public': subject.chmod(0o644)
    else:
        with subject.open('wb') as stream: stream.truncate(nf.MAX_SUBJECT_BYTES + 1)
    result = cli(*prepare_args(p))
    assert result.returncode == 2 and not result.stderr and not (p / 'sidecar.json').exists()
    assert json.loads(result.stdout)['reason'] == 'invalid_or_unsupported_selected_source_request'


def copy_source(root):
    names = set(nf.COMMON) | {'protocol/corpus_support.py'}
    for name in names:
        path = root / name; path.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(ROOT / name, path)


def test_real_fi_absent_and_broken_cosine_cannot_stop_exact(tmp_path):
    copied = tmp_path / 'source'; copy_source(copied)
    assert not (copied / 'tools/citation_resolution.py').exists()
    p = files(tmp_path)
    assert cli(*prepare_args(p), root=copied).returncode == 0
    (copied / 'protocol/corpus_support.py').write_text('raise SyntaxError("SYNTHETIC_PRIVATE_CANARY")')
    result = cli(*check_args(p), root=copied)
    assert result.returncode == 0 and not result.stderr
    value = json.loads(result.stdout)
    assert value['state'] == 'PARTIAL' and [r['state'] for r in value['checks']] == ['COMPLETE', 'UNAVAILABLE']


def test_real_broken_nf_does_not_stop_independent_quantitative_cli(tmp_path):
    copied = tmp_path / 'source'; copy_source(copied)
    for name in ('tools/language_observations.py', 'tools/quantitative_observations.py', 'scripts/quantitative-observations.py'):
        path = copied / name; path.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(ROOT / name, path)
    (copied / 'tools/nf_source_evidence.py').write_text('raise SyntaxError("SYNTHETIC_PRIVATE_CANARY")')
    result = subprocess.run([sys.executable, '-I', '-S', '-B', str(copied / 'scripts/quantitative-observations.py'), '--language', 'en'],
        input=b'There are 12 entries.', capture_output=True, timeout=5)
    assert result.returncode == 0 and not result.stderr and json.loads(result.stdout)['supported_detail_count'] == 1


@pytest.mark.parametrize('fault', ['timeout', 'output_limit', 'bad_json', 'identity'])
def test_supervision_failures_become_only_selected_unavailable(tmp_path, monkeypatch, fault):
    def supervisor(*args, **kwargs):
        if fault == 'timeout': raise subprocess.TimeoutExpired('fixed worker', 8)
        if fault == 'output_limit': raise RuntimeError('SYNTHETIC_PRIVATE_CANARY')
        return subprocess.CompletedProcess([], 0, b'{}' if fault == 'identity' else b'{')
    monkeypatch.setattr(nf.runpy, 'run_path', lambda _: {'run_worker': supervisor})
    with nf.io.Capture() as capture:
        result = nf.run_check('literal', [{'claim': 'A', 'passage': 'A'}], {}, capture)
    assert result == {'component': 'literal', 'state': 'UNAVAILABLE', 'reason': 'selected_check_unavailable'}


@pytest.mark.parametrize('kind', ['literal', 'cosine'])
@pytest.mark.parametrize('mode', ['outer_extra', 'row_extra', 'inner_extra', 'wrong_request',
    'wrong_source', 'wrong_projection', 'wrong_span', 'duplicate', 'wrong_state', 'boolean_index'])
def test_closed_worker_results_reject_corruption_before_rebasing(kind, mode):
    pairs = [{'claim': 'Water is safe.', 'passage': 'Water is safe.'}]
    sources = {'fixed': '0' * 64}
    value = {'component': kind, 'method': nf.METHODS[kind], 'request_sha256': '1' * 64,
             'source_sha256': sources, 'network_control': {'Darwin': 'macos_sandbox_deny_network',
             'Linux': 'linux_seccomp_deny_network'}[sys.platform == 'darwin' and 'Darwin' or 'Linux'],
             'ipv4_ipv6_denied': True, 'rows': nf.evaluate(kind, pairs)}
    if mode == 'outer_extra': value['raw_input'] = 'SYNTHETIC_PRIVATE_CANARY'
    elif mode == 'row_extra': value['rows'][0]['raw_input'] = 'SYNTHETIC_PRIVATE_CANARY'
    elif mode == 'inner_extra': value['rows'][0]['matches'][0]['raw_input'] = 'SYNTHETIC_PRIVATE_CANARY'
    elif mode == 'wrong_request': value['request_sha256'] = '2' * 64
    elif mode == 'wrong_source': value['source_sha256'] = {}
    elif mode == 'wrong_projection': value['rows'][0]['projection_document_sha256'] = '2' * 64
    elif mode == 'wrong_span': value['rows'][0]['matches'][0]['source_span'] = [1, 2]
    elif mode == 'duplicate': value['rows'][0]['matches'] *= 2
    elif mode == 'wrong_state': value['rows'][0]['state'] = 'VERIFIED'
    else: value['rows'][0]['pair_index'] = False
    with pytest.raises((ValueError, TypeError)):
        nf.validate_output(value, kind, pairs, '1' * 64, sources)


@pytest.mark.parametrize('mode', ['forged_score', 'omitted_matches'])
def test_canonical_cosine_replay_rejects_plausible_corruption(mode):
    pairs = [{'claim': 'Water is safe.', 'passage': 'Water is not safe.'}]
    sources = {'fixed': '0' * 64}
    rows = nf.evaluate('cosine', pairs)
    if mode == 'forged_score': rows[0]['matches'][0]['cosine'] = 1.0
    else: rows[0]['matches'] = []; rows[0]['state'] = 'NO_SIMILAR_PASSAGE'
    value = {'component': 'cosine', 'method': nf.METHODS['cosine'], 'request_sha256': '1' * 64,
        'source_sha256': sources, 'network_control': 'macos_sandbox_deny_network' if sys.platform == 'darwin'
        else 'linux_seccomp_deny_network', 'ipv4_ipv6_denied': True, 'rows': rows}
    with pytest.raises(ValueError): nf.validate_output(value, 'cosine', pairs, '1' * 64, sources)


@pytest.mark.parametrize('mode', ['forged_score', 'omitted_matches'])
def test_real_cosine_worker_record_corruption_keeps_literal_available(monkeypatch, mode):
    validate = nf.validate_output
    def corrupt(value, kind, *args):
        if kind == 'cosine':
            if mode == 'forged_score': value['rows'][0]['matches'][0]['cosine'] = 1.0
            else: value['rows'][0]['matches'] = []; value['rows'][0]['state'] = 'NO_SIMILAR_PASSAGE'
        return validate(value, kind, *args)
    monkeypatch.setattr(nf, 'validate_output', corrupt)
    value = execute(*fixture()[:2], bound())
    assert value['state'] == 'PARTIAL' and [v['state'] for v in value['checks']] == ['COMPLETE', 'UNAVAILABLE']


@pytest.mark.parametrize('mode', ['timeout', 'output_limit'])
def test_actual_owned_worker_timeout_or_output_limit_preserves_sibling(tmp_path, mode):
    copied = tmp_path / 'source'; copy_source(copied)
    worker = copied / 'scripts/nf-source-worker.py'
    code = worker.read_text()
    anchor = "        kind, pairs = request['component'], request['pairs']\n"
    assert code.count(anchor) == 1
    action = ('import time; time.sleep(30)' if mode == 'timeout' else
              "sys.stdout.buffer.write(b'x' * (nf.MAX_RESULT_BYTES + 1)); sys.stdout.buffer.flush(); return 0")
    worker.write_text(code.replace(anchor, anchor + "        if kind == 'literal':\n            " + action + '\n'))
    p = files(tmp_path)
    assert cli(*prepare_args(p), root=copied).returncode == 0
    result = cli(*check_args(p), root=copied)
    assert result.returncode == 0 and not result.stderr
    value = json.loads(result.stdout)
    assert value['state'] == 'PARTIAL' and [r['state'] for r in value['checks']] == ['UNAVAILABLE', 'COMPLETE']


def test_prepublication_input_drift_never_commits_new_final(tmp_path):
    p = files(tmp_path); source = p / 'subject.txt'; output = p / 'not-created.json'
    with nf.io.Capture() as capture:
        capture.read(source, nf.MAX_SUBJECT_BYTES)
        source.write_text('SYNTHETIC_PRIVATE_CANARY')
        with pytest.raises(ValueError): capture.save(output, {'text_included': False}, 1000)
    assert not output.exists() and not list(p.glob('.nf-evidence-*'))


def test_raw_close_error_after_descriptor_reuse_does_not_close_replacement(tmp_path, monkeypatch):
    p = files(tmp_path); output = p / 'not-created.json'
    fdopen, close = os.fdopen, os.close
    raw = None; replacement = None; attempts = []
    def construction_failure(fd, *args, **kwargs):
        nonlocal raw
        assert kwargs['closefd'] is False
        raw = fd; raise OSError('SYNTHETIC_PRIMARY')
    def close_error(fd):
        nonlocal replacement
        attempts.append(fd); close(fd)
        if fd == raw:
            replacement = os.open(os.devnull, os.O_RDONLY)
            assert replacement == raw
            raise OSError('SYNTHETIC_SECONDARY')
    monkeypatch.setattr(os, 'fdopen', construction_failure); monkeypatch.setattr(os, 'close', close_error)
    try:
        with pytest.raises(OSError, match='SYNTHETIC_PRIMARY'):
            with nf.io.Capture() as capture: capture.save(output, {'synthetic': True}, 1000)
        assert attempts.count(raw) == 1 and capture.fds == [] and not output.exists()
        os.fstat(replacement)
    finally:
        if replacement is not None: close(replacement)


def test_private_inputs_inside_checkout_refuse_before_read(tmp_path, monkeypatch):
    p = files(tmp_path)
    monkeypatch.setattr(nf.io, 'ROOT', tmp_path)
    with nf.io.Capture() as capture, pytest.raises(ValueError): capture.read(p / 'subject.txt', nf.MAX_SUBJECT_BYTES)


def test_all_checks_unavailable_does_not_create_private_report(tmp_path):
    copied = tmp_path / 'source'; copy_source(copied)
    (copied / 'scripts/nf-source-worker.py').write_text('print(\'{"state":"UNAVAILABLE"}\');raise SystemExit(2)')
    p = files(tmp_path)
    assert cli(*prepare_args(p), root=copied).returncode == 0
    report = p / 'not-created.json'
    result = cli(*check_args(p), '--private-report', report, root=copied)
    assert result.returncode == 2 and not result.stderr and not report.exists()
    assert json.loads(result.stdout)['private_report_saved'] is False


IO_DRIVER = r'''
import os,pathlib,runpy,stat,sys
root,mode=sys.argv[1:3];sys.path.insert(0,root)
from tools import nf_source_evidence as nf
original={name:getattr(os,name) for name in ('fdopen','link','unlink','fsync','close')}
raw=None;linked=False;replacement=None;attempts=0;owned=[]
def fdopen(fd,*args,**kwargs):
 global raw
 assert kwargs['closefd'] is False
 raw=fd
 if mode in ('fdopen','fdopen_reuse'):raise OSError('SYNTHETIC_PRIVATE_CANARY')
 return original['fdopen'](fd,*args,**kwargs)
def link(*args,**kwargs):
 global linked
 if mode=='link_unknown':raise OSError('SYNTHETIC_PRIVATE_CANARY')
 result=original['link'](*args,**kwargs);linked=True;return result
def unlink(*args,**kwargs):
 if mode=='unlink' and linked:raise OSError('SYNTHETIC_PRIVATE_CANARY')
 return original['unlink'](*args,**kwargs)
def fsync(fd):
 if mode=='fsync' and linked:raise OSError('SYNTHETIC_PRIVATE_CANARY')
 return original['fsync'](fd)
def close(fd):
 global attempts,replacement
 original['close'](fd)
 if fd==raw:
  attempts+=1
  if mode=='fdopen_reuse':
   replacement=os.open(os.devnull,os.O_RDONLY);assert replacement==raw
   raise OSError('SYNTHETIC_PRIVATE_CANARY')
  if mode=='close':raise OSError('SYNTHETIC_PRIVATE_CANARY')
capture_close=nf.io.Capture.close
def close_capture(self):owned.extend(self.fds);return capture_close(self)
nf.io.Capture.close=close_capture
for name in original:setattr(os,name,globals()[name])
sys.argv=[str(pathlib.Path(root)/'scripts/check-nf-source-evidence.py'),*sys.argv[3:]]
try:runpy.run_path(sys.argv[0],run_name='__main__')
except SystemExit:
 assert raw is not None and attempts==1
 for fd in owned:
  if fd==replacement:continue
  try:os.fstat(fd)
  except OSError:pass
  else:raise AssertionError('Owned handle leaked')
 if replacement is not None:os.fstat(replacement);original['close'](replacement)
 raise
'''


def io_cli(mode, *args):
    return subprocess.run([sys.executable, '-I', '-S', '-B', '-c', IO_DRIVER, str(ROOT), mode, *map(str,args)],
        capture_output=True, timeout=5, env={'PATH':os.defpath,'PYTHONIOENCODING':'utf-8'})


@pytest.mark.parametrize('mode', ['fdopen', 'fdopen_reuse', 'fsync', 'unlink', 'link_unknown', 'close'])
def test_actual_cli_io_faults_are_private_and_honest(tmp_path, mode):
    p = files(tmp_path)
    result = io_cli(mode, *prepare_args(p))
    assert result.returncode == 2 and not result.stderr and b'SYNTHETIC_PRIVATE_CANARY' not in result.stdout
    value = json.loads(result.stdout)
    if mode in ('fdopen', 'fdopen_reuse'):
        assert value['reason'] == 'invalid_or_unsupported_selected_source_request'
    else:
        assert value['reason'] == 'output_commit_uncertain' and value['output_may_exist'] is True
    assert (p / 'sidecar.json').exists() is (mode in ('fsync', 'unlink', 'close'))


@pytest.mark.parametrize('mode', ['fdopen', 'fsync', 'unlink', 'link_unknown', 'close'])
def test_nf_owned_io_failures_keep_refusal_or_uncertainty_and_no_raw_leak(tmp_path, monkeypatch, mode):
    p = files(tmp_path); output = p / 'new.json'
    io = nf.io; original = {name: getattr(os, name) for name in ('fdopen', 'fsync', 'unlink', 'link', 'close')}
    raw_fd = None; linked = False; closes = []
    def fdopen(fd, *a, **kw):
        nonlocal raw_fd
        assert kw['closefd'] is False
        raw_fd = fd
        if mode == 'fdopen': raise OSError('SYNTHETIC_PRIVATE_CANARY')
        return original['fdopen'](fd, *a, **kw)
    def link(*a, **kw):
        nonlocal linked
        if mode == 'link_unknown': raise OSError('SYNTHETIC_PRIVATE_CANARY')
        value = original['link'](*a, **kw); linked = True; return value
    def fsync(fd):
        if mode == 'fsync' and linked: raise OSError('SYNTHETIC_PRIVATE_CANARY')
        return original['fsync'](fd)
    def unlink(*a, **kw):
        if mode == 'unlink' and linked: raise OSError('SYNTHETIC_PRIVATE_CANARY')
        return original['unlink'](*a, **kw)
    def close(fd):
        closes.append(fd); original['close'](fd)
        if mode == 'close' and fd == raw_fd: raise OSError('SYNTHETIC_PRIVATE_CANARY')
    for name in original: monkeypatch.setattr(os, name, locals()[name])
    expected = OSError if mode == 'fdopen' else io.OutputCommitUncertain
    with pytest.raises(expected):
        with io.Capture() as capture: capture.save(output, {'synthetic': True}, 1000)
    assert closes.count(raw_fd) == 1 and capture.fds == []
    with pytest.raises(OSError): os.fstat(raw_fd)
    assert output.exists() is (mode in ('fsync', 'unlink', 'close'))


@pytest.mark.parametrize('args', [('--private-SYNTHETIC_PRIVATE_CANARY',), ('prepare', '--subject'), ('unknown',)])
def test_bad_cli_arguments_are_fixed_and_nonleaking(args):
    result = cli(*args)
    assert result.returncode == 2 and not result.stderr and b'SYNTHETIC_PRIVATE_CANARY' not in result.stdout
