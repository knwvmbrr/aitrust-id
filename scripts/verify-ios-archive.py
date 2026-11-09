#!/usr/bin/env python3
"""Build an unsigned registered-ID device archive; never provision or upload it."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import plistlib
import runpy
import shutil
import signal
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.blind_review_io import create, PacketError


def inspect(archive, payload):
    """Compare actual bundle contents, rather than trusting xcodebuild's exit."""
    app = archive / 'Products/Applications/AITrustID.app'
    hashes = {}
    for bundle, identifier in [(app, 'com.aitrustid.app'),
                               (app / 'PlugIns/AITrustIDShare.appex', 'com.aitrustid.app.share')]:
        if bundle.is_symlink() or not bundle.is_dir():
            raise ValueError('Expected bundle missing')
        if any(p.is_symlink() or p.name in {'embedded.mobileprovision', '_CodeSignature'}
               or p.suffix in {'.p12', '.p8', '.key'} for p in bundle.rglob('*')):
            raise ValueError('Unsigned bundle boundary violated')
        info = plistlib.loads((bundle / 'Info.plist').read_bytes())
        expected = {'CFBundleIdentifier': identifier, 'CFBundleShortVersionString': '1.0',
                    'CFBundleVersion': '1', 'CFBundleSupportedPlatforms': ['iPhoneOS'],
                    'MinimumOSVersion': '18.0'}
        if any(info.get(k) != v for k, v in expected.items()):
            raise ValueError('Device bundle identity changed')
        executable = bundle / ('AITrustID' if bundle == app else 'AITrustIDShare')
        if not executable.is_file() or executable.stat().st_size == 0:
            raise ValueError('Device executable missing')
        for name, raw in payload.items():
            if name.startswith(('Assets/', 'Notices/')) or name in {'Privacy.txt', 'AppLicense.txt'}:
                actual = bundle / name
                if not actual.is_file() or actual.read_bytes() != raw:
                    raise ValueError('Bundled resource differs')
                hashes[bundle.name + '/' + name] = hashlib.sha256(raw).hexdigest()
    info = plistlib.loads((app / 'Info.plist').read_bytes())
    icon = info.get('CFBundleIcons', {}).get('CFBundlePrimaryIcon', {})
    if icon.get('CFBundleIconName') != 'AppIcon' or not (app / 'Assets.car').is_file():
        raise ValueError('Compiled icon missing')
    if set(info.get('UISupportedInterfaceOrientations', [])) != {
            'UIInterfaceOrientationPortrait', 'UIInterfaceOrientationPortraitUpsideDown',
            'UIInterfaceOrientationLandscapeLeft', 'UIInterfaceOrientationLandscapeRight'}:
        raise ValueError('Declared device orientations missing')
    return hashes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    report = {'pass': False, 'kind': 'unsigned_ios_distribution_archive',
              'signing_configured': False, 'signed_upload': False,
              'physical_device_acceptance': False, 'independent_accuracy_evidence': False,
              'requirements_closed': []}
    created = False
    process = None
    try:
        module = runpy.run_path(str(ROOT / 'scripts/verify-ios-share.py'))
        output = module['destination'](args.output)
        if sys.platform != 'darwin' or shutil.disk_usage(output.parent).free < 5_000_000_000:
            raise ValueError('macOS SDK and build capacity required')
        before = module['source_hashes']()
        before['scripts/verify-ios-archive.py'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        payload = runpy.run_path(str(ROOT / 'scripts/build-ios-project.py'))['files']('distribution')
        create(output, ROOT, {'context.json': b'{"profile":"distribution","signing":false}\n'})
        created = True
        project = output / 'project'; project.mkdir(mode=0o700)
        for name, raw in payload.items():
            if Path(name).is_absolute() or '..' in Path(name).parts:
                raise ValueError('Unsafe generated path')
            target = project / name
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            target.write_bytes(raw)
        archive = output / 'AITrustID.xcarchive'
        with (output / 'archive.log').open('wb') as log:
            process = subprocess.Popen(['xcodebuild', '-project', str(project / 'AITrustID.xcodeproj'),
                '-scheme', 'AITrustID', '-configuration', 'Release', '-sdk', 'iphoneos',
                '-destination', 'generic/platform=iOS', '-derivedDataPath', str(output / 'derived'),
                '-archivePath', str(archive), 'archive', 'CODE_SIGNING_ALLOWED=NO'],
                cwd=ROOT, stdout=log, stderr=log, start_new_session=True)
            if process.wait(timeout=600) != 0:
                raise ValueError('Device archive failed')
        hashes = inspect(archive, payload)
        app = archive / 'Products/Applications/AITrustID.app'
        for bundle in [app, app / 'PlugIns/AITrustIDShare.appex']:
            signature = subprocess.run(['codesign', '--display', str(bundle)], capture_output=True, timeout=20)
            if signature.returncode != 1 or b'code object is not signed at all' not in signature.stderr:
                raise ValueError('Archive must be unsigned')
        after = module['source_hashes']()
        after['scripts/verify-ios-archive.py'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        if before != after:
            raise ValueError('Sources changed during archive execution')
        report.update({'pass': True, 'sources': before, 'source_unchanged_during_execution': True,
                       'bundle_identifiers': ['com.aitrustid.app', 'com.aitrustid.app.share'],
                       'app_version': '1.0', 'build': '1', 'app_icon_compiled': True,
                       'executables_unsigned': True,
                       'bundled_resource_hashes': hashes,
                       'limits': ['Unsigned device compilation is not signing, upload, TestFlight or phone acceptance.',
                                  'Privacy/platform/transitive dependency review and independent tag gates remain open.']})
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError, PacketError):
        print('Unsigned archive verification failed; inspect the private archive log.', file=sys.stderr)
    finally:
        if process is not None and process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGTERM)
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL); process.wait()
            except ProcessLookupError:
                pass
        report['captured_at'] = datetime.now(timezone.utc).isoformat()
        if created:
            with (output / 'proof.json').open('x') as stream:
                json.dump(report, stream, indent=2); stream.write('\n')
        print(json.dumps({k: report[k] for k in ['pass', 'signing_configured', 'signed_upload']}))
    return 0 if report['pass'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
