"""Exact public PS assets for native engine verification; no containing app or Share installer."""
import hashlib
import json
from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[1]

def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def assets():
    notice_root = ROOT / 'site/public/device-licenses'
    required_notices = {'pyodide-MPL-2.0.txt', 'python-license.txt', 'source.txt', 'unicode-license.txt'}
    if ({file.name for file in notice_root.iterdir()} != required_notices
            or any(not file.is_file() or file.is_symlink() for file in notice_root.iterdir())
            or (notice_root / 'unicode-license.txt').read_bytes() != (ROOT / 'eval/vectors/unicode/LICENSE.txt').read_bytes()):
        raise ValueError('Exact runtime and Unicode notices required')
    manifest = json.loads((ROOT / 'site/src/device-manifest.json').read_text())
    expected = {'method_sha256', 'bundle_sha256', 'path', 'runtime', 'max_codepoints', 'normalization_id', 'normalization_data_sha256'}
    if (set(manifest) != expected or manifest['runtime'] != '314.0.7' or type(manifest['max_codepoints']) is not int
            or manifest['max_codepoints'] != 20000 or manifest['normalization_id'] != 'NFC-Unicode-15.0.0/v1'
            or manifest['normalization_data_sha256'] != digest((ROOT / 'protocol/unicode15-data.json').read_bytes())
            or manifest['path'] != '/device/method-' + manifest['bundle_sha256'] + '.py'
            or any(not isinstance(manifest[key], str) or len(manifest[key]) != 64 or any(c not in '0123456789abcdef' for c in manifest[key]) for key in ['method_sha256', 'bundle_sha256'])):
        raise ValueError('Prepared manifest refused')
    method = (ROOT / 'site/public' / manifest['path'].lstrip('/')).read_bytes()
    if digest(method) != manifest['bundle_sha256']: raise ValueError('Prepared method changed')
    # Rebuild the identity from current evaluator bytes instead of trusting a stale manifest.
    current = digest((ROOT / 'services/evaluator/app.py').read_bytes())
    if current != manifest['method_sha256']: raise ValueError('Prepare current device assets first')
    rebuilt, rebuilt_hash = runpy.run_path(str(ROOT / 'scripts/build-device-detector.py'))['project']((ROOT / 'services/evaluator/app.py').read_bytes())
    if rebuilt != method or rebuilt_hash != current: raise ValueError('Prepared projection differs from current sources')
    vendor = ROOT / 'site/node_modules/pyodide'
    if json.loads((vendor / 'package.json').read_text()).get('version') != manifest['runtime']:
        raise ValueError('Installed runtime version differs')
    payload = {}
    web = list((ROOT / 'mobile/ios/Web').iterdir())
    if {file.name for file in web} != {'index.html', 'bridge.mjs'}:
        raise ValueError('Unreviewed native web asset')
    for file in sorted(web):
        if not file.is_file() or file.is_symlink(): raise ValueError('Web source refused')
        payload['Assets/' + file.name] = file.read_bytes()
    runtime = ROOT / 'site/public/device' / ('runtime-' + manifest['runtime'])
    for file in sorted(runtime.iterdir()):
        if not file.is_file() or file.is_symlink(): raise ValueError('Runtime source refused')
        if file.name not in {'pyodide.mjs', 'pyodide.asm.mjs', 'pyodide.asm.wasm', 'python_stdlib.zip', 'pyodide-lock.json'} or file.read_bytes() != (vendor / file.name).read_bytes():
            raise ValueError('Prepared runtime differs from installed pinned package')
        payload['Assets/runtime/' + file.name] = file.read_bytes()
    if len([key for key in payload if key.startswith('Assets/runtime/')]) != 5:
        raise ValueError('Incomplete runtime')
    payload['Assets/method.py'] = method
    payload['Assets/device-manifest.json'] = (json.dumps(manifest, sort_keys=True) + '\n').encode()
    hashes = {'/' + name.removeprefix('Assets/'): digest(raw) for name, raw in payload.items() if name.startswith('Assets/')}
    payload['Assets/native-assets.json'] = (json.dumps({'format': 'ai-trust-id-native-assets/v1', 'method_sha256': current, 'bundle_sha256': manifest['bundle_sha256'], 'hashes': hashes}, sort_keys=True) + '\n').encode()
    payload['LICENSE'] = (ROOT / 'LICENSE').read_bytes()
    notices = ROOT / 'site/public/device-licenses'
    files = sorted(notices.rglob('*'))
    if not any(file.is_file() for file in files):
        raise ValueError('Prepared runtime notices unavailable')
    for file in files:
        if file.is_symlink():
            raise ValueError('Notice link refused')
        if file.is_file():
            payload['Notices/' + file.relative_to(notices).as_posix()] = file.read_bytes()
    return payload
