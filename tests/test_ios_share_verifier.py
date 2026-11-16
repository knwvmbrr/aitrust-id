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


@pytest.fixture
def lifecycle_run(tmp_path, monkeypatch):
    """Exercise main's report/cleanup lifecycle without executing native tools."""
    import json, os
    from types import SimpleNamespace
    namespace = verifier['main'].__globals__
    identity = '706597C7-9A9E-4F75-9DE8-48F211D005D4'
    runtime = 'com.apple.CoreSimulator.SimRuntime.iOS-synthetic'
    unchanged = {'synthetic-source.swift': 'a' * 64}

    def run(*, failure=None, failure_exception=None, summary=None, source_states=None):
        trace, calls = [], []
        states = source_states or [unchanged, unchanged, unchanged]
        output = tmp_path / 'proof'
        counter = 0
        def sources():
            nonlocal counter
            trace.append('hash-' + str(counter + 1))
            value = states[min(counter, len(states) - 1)]; counter += 1
            if isinstance(value, Exception): raise value
            return dict(value)
        def create_output(path, root, members):
            path.mkdir()
            for name, raw in members.items(): (path / name).write_bytes(raw)
        payload = {'Source/synthetic.swift': b'// fixed fixture\n',
                   'Assets/device-manifest.json': json.dumps({'method_sha256': 'a' * 64}).encode(),
                   'Assets/native-assets.json': b'{"hashes":{}}'}
        def command(argv, **options):
            if argv[1:3] == ['simctl', 'list']:
                name, value = 'runtimes', json.dumps({'runtimes': [{'identifier': runtime,
                    'isAvailable': True, 'name': 'Synthetic iOS', 'buildversion': 'synthetic'}]})
            elif argv[1:3] == ['simctl', 'create']: name, value = 'create', identity
            elif argv[1:3] in [['simctl', action] for action in ['boot', 'bootstatus', 'shutdown', 'delete']]:
                name, value = argv[2], ''
                assert argv[3] == identity
            elif 'build-for-testing' in argv: name, value = 'build', ''
            elif 'test-without-building' in argv: name, value = 'ui', ''
            elif argv[1:3] == ['xcresulttool', 'get']:
                name, value = 'summary', json.dumps(summary if summary is not None else {
                    'result': 'Passed', 'totalTestCount': 5, 'passedTests': 5,
                    'failedTests': 0, 'skippedTests': 0})
            elif argv[0] == '/usr/sbin/sysctl': name, value = 'capacity', '7516192768\n3\n'
            elif argv[0] == 'xcodebuild': name, value = 'xcode-version', 'Synthetic Xcode'
            elif argv[1:3] == ['--sdk', 'iphonesimulator']: name, value = 'sdk-version', 'synthetic'
            else: raise AssertionError('Unexpected external command')
            trace.append(name); calls.append({'name': name, **options})
            if name == failure:
                raise failure_exception if failure_exception is not None else ValueError('synthetic command deadline')
            return value
        monkeypatch.setattr(verifier['sys'], 'platform', 'darwin')
        monkeypatch.setattr(verifier['sys'], 'argv', ['verify-ios-share.py', '--output', str(output),
                                                     '--runtime', runtime])
        monkeypatch.setattr(verifier['shutil'], 'disk_usage', lambda _: SimpleNamespace(free=50000000000))
        monkeypatch.setattr(verifier['runpy'], 'run_path', lambda _: {'files': lambda: payload})
        for name, value in [('source_hashes', sources), ('create', create_output), ('run_command', command)]:
            monkeypatch.setitem(namespace, name, value)
        previous_umask = os.umask(0o077)
        try: status = verifier['main']()
        finally: os.umask(previous_umask)
        return status, json.loads((output / 'proof.json').read_text()), trace, calls
    return run


def test_completed_ui_is_reclaimed_before_exact_summary_and_final_identity(lifecycle_run):
    status, proof, trace, calls = lifecycle_run()
    assert status == 0 and proof['pass'] is True
    ordered = ['ui', 'hash-2', 'shutdown', 'delete', 'summary', 'hash-3']
    assert [trace.index(name) for name in ordered] == sorted(trace.index(name) for name in ordered)
    assert trace.count('shutdown') == trace.count('delete') == 1
    assert proof['post_ui_sources'] == proof['attempted_sources'] == proof['final_sources']
    assert proof['post_ui_source_unchanged'] is proof['source_unchanged_during_execution'] is True
    assert proof['owned_simulator_removed'] is True and proof['test_count'] == 5
    for name, timeout in [('ui', 600), ('summary', 30), ('shutdown', 90), ('delete', 90)]:
        call = next(call for call in calls if call['name'] == name)
        assert call['timeout'] == timeout
        assert call['cleanup'] is (name in ['shutdown', 'delete'])


