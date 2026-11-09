"""Refuse misidentified, incomplete, signed or altered native archive contents."""
import plistlib
from pathlib import Path
import runpy

import pytest

inspect = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'scripts/verify-ios-archive.py'))['inspect']


@pytest.fixture
def archive(tmp_path):
    payload = {'Assets/method.py': b'fixture method', 'Notices/license.txt': b'fixture notice',
               'Privacy.txt': b'fixture privacy', 'AppLicense.txt': b'fixture license'}
    app = tmp_path / 'Products/Applications/AITrustID.app'
    share = app / 'PlugIns/AITrustIDShare.appex'
    for bundle, identifier, executable in [(app, 'com.aitrustid.app', 'AITrustID'),
                                           (share, 'com.aitrustid.app.share', 'AITrustIDShare')]:
        bundle.mkdir(parents=True, exist_ok=True)
        info = {'CFBundleIdentifier': identifier, 'CFBundleShortVersionString': '1.0',
                'CFBundleVersion': '1', 'CFBundleSupportedPlatforms': ['iPhoneOS'], 'MinimumOSVersion': '18.0'}
        if bundle == app:
            info.update(CFBundleIcons={'CFBundlePrimaryIcon': {'CFBundleIconName': 'AppIcon'}},
                        UISupportedInterfaceOrientations=['UIInterfaceOrientationPortrait', 'UIInterfaceOrientationPortraitUpsideDown',
                                                          'UIInterfaceOrientationLandscapeLeft', 'UIInterfaceOrientationLandscapeRight'])
            (bundle / 'Assets.car').write_bytes(b'fixture compiled icon')
        (bundle / 'Info.plist').write_bytes(plistlib.dumps(info))
        (bundle / executable).write_bytes(b'fixture executable, not runtime proof')
        for name, raw in payload.items():
            target = bundle / name; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(raw)
    return tmp_path, app, share, payload


def test_exact_bundle_resources_pass_content_inspection(archive):
    root, app, share, payload = archive
    assert len(inspect(root, payload)) == 2 * len(payload)


@pytest.mark.parametrize('mutation', ['preview_identifier', 'simulator_platform', 'changed_notice', 'missing_privacy',
                                    'missing_executable', 'missing_icon', 'missing_orientation', 'profile', 'signature', 'resource_link'])
def test_archive_refuses_invalid_distribution_boundary(archive, mutation):
    root, app, share, payload = archive
    info = plistlib.loads((app / 'Info.plist').read_bytes())
    if mutation == 'preview_identifier': info['CFBundleIdentifier'] = 'com.aitrustid.personal.preview'
    elif mutation == 'simulator_platform': info['CFBundleSupportedPlatforms'] = ['iPhoneSimulator']
    elif mutation == 'missing_orientation': info['UISupportedInterfaceOrientations'].pop()
    elif mutation == 'changed_notice': (share / 'Notices/license.txt').write_bytes(b'changed')
    elif mutation == 'missing_privacy': (share / 'Privacy.txt').unlink()
    elif mutation == 'missing_executable': (share / 'AITrustIDShare').unlink()
    elif mutation == 'missing_icon': (app / 'Assets.car').unlink()
    elif mutation == 'profile': (share / 'embedded.mobileprovision').write_bytes(b'not accepted')
    elif mutation == 'signature': (share / '_CodeSignature').mkdir()
    elif mutation == 'resource_link':
        (share / 'Privacy.txt').unlink(); (share / 'Privacy.txt').symlink_to(app / 'Privacy.txt')
    (app / 'Info.plist').write_bytes(plistlib.dumps(info))
    with pytest.raises(ValueError): inspect(root, payload)
