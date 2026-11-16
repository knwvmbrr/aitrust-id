"""Fail closed on incomplete native workflow results and unsafe output locations."""
import runpy
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
verifier = runpy.run_path(str(ROOT / 'scripts/verify-ios-share.py'))


def test_complete_native_summary():
    assert verifier['accepted_summary']({'result': 'Passed', 'totalTestCount': 5,
                                        'passedTests': 5, 'failedTests': 0, 'skippedTests': 0})


@pytest.mark.parametrize('field,value', [('result', 'Failed'), ('totalTestCount', 4),
    ('totalTestCount', 6), ('totalTestCount', 5.0), ('passedTests', 4), ('failedTests', 1),
    ('failedTests', False), ('skippedTests', 1), ('skippedTests', False), ('testFailures', ['failure'])])
def test_incomplete_summary_refused(field, value):
    summary = {'result': 'Passed', 'totalTestCount': 5, 'passedTests': 5, 'failedTests': 0, 'skippedTests': 0}
    summary[field] = value
    assert not verifier['accepted_summary'](summary)


@pytest.mark.parametrize('value', [None, [], {}, {'result': 'Passed'}])
def test_missing_summary_refused(value):
    assert not verifier['accepted_summary'](value)


@pytest.mark.parametrize('git_kind', ['directory', 'worktree-file'])
def test_every_git_checkout_refused_before_output_creation(tmp_path, git_kind):
    root = tmp_path / 'unrelated'; root.mkdir()
    if git_kind == 'directory': (root / '.git').mkdir()
    else: (root / '.git').write_text('gitdir: /unrelated/checkout')
    with pytest.raises(ValueError): verifier['destination'](root / 'new-proof')
    assert not (root / 'new-proof').exists()


def test_existing_destination_and_broken_symlink_refused(tmp_path):
    target = tmp_path / 'keep'; target.mkdir(); (target / 'sentinel').write_text('unchanged')
    link = tmp_path / 'link'; link.symlink_to(tmp_path / 'missing')
    for path in [target, link]:
        with pytest.raises(ValueError): verifier['destination'](path)
    assert (target / 'sentinel').read_text() == 'unchanged'


def test_new_non_git_destination_is_only_validated(tmp_path):
    target = tmp_path / 'new-proof'
    assert verifier['destination'](target) == target
    assert not target.exists()


def test_simulator_uuid_case_is_preserved_for_xcode_destination():
    identity = '706597C7-9A9E-4F75-9DE8-48F211D005D4'
    assert verifier['simulator_identity'](identity) == identity
    for invalid in ['not-a-device', '{' + identity + '}', identity.replace('-', '')]:
        with pytest.raises(ValueError): verifier['simulator_identity'](invalid)


@pytest.mark.parametrize('exit_status', [0, 7])
def test_actual_command_exit_and_diagnostics_retained(tmp_path, exit_status):
    import sys
    report = {'command_events': []}
    argv = [sys.executable, '-c', f"import sys; print('synthetic diagnostic'); sys.exit({exit_status})"]
    options = dict(output=tmp_path, stage='synthetic', report=report, created=True)
    if exit_status:
        with pytest.raises(ValueError, match='command failed'):
            verifier['run_command'](argv, **options)
    else:
        assert verifier['run_command'](argv, **options) == 'synthetic diagnostic'
    event = report['command_events'][0]
    assert event['returncode'] == exit_status
    assert event['outcome'] == ('nonzero_exit' if exit_status else 'passed')
    assert event['finished_at'] >= event['started_at']
    assert 'synthetic diagnostic' in (tmp_path / 'synthetic.log').read_text()


def test_actual_deadline_kills_child_and_records_failure(tmp_path):
    import sys, os
    pid = tmp_path / 'child.pid'
    report = {'command_events': []}
    code = f"import os,time,pathlib; pathlib.Path({str(pid)!r}).write_text(str(os.getpid())); time.sleep(20)"
    with pytest.raises(ValueError, match='deadline'):
        verifier['run_command']([sys.executable, '-c', code], output=tmp_path,
            stage='synthetic_deadline', report=report, created=True, timeout=.5)
    assert report['command_events'][0]['outcome'] == 'deadline'
    with pytest.raises(ProcessLookupError): os.kill(int(pid.read_text()), 0)
    assert (tmp_path / 'synthetic_deadline.log').exists()