def test_summary_deadline_keeps_post_ui_identity_and_original_failure(lifecycle_run):
    status, proof, trace, _ = lifecycle_run(failure='summary')
    assert status == 2 and proof['pass'] is False and proof['failed_stage'] == 'result'
    assert trace.index('delete') < trace.index('summary')
    assert trace.count('shutdown') == trace.count('delete') == 1
    assert proof['owned_simulator_removed'] is True
    assert proof['post_ui_sources'] == proof['attempted_sources'] == proof['final_sources']
    assert proof['source_unchanged_during_execution'] is True
    assert 'sources' not in proof and 'test_count' not in proof


@pytest.mark.parametrize('failed_action', ['shutdown', 'delete'])
def test_failed_early_cleanup_stops_parsing_and_is_never_retried(lifecycle_run, failed_action):
    status, proof, trace, _ = lifecycle_run(failure=failed_action)
    assert status == 2 and proof['pass'] is False and proof['failed_stage'] == 'cleanup'
    assert proof['owned_simulator_removed'] is False
    assert trace.count('shutdown') == trace.count('delete') == 1
    assert 'summary' not in trace
    assert proof['post_ui_source_unchanged'] is True


@pytest.mark.parametrize('failed_phase', ['build', 'ui'])
def test_earlier_failure_still_reclaims_owned_guest_once(lifecycle_run, failed_phase):
    status, proof, trace, _ = lifecycle_run(failure=failed_phase)
    assert status == 2 and proof['pass'] is False
    assert proof['failed_stage'] == ('build' if failed_phase == 'build' else 'ui_workflows')
    assert proof['owned_simulator_removed'] is True
    assert trace.count('shutdown') == trace.count('delete') == 1 and 'summary' not in trace
    assert ('post_ui_sources' in proof) is (failed_phase == 'ui')


def test_xcode_zero_exit_cannot_replace_exact_five_summary(lifecycle_run):
    status, proof, trace, _ = lifecycle_run(summary={'result': 'Passed', 'totalTestCount': 4,
        'passedTests': 4, 'failedTests': 0, 'skippedTests': 0})
    assert status == 2 and proof['pass'] is False and proof['failed_stage'] == 'result'
    assert trace.index('delete') < trace.index('summary')
    assert proof['owned_simulator_removed'] is True


@pytest.mark.parametrize('boundary', ['post_ui', 'final'])
def test_changed_source_cannot_be_accepted_after_cleanup(lifecycle_run, boundary):
    original = {'synthetic-source.swift': 'a' * 64}
    changed = {'synthetic-source.swift': 'b' * 64}
    states = [original, changed if boundary == 'post_ui' else original, changed]
    status, proof, trace, _ = lifecycle_run(source_states=states)
    assert status == 2 and proof['pass'] is False and proof['failed_stage'] == 'source_integrity'
    assert proof['owned_simulator_removed'] is True
    assert proof['source_unchanged_during_execution'] is False
    assert ('summary' in trace) is (boundary == 'final')


@pytest.mark.parametrize('boundary', ['post_ui', 'final'])
def test_unavailable_source_snapshot_fails_closed_without_repeating_cleanup(lifecycle_run, boundary):
    original = {'synthetic-source.swift': 'a' * 64}
    states = [original, OSError('synthetic source unavailable') if boundary == 'post_ui' else original,
              OSError('synthetic source unavailable') if boundary == 'final' else original]
    status, proof, trace, _ = lifecycle_run(source_states=states)
    assert status == 2 and proof['pass'] is False and proof['failed_stage'] == 'source_integrity'
    assert proof['source_unchanged_during_execution'] is False
    assert proof[boundary + '_sources_unavailable'] is True
    assert proof['owned_simulator_removed'] is True
    assert trace.count('shutdown') == trace.count('delete') == 1


def test_late_source_capture_failure_does_not_mask_summary_deadline(lifecycle_run):
    original = {'synthetic-source.swift': 'a' * 64}
    status, proof, trace, _ = lifecycle_run(failure='summary',
        source_states=[original, original, OSError('synthetic final source unavailable')])
    assert status == 2 and proof['pass'] is False and proof['failed_stage'] == 'result'
    assert proof['post_ui_sources'] == proof['attempted_sources']
    assert proof['final_sources_unavailable'] is True
    assert proof['source_unchanged_during_execution'] is False
    assert proof['owned_simulator_removed'] is True
    assert trace.count('shutdown') == trace.count('delete') == 1


def test_interrupted_cleanup_preserves_failure_report_and_original_interrupt(lifecycle_run, tmp_path):
    import json
    with pytest.raises(KeyboardInterrupt):
        lifecycle_run(failure='shutdown', failure_exception=KeyboardInterrupt())
    proof = json.loads((tmp_path / 'proof/proof.json').read_text())
    assert proof['pass'] is False and proof['owned_simulator_removed'] is False
    assert proof['post_ui_source_unchanged'] is True
    assert 'test_count' not in proof
