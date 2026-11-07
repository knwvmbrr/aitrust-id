#!/usr/bin/env python3
"""Build and exercise the unreleased Share workflow on an owned simulator only."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import runpy
import shutil
import signal
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.blind_review_io import create, PacketError

SOURCES = ['scripts/verify-ios-share.py', 'scripts/build-ios-project.py',
           'scripts/native_bundle.py', 'scripts/asset_notices.py',
           'mobile/ios/Tests/UIFlows.swift', 'mobile/ios/Web/bridge.mjs',
           'mobile/ios/Web/index.html', 'services/evaluator/app.py',
           'protocol/normalization.py', 'protocol/unicode15-data.json']
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--runtime', required=True, help='Already installed available iOS runtime; no download')
    args = parser.parse_args()
    os.umask(0o077)
    owned = None
    created = False
    stage = 'prerequisites'
    report = {'pass': False, 'physical_device': False, 'independent_accuracy': False,
              'human_accessibility': False, 'installable_phone_release': False,
              'started_at': datetime.now(timezone.utc).isoformat()}
    output = args.output

    def command(argv, timeout=30, cleanup=False):
        with tempfile_log() as log:
            process = subprocess.Popen(argv, cwd=ROOT, stdout=log, stderr=log, start_new_session=True)
            try:
                until = time.monotonic() + timeout
                while process.poll() is None:
                    if time.monotonic() > until:
                        raise ValueError('Verification deadline reached')
                    if not cleanup and shutil.disk_usage(output.parent).free < 2_000_000_000:
                        raise ValueError('Build capacity reserve reached')
                    time.sleep(.25)
                log.seek(0)
                raw = log.read()
                if created:
                    with (output / (stage + '.log')).open('ab') as saved:
                        saved.write(raw)
                if process.returncode:
                    raise ValueError('Verification command failed')
                return raw.decode('utf-8', errors='strict').strip()
            finally:
                if process.poll() is None:
                    try: os.killpg(process.pid, signal.SIGTERM)
                    except ProcessLookupError: pass
                    try: process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        try: os.killpg(process.pid, signal.SIGKILL)
                        except ProcessLookupError: pass
                        process.wait()

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
        project = output / 'project'
        project.mkdir(mode=0o700)
        for name, raw in payload.items():
            if Path(name).is_absolute() or '..' in Path(name).parts:
                raise ValueError('Unexpected build path')
            target = project / name
            target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            target.write_bytes(raw)
        stage = 'owned_simulator'
        identity = command(['xcrun', 'simctl', 'create', 'AITrust-ID-Share-proof-' + uuid.uuid4().hex[:8],
                            'com.apple.CoreSimulator.SimDeviceType.iPhone-14-Plus', args.runtime])
        owned = simulator_identity(identity)
        command(['xcrun', 'simctl', 'boot', owned])
        command(['xcrun', 'simctl', 'bootstatus', owned, '-b'], timeout=180)
        stage = 'build_and_ui'
        command(['xcodebuild', '-project', str(project / 'AITrustID.xcodeproj'), '-scheme', 'AITrustID',
                 '-sdk', 'iphonesimulator', '-destination', 'platform=iOS Simulator,id=' + owned,
                 '-derivedDataPath', str(output / 'derived'), '-resultBundlePath', str(output / 'workflow.xcresult'),
                 '-parallel-testing-enabled', 'NO', '-test-timeouts-enabled', 'YES',
                 '-default-test-execution-time-allowance', '60', '-maximum-test-execution-time-allowance', '90',
                 'test', 'CODE_SIGNING_ALLOWED=NO', 'ONLY_ACTIVE_ARCH=YES'], timeout=600)
        stage = 'result'
        measured = json.loads(command(['xcrun', 'xcresulttool', 'get', 'test-results', 'summary',
                                      '--path', str(output / 'workflow.xcresult'), '--format', 'json']))
        if not accepted_summary(measured): raise ValueError('Native workflow acceptance failed')
        if source_hashes() != before: raise ValueError('Sources changed during execution')
        report.update({'pass': True, 'sources': before, 'source_unchanged_during_execution': True,
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
        if owned:
            stage = 'cleanup'
            clean = []
            for action in ['shutdown', 'delete']:
                try: command(['xcrun', 'simctl', action, owned], cleanup=True); clean.append(action)
                except (ValueError, OSError, subprocess.SubprocessError): pass
            report['owned_simulator_removed'] = clean == ['shutdown', 'delete']
            if not report['owned_simulator_removed']: report['pass'] = False
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