def test_terminal_progress_survives_actual_deadline(tmp_path):
    import sys, hashlib
    report = {'command_events': []}
    # No explicit flush: native tools line-buffer only when stdout is a TTY.
    code = "import sys,time; print('tty=' + str(sys.stdout.isatty())); print('synthetic boot phase'); time.sleep(20)"
    with pytest.raises(ValueError, match='deadline'):
        verifier['run_command']([sys.executable, '-c', code], output=tmp_path,
            stage='terminal_deadline', report=report, created=True, timeout=1,
            terminal_output=True)
    retained = (tmp_path / 'terminal_deadline.log').read_bytes()
    assert b'tty=True' in retained and b'synthetic boot phase' in retained
    event = report['command_events'][0]
    assert event['outcome'] == 'deadline' and event['returncode'] < 0
    assert event['output_transport'] == 'pty'
    assert event['output_bytes'] == len(retained)
    assert event['output_sha256'] == hashlib.sha256(retained).hexdigest()


@pytest.mark.parametrize('exit_status', [0, 7])
def test_terminal_quick_exit_preserves_output_and_status(tmp_path, exit_status):
    import sys
    report = {'command_events': []}
    argv = [sys.executable, '-c', f"import sys; print('synthetic boot phase'); sys.exit({exit_status})"]
    options = dict(output=tmp_path, stage='terminal_exit', report=report,
                   created=True, terminal_output=True)
    if exit_status:
        with pytest.raises(ValueError, match='command failed'):
            verifier['run_command'](argv, **options)
    else:
        assert verifier['run_command'](argv, **options) == 'synthetic boot phase'
    assert b'synthetic boot phase' in (tmp_path / 'terminal_exit.log').read_bytes()
    assert report['command_events'][0]['returncode'] == exit_status


def test_terminal_output_larger_than_pty_buffer_does_not_block(tmp_path):
    import sys
    report = {'command_events': []}
    result = verifier['run_command']([sys.executable, '-c', "print('x' * 100000)"],
        output=tmp_path, stage='terminal_burst', report=report, created=True,
        timeout=5, terminal_output=True)
    assert result == 'x' * 100000
    assert report['command_events'][0]['outcome'] == 'passed'


def test_terminal_descriptors_close_when_process_cannot_start(tmp_path, monkeypatch):
    import os
    captured = []
    original = verifier['pty'].openpty
    def opened():
        pair = original(); captured.extend(pair); return pair
    def unavailable(*args, **kwargs):
        raise OSError('synthetic unavailable executable')
    monkeypatch.setattr(verifier['pty'], 'openpty', opened)
    monkeypatch.setattr(verifier['subprocess'], 'Popen', unavailable)
    report = {'command_events': []}
    with pytest.raises(OSError, match='unavailable executable'):
        verifier['run_command'](['synthetic-unavailable'], output=tmp_path,
            stage='terminal_spawn', report=report, created=True, terminal_output=True)
    assert len(captured) == 2
    for descriptor in captured:
        with pytest.raises(OSError): os.fstat(descriptor)
    assert report['command_events'][0]['outcome'] == 'unexpected_failure'


def test_regular_json_output_is_not_given_terminal_formatting(tmp_path):
    import sys, json
    report = {'command_events': []}
    result = verifier['run_command']([sys.executable, '-c',
        "import json,sys; print(json.dumps({'tty':sys.stdout.isatty()}))"],
        output=tmp_path, stage='regular_json', report=report, created=True)
    assert json.loads(result) == {'tty': False}
    assert 'output_transport' not in report['command_events'][0]


def test_terminal_capture_failure_cannot_return_command_success(tmp_path, monkeypatch):
    import sys, errno
    masters = []
    openpty = verifier['pty'].openpty
    read = verifier['os'].read
    def opened():
        pair = openpty(); masters.append(pair[0]); return pair
    def unavailable(descriptor, size):
        if descriptor in masters: raise OSError(errno.EBADF, 'synthetic capture refusal')
        return read(descriptor, size)
    monkeypatch.setattr(verifier['pty'], 'openpty', opened)
    monkeypatch.setattr(verifier['os'], 'read', unavailable)
    report = {'command_events': []}
    with pytest.raises(ValueError, match='capture unavailable'):
        verifier['run_command']([sys.executable, '-c', 'import time; time.sleep(20)'],
            output=tmp_path, stage='capture_refusal', report=report, created=True,
            terminal_output=True)
    event = report['command_events'][0]
    assert event['outcome'] == 'capture_failure'
    assert event['returncode'] < 0


def test_only_numeric_documented_host_capacity_is_accepted():
    assert verifier['host_capacity']('8589934592\n8\n', 6000000000) == {
        'memory_bytes': 8589934592, 'logical_cpus': 8, 'disk_free_bytes': 6000000000}


@pytest.mark.parametrize('raw', ['', '8', '8 2 extra', '0 2', '8 0', '-1 2',
                                 '8 2.0', 'memory=8 cpu=2', '８ ２'])
def test_missing_or_malformed_host_capacity_cannot_be_reported_as_numeric(raw):
    with pytest.raises(ValueError, match='capacity unavailable'):
        verifier['host_capacity'](raw, 6000000000)
