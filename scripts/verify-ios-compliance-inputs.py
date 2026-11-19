#!/usr/bin/env python3
"""Measure encryption-related inputs for the exact signed internal iPhone build."""

import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import plistlib
import stat
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.source_snapshot import read_file

UPLOAD = 'runs/2026-11-18-ios-testflight-internal-upload.json'
RUNTIME = 'sbom/nested-runtime/pyodide-wasm-release.json'
APP = 'Payload/AITrustID.app/'
TARGETS = {APP: 'com.aitrustid.app', APP + 'PlugIns/AITrustIDShare.appex/': 'com.aitrustid.app.share'}
PROBE = '''
import hashlib, importlib.util, json, sqlite3, sys, zlib
from compression import zstd
try:
    import ssl
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    tls = {'provider': ssl.OPENSSL_VERSION, 'client_context_created': True,
           'cipher_suite_count': len(context.get_ciphers())}
except ImportError:
    tls = {'provider': None, 'client_context_created': False, 'cipher_suite_count': 0}
print(json.dumps({
    'tls': tls,
    'embedded_libraries': {
        'python': '.'.join(map(str, sys.version_info[:3])),
        'sqlite_source_id': sqlite3.connect(':memory:').execute('select sqlite_source_id()').fetchone()[0],
        'zlib': zlib.ZLIB_RUNTIME_VERSION, 'zstd': zstd.zstd_version,
    },
    'sha256_provider': hashlib.sha256.__module__,
    'sha256_known_answer_pass': hashlib.sha256(b'abc').hexdigest() ==
        'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad',
    'module_available': {name: importlib.util.find_spec(name) is not None
                         for name in ('_ssl', '_hashlib', '_hmac', '_sha2')},
}))
'''
NODE_RUNNER = """
import { pathToFileURL } from 'node:url';
import { readFileSync } from 'node:fs';
const directory = process.argv[1];
const { loadPyodide } = await import(pathToFileURL(`${directory}/pyodide.mjs`).href);
let output;
const vm = await loadPyodide({ indexURL: directory, stdout: text => { output = text; } });
vm.runPython(readFileSync(0, 'utf8'));
if (output === undefined) throw Error('Missing runtime observation');
console.log(output);
"""


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def member(archive, name, limit):
    selected = [info for info in archive.infolist() if info.filename == name]
    require(len(selected) == 1, 'Expected exactly one selected archive file')
    (info,) = selected
    require(0 < info.file_size <= limit and not stat.S_ISLNK(info.external_attr >> 16),
            'Unexpected archive file size or link')
    return archive.read(info)


def verify(ipa):
    upload = json.loads((ROOT / UPLOAD).read_text())
    proof = json.loads((ROOT / upload['signed_archive_and_validation']).read_text())
    origin = json.loads((ROOT / RUNTIME).read_text())
    raw = read_file(ipa, proof['exported_ipa_bytes'])
    require(upload['upload_completed'] and upload['build'] == proof['build']
            and upload['source_commit'] == proof['source_commit']
            and upload['validation_receipt_sha256'] == sha((ROOT / upload['signed_archive_and_validation']).read_bytes())
            and len(raw) == proof['exported_ipa_bytes'] and sha(raw) == proof['exported_ipa_sha256'],
            'Input is not the recorded signed TestFlight IPA')

    def source(name):
        return subprocess.check_output(['git', '--no-replace-objects', 'show', f"{proof['source_commit']}:{name}"],
                                       cwd=ROOT, timeout=15)

    require(b'SHA256.hash(data: data)' in source('mobile/ios/Source/Assets.swift')
            and b'import CryptoKit' in source('mobile/ios/Source/Assets.swift'),
            'Expected CryptoKit integrity check differs')
    bridge = source('mobile/ios/Web/bridge.mjs')
    require(b'_aitrust_hashlib.sha256(_aitrust_source)' in bridge, 'Expected WASM integrity check differs')
    targets = {}
    with tempfile.TemporaryDirectory(prefix='aitrust-ios-runtime-') as staging, zipfile.ZipFile(io.BytesIO(raw)) as archive:
        for prefix, bundle_id in TARGETS.items():
            info = plistlib.loads(member(archive, prefix + 'Info.plist', 1_000_000))
            require((info['CFBundleIdentifier'], info['CFBundleShortVersionString'], info['CFBundleVersion'])
                    == (bundle_id, upload['version'], upload['build']), 'Bundle identity differs')
            require(member(archive, prefix + 'Assets/bridge.mjs', 1_000_000) == bridge,
                    'Archived bridge differs from identified source')
            for name, expected in origin['runtime_members'].items():
                payload = member(archive, prefix + 'Assets/runtime/' + name, expected['bytes'])
                require(len(payload) == expected['bytes'] and sha(payload) == expected['sha256'],
                        'Unexpected packaged runtime bytes')
                if prefix == APP:
                    (Path(staging) / name).write_bytes(payload)
            targets[bundle_id] = {'non_exempt_encryption_plist_value': info.get('ITSAppUsesNonExemptEncryption'),
                                  'runtime_files_matched': len(origin['runtime_members']), 'bridge_matches_source': True}
        runtime = json.loads(subprocess.run(['node', '--input-type=module', '-e', NODE_RUNNER, staging],
                                           input=PROBE, text=True, check=True, capture_output=True, timeout=45).stdout)
    require(runtime['sha256_known_answer_pass'] is True, 'Packaged WASM SHA-256 failed')
    return {'kind': 'ios_testflight_compliance_inputs', 'pass': True, 'version': upload['version'],
            'build': upload['build'], 'captured_at': datetime.now(timezone.utc).isoformat(), 'ipa_sha256': sha(raw), 'source_commit': proof['source_commit'],
            'bundle_observations': targets, 'pyodide_runtime_version': origin['pyodide_version'],
            'native_source_observation': 'Apple CryptoKit SHA-256 resource integrity check',
            'bridge_observation': 'Python hashlib SHA-256 source integrity check',
            'packaged_wasm_node_probe': runtime, 'native_device_crypto_probe': False,
            'export_compliance_determined': False, 'export_compliance_submitted': False,
            'requirements_closed': []}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ipa', type=Path, help='Private copy of the exact signed internal build')
    args = parser.parse_args()
    try:
        print(json.dumps(verify(args.ipa), indent=2))
    except (OSError, ValueError, TypeError, KeyError, subprocess.SubprocessError, zipfile.BadZipFile) as error:
        print(f'iOS compliance input audit failed ({type(error).__name__}).', file=sys.stderr)
        raise SystemExit(1)
