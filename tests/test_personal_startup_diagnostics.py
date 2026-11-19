"""Fixture diagnostics never start Docker or accept a failed service."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('personal_startup', ROOT/'scripts/diagnose-personal-startup.py')
diagnostic = importlib.util.module_from_spec(spec)
spec.loader.exec_module(diagnostic)
TOKEN = 'SYNTHETIC_PRIVATE_TOKEN_19_873265'
CONTAINER_ID = 'a'*64


def snapshot():
    return {'id': CONTAINER_ID, 'name': '/' + diagnostic.CONTAINER,
        'project': diagnostic.PROJECT, 'service': 'anonymizer',
        'state': {'Status': 'restarting', 'Running': True, 'OOMKilled': True,
                  'ExitCode': 137, 'Error': TOKEN, 'Health': {
                      'Status': 'unhealthy', 'FailingStreak': 1, 'Log': [
                          {'Start': 'synthetic', 'End': 'synthetic', 'ExitCode': 1, 'Output': TOKEN}]}},
        'restart_count': 2,
        'healthcheck': {'Test': ['CMD', 'python', 'healthcheck.py'], 'Interval': 30000000000,
                        'Timeout': 3000000000, 'Retries': 6, 'StartPeriod': 20000000000,
                        'StartInterval': 2000000000},
        'resources': {'memory': 1073741824, 'pids_limit': 128, 'read_only': True,
                      'security_opt': ['no-new-privileges:true'], 'user': '10001:10001'}}


@pytest.fixture
def engine(monkeypatch):
    calls = []
    responses = {
        'inspect': json.dumps(snapshot()).encode(),
        'version': b'29.4.2\n',
        'compose': b'5.1.3\n',
        'logs': ('Startup error with synthetic token '+TOKEN+'\n').encode(),
    }
    monkeypatch.setattr(diagnostic, 'read_token', lambda path: TOKEN)

    def run(argv, *, input, timeout, output_limit):
        assert argv[:6] == [sys.executable, '-I', '-S', '-B', '-c', diagnostic.EXEC]
        assert input == b'' and timeout == 10 and output_limit == 65536
        command = argv[6:]
        assert command[0] == 'docker'
        calls.append(command)
        output = responses[command[1]]
        if isinstance(output, Exception):
            raise output
        if isinstance(output, subprocess.CompletedProcess):
            return output
        return subprocess.CompletedProcess(command, 0, output, b'')

    monkeypatch.setattr(diagnostic, 'run_worker', run)
    return responses, calls


def test_successful_collection_retains_failures_and_redacts_before_output(engine):
    _, calls = engine
    row = diagnostic.collect(Path('private-placeholder'))
    assert row['collection_state'] == 'COMPLETE' and row['service_health_accepted'] is False
    assert row['snapshot']['state']['ExitCode'] == 137 and row['snapshot']['state']['OOMKilled'] is True
    assert TOKEN not in json.dumps(row) and row['token_redacted'] is True
    assert row['snapshot']['state']['Error'] == '[REDACTED]'
    assert row['snapshot']['state']['Health']['Log'][0]['Output'] == '[REDACTED]'
    assert calls == [
        ['docker', 'inspect', '--format', diagnostic.INSPECT, diagnostic.CONTAINER],
        ['docker', 'version', '--format', '{{.Server.Version}}'],
        ['docker', 'compose', 'version', '--short'],
        ['docker', 'logs', '--timestamps', '--tail', '100', CONTAINER_ID]]
    assert '.Config.Env' not in diagnostic.INSPECT
    assert 'private-placeholder' not in json.dumps(row)


def test_missing_private_token_refuses_all_docker_capture(engine, monkeypatch):
    _, calls = engine
    def unavailable(path):
        raise OSError(TOKEN)
    monkeypatch.setattr(diagnostic, 'read_token', unavailable)
    row = diagnostic.collect(Path('private-placeholder'))
    assert row['collection_state'] == 'UNAVAILABLE' and not row['token_redacted']
    assert row['reason'] == 'private_token_unavailable' and calls == []
    assert TOKEN not in json.dumps(row)


def test_snapshot_before_first_probe_preserves_empty_health_history(engine):
    responses, _ = engine
    row = snapshot()
    row['state']['Health'] = {'Status': 'starting', 'FailingStreak': 0, 'Log': None}
    responses['inspect'] = json.dumps(row).encode()
    observed = diagnostic.collect(Path('private-placeholder'))
    assert observed['collection_state'] == 'COMPLETE'
    assert observed['snapshot']['state']['Health']['Log'] is None
    assert observed['service_health_accepted'] is False


@pytest.mark.parametrize('field,value', [
    ('project', 'foreign-project'), ('service', 'gateway'), ('name', '/foreign-container'),
    ('id', 'invalid-id'), ('state', []), ('restart_count', True),
    ('healthcheck', {'Test': 'not-a-command'}), ('resources', {}),
])
def test_unverified_container_snapshot_is_never_exported_or_used_for_logs(engine, field, value):
    responses, calls = engine
    row = snapshot()
    row[field] = value
    responses['inspect'] = json.dumps(row).encode()
    observed = diagnostic.collect(Path('private-placeholder'))
    assert observed['collection_state'] == 'UNAVAILABLE'
    assert 'snapshot' not in observed and 'startup_logs' not in observed
    assert len(calls) == 1 and TOKEN not in json.dumps(observed)


@pytest.mark.parametrize('value', [
    b'not-json', b'{"id":"a","id":"b"}', b'{"id":NaN}', b'\xff',
    subprocess.CompletedProcess([], 1, TOKEN.encode(), b''),
    subprocess.TimeoutExpired(['synthetic'], 10),
    RuntimeError(TOKEN),
])
def test_failed_or_malformed_inspection_remains_unavailable(engine, value):
    responses, _ = engine
    responses['inspect'] = value
    row = diagnostic.collect(Path('private-placeholder'))
    assert row['collection_state'] == 'UNAVAILABLE' and row['service_health_accepted'] is False
    assert row['commands']['inspect']['state'] == 'UNAVAILABLE'
    assert TOKEN not in json.dumps(row)


@pytest.mark.parametrize('operation,value', [
    ('logs', subprocess.TimeoutExpired(['synthetic'], 10)),
    ('logs', RuntimeError('synthetic output excess')),
    ('version', b'not a version with '+TOKEN.encode()),
    ('compose', subprocess.CompletedProcess([], 1, TOKEN.encode(), b'')),
])
def test_unavailable_optional_capture_keeps_state_and_does_not_claim_health(engine, operation, value):
    responses, _ = engine
    responses[operation] = value
    row = diagnostic.collect(Path('private-placeholder'))
    assert row['collection_state'] == 'PARTIAL'
    assert row['service_health_accepted'] is False and 'snapshot' in row
    assert TOKEN not in json.dumps(row)


def test_real_wrapper_captures_stderr_and_supervisor_enforces_limits():
    def invoke(program, *, timeout=2, output_limit=1024):
        return diagnostic.run_worker([sys.executable, '-I', '-S', '-B', '-c', diagnostic.EXEC,
            sys.executable, '-I', '-S', '-B', '-c', program],
            input=b'', timeout=timeout, output_limit=output_limit)
    completed = invoke('import sys;sys.stdout.write("out");sys.stderr.write("err")')
    assert completed.returncode == 0 and sorted(completed.stdout.decode()) == sorted('outerr')
    with pytest.raises(subprocess.TimeoutExpired):
        invoke('import time;time.sleep(2)', timeout=.1)
    with pytest.raises(RuntimeError):
        invoke('import sys;sys.stderr.write("x"*2048)', output_limit=1024)


def test_cli_records_diagnostic_failure_without_private_console_output(engine, monkeypatch, capsys):
    responses, _ = engine
    responses['inspect'] = b'not-json'
    reports = []
    monkeypatch.setattr(diagnostic, 'write_report', lambda path, row: reports.append(row))
    assert diagnostic.main(['--env-file', 'private-placeholder', '--output', 'output/verification/test.json']) == 0
    assert len(reports) == 1 and reports[0]['collection_state'] == 'UNAVAILABLE'
    assert reports[0]['service_health_accepted'] is False
    assert TOKEN not in capsys.readouterr().out
