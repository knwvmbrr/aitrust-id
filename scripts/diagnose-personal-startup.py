#!/usr/bin/env python3
"""Capture bounded, token-redacted diagnostics for one disposable CI redactor."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.aitrust import read_token
from scripts.worker_process import WorkerOutputLimit, run_worker
from protocol.reports import write_report

CONTAINER = 'aitrust-staging-anonymizer-1'
PROJECT = 'aitrust-staging'
TIMEOUT = 10
OUTPUT_LIMIT = 65_536
EXEC = 'import os,sys;os.dup2(1,2);os.execvp(sys.argv[1],sys.argv[1:])'
INSPECT = (
    '{"id":{{json .Id}},"name":{{json .Name}},'
    '"project":{{json (index .Config.Labels "com.docker.compose.project")}},'
    '"service":{{json (index .Config.Labels "com.docker.compose.service")}},'
    '"state":{{json .State}},"restart_count":{{json .RestartCount}},'
    '"healthcheck":{{json .Config.Healthcheck}},'
    '"resources":{"memory":{{json .HostConfig.Memory}},'
    '"pids_limit":{{json .HostConfig.PidsLimit}},"read_only":{{json .HostConfig.ReadonlyRootfs}},'
    '"security_opt":{{json .HostConfig.SecurityOpt}},"user":{{json .Config.User}}}}'
)


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate diagnostic field')
        result[key] = value
    return result


def parse(raw):
    return json.loads(raw, object_pairs_hook=unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Invalid diagnostic number')))


def owned_snapshot(raw):
    row = parse(raw)
    if (type(row) is not dict or set(row) != {
            'id', 'name', 'project', 'service', 'state', 'restart_count', 'healthcheck', 'resources'}
            or row['name'] != '/' + CONTAINER or row['project'] != PROJECT or row['service'] != 'anonymizer'
            or type(row['id']) is not str or not re.fullmatch('[a-f0-9]{64}', row['id'])
            or type(row['restart_count']) is not int or row['restart_count'] < 0
            or type(row['state']) is not dict or type(row['resources']) is not dict
            or row['healthcheck'] is not None and type(row['healthcheck']) is not dict):
        raise ValueError('Diagnostic ownership or shape refused')
    state_keys = {'Status', 'Running', 'Paused', 'Restarting', 'OOMKilled', 'Dead',
                  'Pid', 'ExitCode', 'Error', 'StartedAt', 'FinishedAt', 'Health'}
    state = row['state']
    resources = row['resources']
    if (not set(state) <= state_keys or type(state.get('Status')) is not str
            or any(type(state.get(k)) is not bool for k in ('Running', 'OOMKilled'))
            or type(state.get('ExitCode')) is not int
            or set(resources) != {'memory', 'pids_limit', 'read_only', 'security_opt', 'user'}
            or type(resources['memory']) is not int or resources['memory'] < 0
            or type(resources['pids_limit']) is not int or resources['pids_limit'] < 0
            or type(resources['read_only']) is not bool
            or type(resources['user']) is not str
            or type(resources['security_opt']) is not list
            or any(type(value) is not str for value in resources['security_opt'])):
        raise ValueError('Diagnostic state or resource shape refused')
    health = state.get('Health')
    if health is not None:
        if (type(health) is not dict or not set(health) <= {'Status', 'FailingStreak', 'Log'}
                or health.get('Status') not in ('starting', 'healthy', 'unhealthy')
                or type(health.get('FailingStreak')) is not int
                or health.get('Log') is not None and (
                    type(health['Log']) is not list or len(health['Log']) > 5)):
            raise ValueError('Diagnostic health shape refused')
        for entry in health.get('Log') or []:
            if (type(entry) is not dict or set(entry) != {'Start', 'End', 'ExitCode', 'Output'}
                    or type(entry['ExitCode']) is not int
                    or any(type(entry[key]) is not str for key in ('Start', 'End', 'Output'))):
                raise ValueError('Diagnostic probe shape refused')
    check = row['healthcheck']
    if check is not None:
        if (not set(check) <= {'Test', 'Interval', 'Timeout', 'Retries', 'StartPeriod', 'StartInterval'}
                or type(check.get('Test')) is not list or not check['Test']
                or any(type(item) is not str for item in check['Test'])
                or any(type(value) is not int or value < 0 for key, value in check.items() if key != 'Test')):
            raise ValueError('Diagnostic health configuration refused')
    return row


def collect(env_file):
    record = {'kind': 'personal_pipeline_startup_diagnostic',
              'captured_at': datetime.now(timezone.utc).isoformat(),
              'collection_state': 'UNAVAILABLE', 'service_health_accepted': False,
              'command_timeout_seconds': TIMEOUT, 'command_output_limit_bytes': OUTPUT_LIMIT,
              'container': CONTAINER, 'commands': {}, 'token_redacted': False}
    try:
        token = read_token(env_file)
    except Exception:
        record['reason'] = 'private_token_unavailable'
        return record
    record['token_redacted'] = True

    def capture(name, argv):
        try:
            child = run_worker([sys.executable, '-I', '-S', '-B', '-c', EXEC, *argv],
                               input=b'', timeout=TIMEOUT, output_limit=OUTPUT_LIMIT)
            raw = child.stdout.decode('utf-8', 'strict').replace(token, '[REDACTED]')
            if child.returncode:
                record['commands'][name] = {'state': 'UNAVAILABLE', 'returncode': child.returncode}
                return None
            record['commands'][name] = {'state': 'CAPTURED'}
            return raw
        except Exception as error:
            reason = ('deadline' if isinstance(error, subprocess.TimeoutExpired) else
                      'output_limit' if isinstance(error, WorkerOutputLimit) else 'capture_refused')
            record['commands'][name] = {'state': 'UNAVAILABLE', 'reason': reason}
            return None

    raw = capture('inspect', ['docker', 'inspect', '--format', INSPECT, CONTAINER])
    try:
        snapshot = owned_snapshot(raw) if raw is not None else None
        if snapshot is None:
            raise ValueError('No snapshot')
    except Exception:
        record['reason'] = 'owned_snapshot_unavailable'
        record['commands']['inspect'] = {'state': 'UNAVAILABLE'}
        return record
    record['snapshot'] = snapshot
    for name, argv in (
        ('docker_version', ['docker', 'version', '--format', '{{.Server.Version}}']),
        ('compose_version', ['docker', 'compose', 'version', '--short']),
        ('startup_logs', ['docker', 'logs', '--timestamps', '--tail', '100', snapshot['id']]),
    ):
        value = capture(name, argv)
        if value is None:
            continue
        if name != 'startup_logs' and not re.fullmatch(r'v?[0-9][A-Za-z0-9.+_-]{0,63}\n?', value):
            record['commands'][name] = {'state': 'UNAVAILABLE'}
            continue
        record[name] = value
    record['collection_state'] = ('COMPLETE' if all(row['state'] == 'CAPTURED'
                                   for row in record['commands'].values()) else 'PARTIAL')
    return record


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file', type=Path, required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args(argv)
    try:
        write_report(args.output, collect(args.env_file))
        print('Startup diagnostic recorded. Service health remains unaccepted.')
        return 0
    except Exception:
        print('Startup diagnostic unavailable.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
