#!/usr/bin/env python3
"""Build and exercise the unreleased Share workflow on an owned simulator only."""
import argparse
from datetime import datetime, timezone
import errno
import hashlib
import json
import os
from pathlib import Path
import pty
import runpy
import select
import shutil
import signal
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.blind_review_io import create, PacketError

SOURCES = ['scripts/verify-ios-share.py', 'scripts/build-ios-project.py', 'scripts/build-device-detector.py',
           'scripts/native_bundle.py', 'scripts/asset_notices.py',
           'mobile/ios/Tests/UIFlows.swift', 'mobile/ios/Web/bridge.mjs',
           'mobile/ios/Web/index.html', 'services/evaluator/app.py',
           'protocol/normalization.py', 'protocol/unicode15-data.json']
SOURCES += ['mobile/ios/Privacy.txt', 'mobile/ios/PrivacyInfo.xcprivacy',
            'mobile/ios/Artwork/AppIcon.svg', 'mobile/ios/Artwork/AppIcon.png']
SOURCES += ['mobile/ios/Source/' + name for name in
            ['App.swift', 'Assets.swift', 'CheckerController.swift', 'ShareController.swift', 'SharedText.swift']]


def source_hashes():
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in SOURCES}


def destination(path):
    path = path.expanduser().absolute()
    if path.is_symlink() or path.exists():
        raise ValueError('Use a new private output folder')
    for parent in (path.parent.resolve(), *path.parent.resolve().parents):
        if (parent / '.git').exists():
            raise ValueError('Keep verification output outside every Git checkout')
    return path


def accepted_summary(summary):
    return (isinstance(summary, dict)
            and all(type(summary.get(key)) is int for key in ['totalTestCount', 'passedTests', 'failedTests'])
            and type(summary.get('skippedTests', 0)) is int
            and summary.get('result') == 'Passed' and summary.get('totalTestCount') == 5
            and summary.get('passedTests') == 5 and summary.get('failedTests') == 0
            and summary.get('skippedTests', 0) == 0 and not summary.get('testFailures'))


def simulator_identity(value):
    parsed = uuid.UUID(value)
    if value.lower() != str(parsed):
        raise ValueError('Unexpected simulator identity')
    # Xcode destination matching is case-sensitive even though simctl's is not.
    return value


def host_capacity(raw, free_bytes):
    values = raw.split()
    if len(values) != 2 or not all(value.isascii() and value.isdecimal() and int(value) > 0
                                   for value in values):
        raise ValueError('Numeric host memory and CPU capacity unavailable')
    return {'memory_bytes': int(values[0]), 'logical_cpus': int(values[1]),
            'disk_free_bytes': free_bytes}


