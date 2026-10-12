#!/usr/bin/env python3
"""Exercise the exact bundled checker on a newly owned iPhone simulator; no physical-device credit."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import plistlib
import shutil
import tempfile
import subprocess
import sys
import time
import uuid
ROOT = Path(__file__).resolve().parents[1]
SOURCES = ['mobile/ios/Source/Assets.swift', 'mobile/ios/Web/index.html', 'mobile/ios/Web/bridge.mjs', 'mobile/ios/Tests/BundleProbe.swift', 'scripts/native_bundle.py', 'scripts/native-probe-cases.py', 'scripts/verify-ios-bundle.py', 'services/evaluator/app.py', 'protocol/normalization.py', 'protocol/unicode15-data.json']
SOURCES += ['runs/2026-10-10-normalization-version-gap.json', 'site/src/device-manifest.json'] + sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / 'eval/datasets/unsafe_code').glob('*') if p.is_file())
sys.path.insert(0, str(ROOT))
from tools.blind_review_io import create, PacketError


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--runtime', required=True, help='An already installed available iOS runtime identifier; no download is attempted')
    p.add_argument('--module-cache', type=Path, help='Optional existing development compiler cache, not product data')
    a = p.parse_args(); owned = None; created = False; stage = 'host'; report = {'pass': False, 'physical_device': False, 'independent_accuracy': False, 'captured_at': datetime.now(timezone.utc).isoformat()}
    os.umask(0o077)
    def command(args, timeout=30, cleanup=False):
        with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
            process = subprocess.Popen(args, cwd=ROOT, stdout=stdout, stderr=stderr)
            start = time.monotonic()
            try:
                while process.poll() is None:
                    if not cleanup and shutil.disk_usage(a.output.parent).free < 2_000_000_000:
                        raise ValueError('Build capacity reserve reached')
                    if time.monotonic()-start > timeout: raise subprocess.TimeoutExpired(args, timeout)
                    time.sleep(.25)
                if process.returncode: raise subprocess.CalledProcessError(process.returncode, args)
                stdout.seek(0); return stdout.read().decode().strip()
            finally:
                if process.poll() is None:
                    process.terminate()
                    try: process.wait(timeout=5)
                    except subprocess.TimeoutExpired: process.kill(); process.wait()
    try:
        if sys.platform != 'darwin': raise ValueError('macOS SDK required')
        if shutil.disk_usage(a.output.parent).free < 5_000_000_000: raise ValueError('Insufficient build capacity')
        if a.module_cache and (not a.module_cache.is_dir() or a.module_cache.is_symlink()): raise ValueError('Compiler cache unavailable')
        runtimes = json.loads(command(['xcrun', 'simctl', 'list', 'runtimes', '--json']))['runtimes']
        runtime = next((r for r in runtimes if r['identifier'] == a.runtime and r.get('isAvailable') and r['identifier'].startswith('com.apple.CoreSimulator.SimRuntime.iOS-')), None)
        if runtime is None: raise ValueError('Installed iOS runtime unavailable')
        create(a.output, ROOT, {'build-context.json': (json.dumps({'runtime': a.runtime, 'participant_inputs': False}) + '\n').encode()})
        created = True
        stage = 'public_assets'
        source_hashes = {n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest() for n in SOURCES}
        spec = importlib.util.spec_from_file_location('ios_package', ROOT / 'scripts/native_bundle.py'); builder = importlib.util.module_from_spec(spec); spec.loader.exec_module(builder)
        payload = builder.assets(); app = a.output / 'AITrustBundleProbe.app'; app.mkdir(mode=0o700)
        for name, raw in payload.items():
            if name.startswith('Assets/'):
                target = app / name; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(raw)
        (app / 'cases.json').write_text(command([sys.executable, str(ROOT / 'scripts/native-probe-cases.py')]))
        info = {'CFBundleIdentifier': 'com.aitrustid.verification.' + uuid.uuid4().hex, 'CFBundleExecutable': 'AITrustBundleProbe', 'CFBundleName': 'AITrustBundleProbe', 'CFBundlePackageType': 'APPL', 'CFBundleVersion': '1', 'CFBundleShortVersionString': '0.1', 'LSRequiresIPhoneOS': True, 'MinimumOSVersion': '18.0', 'UIDeviceFamily': [1], 'UILaunchScreen': {}}
        (app / 'Info.plist').write_bytes(plistlib.dumps(info)); stage = 'compile'
        sdk = command(['xcrun', '--sdk', 'iphonesimulator', '--show-sdk-path'])
        cache = a.module_cache or a.output / 'CompilerCache'
        args = ['xcrun', '--sdk', 'iphonesimulator', 'swiftc', '-sdk', sdk, '-swift-version', '5', '-target', 'arm64-apple-ios18.0-simulator', '-module-cache-path', str(cache), str(ROOT / 'mobile/ios/Source/Assets.swift'), str(ROOT / 'mobile/ios/Tests/BundleProbe.swift'), '-o', str(app / info['CFBundleExecutable'])]
        command(args, timeout=120)
        command(['codesign', '--force', '--sign', '-', str(app)])
        stage = 'owned_simulator'; owned = command(['xcrun', 'simctl', 'create', 'AITrust-ID-bundle-proof-' + uuid.uuid4().hex[:8], 'com.apple.CoreSimulator.SimDeviceType.iPhone-14-Plus', a.runtime])
        command(['xcrun', 'simctl', 'boot', owned]); command(['xcrun', 'simctl', 'bootstatus', owned, '-b'], timeout=180)
        stage = 'install_and_check'; command(['xcrun', 'simctl', 'install', owned, str(app)])
        command(['xcrun', 'simctl', 'launch', owned, info['CFBundleIdentifier']])
        container = Path(command(['xcrun', 'simctl', 'get_app_container', owned, info['CFBundleIdentifier'], 'data'])); proof = container / 'Documents/proof.json'
        start = time.monotonic()
        while not proof.is_file() and time.monotonic() - start < 100:
            if shutil.disk_usage(a.output.parent).free < 2_000_000_000:
                raise ValueError('Execution capacity reserve reached')
            time.sleep(.5)
        measured = json.loads(proof.read_text())
        if measured.get('pass') is not True or measured.get('case_count') != 137 or measured.get('resource_refusals') != 11 or measured.get('input_refusals') != 5 or measured.get('remote_fetch_refused') is not True or measured.get('input_not_executed') is not True: raise ValueError('Native execution failed')
        report.update(measured); report.update(runtime=runtime['name'], runtime_build=runtime['buildversion'], sdk=command(['xcrun', '--sdk', 'iphonesimulator', '--show-sdk-version']), xcode=command(['xcodebuild', '-version']), selected_fixture_scope='86 development cases plus 41 normalization and 10 Unicode-boundary cases; not independent labels', check_seconds=time.monotonic()-start)
        current_hashes = {n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest() for n in SOURCES}
        if source_hashes != current_hashes: raise ValueError('Source changed during native execution')
        report['sources'] = source_hashes; report['source_unchanged_during_execution'] = True
        report['bundle_sha256'] = builder.digest(payload['Assets/method.py']); report['asset_fingerprints'] = json.loads(payload['Assets/native-assets.json'])['hashes']; report['pass'] = True
    except (ValueError, OSError, KeyError, TypeError, StopIteration, subprocess.SubprocessError, PacketError) as exc:
        report.update({'pass': False, 'failed_stage': stage, 'failure_type': type(exc).__name__})
        print('Native verification unavailable; inspect the private proof and SDK/build prerequisites.', file=sys.stderr)
    finally:
        if owned:
            cleanup = []
            for action in ['shutdown', 'delete']:
                try: command(['xcrun', 'simctl', action, owned], cleanup=True); cleanup.append(action)
                except (OSError, subprocess.SubprocessError): pass
            report['owned_simulator_removed'] = cleanup == ['shutdown', 'delete']
            if cleanup != ['shutdown', 'delete']: report['pass'] = False
        if created:
            target = a.output / 'proof.json'
            with target.open('x') as f: json.dump(report, f, indent=2); f.write('\n')
        print(json.dumps({'pass': report['pass'], 'physical_device': False, 'independent_accuracy': False, 'case_count': report.get('case_count', 0)}))
    return 0 if report['pass'] else 2
if __name__ == '__main__': raise SystemExit(main())