def run_command(argv, *, output, stage, report, created, timeout=30, cleanup=False,
                terminal_output=False):
    event = {'stage': stage, 'tool': Path(argv[0]).name,
             'operation': argv[1:3], 'timeout_seconds': timeout, 'cleanup': cleanup,
             'started_at': datetime.now(timezone.utc).isoformat(), 'outcome': 'unexpected_failure'}
    report['command_events'].append(event)
    with tempfile_log() as log:
        process = None
        master = slave = None

        def drain_terminal():
            if master is None: return
            # Bound each drain so a noisy child cannot postpone its deadline.
            for _ in range(16):
                try: chunk = os.read(master, 65536)
                except BlockingIOError: return
                except OSError as error:
                    if error.errno != errno.EIO: event['capture_error'] = error.errno
                    return
                if not chunk: return
                log.write(chunk)

        try:
            if terminal_output:
                master, slave = pty.openpty()
                os.set_blocking(master, False)
                event['output_transport'] = 'pty'
            process = subprocess.Popen(argv, cwd=ROOT,
                stdout=slave if terminal_output else log,
                stderr=slave if terminal_output else log, start_new_session=True)
            # Keep the parent's slave open until the final drain. On macOS the
            # last slave close can discard queued output before we can read it.
            until = time.monotonic() + timeout
            while process.poll() is None:
                drain_terminal()
                if event.get('capture_error') is not None:
                    event['outcome'] = 'capture_failure'
                    raise ValueError('Terminal output capture unavailable')
                if time.monotonic() > until:
                    event['outcome'] = 'deadline'
                    raise ValueError('Verification deadline reached')
                if not cleanup and shutil.disk_usage(output.parent).free < 2_000_000_000:
                    event['outcome'] = 'capacity_reserve'
                    raise ValueError('Build capacity reserve reached')
                if master is None: time.sleep(.25)
                else: select.select([master], [], [], .25)
            drain_terminal()
            log.seek(0)
            raw = log.read()
            event['returncode'] = process.returncode
            if process.returncode:
                event['outcome'] = 'nonzero_exit'
                raise ValueError('Verification command failed')
            decoded = raw.decode('utf-8', errors='strict').strip()
            event['outcome'] = 'passed'
            return decoded
        finally:
            drain_terminal()
            if process is not None and process.poll() is None:
                try: os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError: pass
                try: process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    try: os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError: pass
                    process.wait()
            drain_terminal()
            for descriptor in (slave, master):
                if descriptor is not None: os.close(descriptor)
            event['finished_at'] = datetime.now(timezone.utc).isoformat()
            if process is not None: event['returncode'] = process.returncode
            log.seek(0)
            retained = log.read()
            event['output_bytes'] = len(retained)
            event['output_sha256'] = hashlib.sha256(retained).hexdigest()
            # Keep diagnostics even when the deadline, not the tool, fails.
            if created:
                with (output / (stage + '.log')).open('ab') as saved:
                    saved.write(retained)
            if event.get('capture_error') is not None and event['outcome'] == 'passed':
                event['outcome'] = 'capture_failure'
                raise ValueError('Terminal output capture unavailable')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--runtime', required=True, help='Already installed available iOS runtime; no download')
    args = parser.parse_args()
    os.umask(0o077)
    owned = None
    cleanup_attempted = False
    created = False
    stage = 'prerequisites'
    report = {'pass': False, 'physical_device': False, 'independent_accuracy': False,
              'human_accessibility': False, 'installable_phone_release': False,
              'started_at': datetime.now(timezone.utc).isoformat(), 'command_events': []}
    output = args.output

    def command(argv, timeout=30, cleanup=False, terminal_output=False):
        return run_command(argv, output=output, stage=stage, report=report,
                           created=created, timeout=timeout, cleanup=cleanup,
                           terminal_output=terminal_output)

    def cleanup_owned():
        nonlocal stage, cleanup_attempted
        if owned is None: return True
        if cleanup_attempted: return report['owned_simulator_removed']
        cleanup_attempted = True
        report['owned_simulator_removed'] = False
        previous_stage = stage
        stage = 'cleanup'
        clean = []
        try:
            for action in ['shutdown', 'delete']:
                try:
                    command(['xcrun', 'simctl', action, owned], timeout=90, cleanup=True)
                    clean.append(action)
                except (ValueError, OSError, subprocess.SubprocessError): pass
            report['owned_simulator_removed'] = clean == ['shutdown', 'delete']
            if not report['owned_simulator_removed']: report['pass'] = False
            return report['owned_simulator_removed']
        finally:
            stage = previous_stage

    try:
        output = destination(output)
        if sys.platform != 'darwin' or shutil.disk_usage(output.parent).free < 5_000_000_000:
            raise ValueError('macOS SDK and build capacity required')
        runtimes = json.loads(command(['xcrun', 'simctl', 'list', 'runtimes', '--json']))['runtimes']
        runtime = next((r for r in runtimes if r['identifier'] == args.runtime
                        and r.get('isAvailable') and r['identifier'].startswith('com.apple.CoreSimulator.SimRuntime.iOS-')), None)
        if runtime is None: raise ValueError('Installed iOS runtime required')
        before = source_hashes()
        builder = runpy.run_path(str(ROOT / 'scripts/build-ios-project.py'))
        payload = builder['files']()
        create(output, ROOT, {'context.json': b'{"invented_examples_only":true}\n'})
        created = True
        report.update({'attempted_sources': before, 'runtime': runtime['name'],
                       'runtime_build': runtime['buildversion'],
                       'xcode': command(['xcodebuild', '-version']),
                       'sdk': command(['xcrun', '--sdk', 'iphonesimulator', '--show-sdk-version'])})
        project = output / 'project'
        project.mkdir(mode=0o700)
        for name, raw in payload.items():
            if Path(name).is_absolute() or '..' in Path(name).parts:
                raise ValueError('Unexpected build path')
            target = project / name
            target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            target.write_bytes(raw)
        stage = 'host_capacity'
        free_bytes = shutil.disk_usage(output.parent).free
        report['host_capacity'] = {'disk_free_bytes': free_bytes, 'memory_cpu_query': 'unavailable'}
        # sysctl(8) documents these read-only numeric keys. Never use -a, a
        # hostname query, environment inventory or a whole-system diagnostic.
        if Path('/usr/sbin/sysctl').is_file():
            report['host_capacity'] = host_capacity(command(
                ['/usr/sbin/sysctl', '-n', 'hw.memsize', 'hw.logicalcpu'], timeout=5), free_bytes)
        stage = 'owned_simulator'
        identity = command(['xcrun', 'simctl', 'create', 'AITrust-ID-Share-proof-' + uuid.uuid4().hex[:8],
                            'com.apple.CoreSimulator.SimDeviceType.iPhone-14-Plus', args.runtime])
        owned = simulator_identity(identity)
        command(['xcrun', 'simctl', 'boot', owned])
        # Native bootstatus output is buffered when redirected to a file. A PTY
        # retains live phase/migration progress if this existing deadline fires.
        command(['xcrun', 'simctl', 'bootstatus', owned, '-b', '-d'], timeout=180,
                terminal_output=True)
        build = ['xcodebuild', '-project', str(project / 'AITrustID.xcodeproj'), '-scheme', 'AITrustID',
                 '-sdk', 'iphonesimulator', '-destination', 'platform=iOS Simulator,id=' + owned,
                 '-derivedDataPath', str(output / 'derived'), '-parallel-testing-enabled', 'NO']
        stage = 'build'
        command([*build, 'build-for-testing', 'CODE_SIGNING_ALLOWED=NO', 'ONLY_ACTIVE_ARCH=YES'], timeout=600)
        stage = 'ui_workflows'
        try:
            command([*build, '-resultBundlePath', str(output / 'workflow.xcresult'), '-test-timeouts-enabled', 'YES',
                     '-default-test-execution-time-allowance', '120', '-maximum-test-execution-time-allowance', '150',
                     'test-without-building', 'CODE_SIGNING_ALLOWED=NO', 'ONLY_ACTIVE_ARCH=YES'], timeout=600)
        finally:
            # Keep this boundary even if UI or later result parsing fails.
            report['post_ui_source_unchanged'] = False
            try:
                report['post_ui_sources'] = source_hashes()
                report['post_ui_source_unchanged'] = report['post_ui_sources'] == before
            except OSError:
                report['post_ui_sources_unavailable'] = True
        # The completed result bundle is on disk outside this simulator. Reclaim
        # the owned guest before parsing it; do not retry a failed cleanup.
        stage = 'cleanup'
        if not cleanup_owned(): raise ValueError('Owned simulator cleanup failed')
        stage = 'source_integrity'
        if not report['post_ui_source_unchanged']:
            raise ValueError('Sources changed or unavailable after UI execution')
        stage = 'result'
        measured = json.loads(command(['xcrun', 'xcresulttool', 'get', 'test-results', 'summary',
                                      '--path', str(output / 'workflow.xcresult'), '--format', 'json']))
        if not accepted_summary(measured): raise ValueError('Native workflow acceptance failed')
        report.update({'pass': True, 'sources': before,
                       'test_count': 5, 'runtime': runtime['name'], 'runtime_build': runtime['buildversion'],
                       'xcode': command(['xcodebuild', '-version']),
                       'sdk': command(['xcrun', '--sdk', 'iphonesimulator', '--show-sdk-version']),
                       'method_sha256': json.loads(payload['Assets/device-manifest.json'])['method_sha256'],
                       'asset_fingerprints': json.loads(payload['Assets/native-assets.json'])['hashes'],
                       'profile': 'invented-text/UIActivityViewController/local-PS/simulator/v1',
                       'limits': ['Typed-provider compatibility API deprecated in iOS 27; no future SDK guarantee.',
                                  'Provider allocation and OS storage are not hard-bounded or physically erased.',
                                  'No physical phone, arbitrary third-party share source or human accessibility acceptance.']})
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError, PacketError):
        report.update(pass_=False, failed_stage=stage)
        report['pass'] = False
        report.pop('pass_', None)
        print('Native Share verification unavailable; inspect the private stage logs.', file=sys.stderr)
    finally:
        cleanup_owned()
        if 'post_ui_source_unchanged' in report:
            report['source_unchanged_during_execution'] = False
            try:
                report['final_sources'] = source_hashes()
                report['source_unchanged_during_execution'] = (
                    report['post_ui_source_unchanged'] and report['final_sources'] == before)
            except OSError:
                report['final_sources_unavailable'] = True
            if not report['source_unchanged_during_execution']:
                report['pass'] = False
                report.setdefault('failed_stage', 'source_integrity')
        report['captured_at'] = datetime.now(timezone.utc).isoformat()
        if created:
            with (output / 'proof.json').open('x') as stream:
                json.dump(report, stream, indent=2); stream.write('\n')
        print(json.dumps({k: report[k] for k in ['pass', 'physical_device', 'independent_accuracy']}))
    return 0 if report['pass'] else 2


def tempfile_log():
    import tempfile
    return tempfile.TemporaryFile()


if __name__ == '__main__':
    raise SystemExit(main())
