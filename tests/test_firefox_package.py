"""The Firefox package changes execution format, never permission or verdict meaning."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('firefox_package', ROOT/'scripts/build-firefox-extension.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


def fixture(tmp_path):
    root = tmp_path/'source'; shutil.copytree(ROOT/'extension', root/'extension'); shutil.copyfile(ROOT/'LICENSE',root/'LICENSE')
    return root


def test_package_preserves_chrome_and_exact_permissions():
    first, proof = m.package(); second, second_proof = m.package()
    assert first == second and proof == second_proof
    assert proof['sha256'] == hashlib.sha256(first).hexdigest()
    assert proof['store_signed'] is proof['live_vendor_verified'] is proof['independent_accuracy_evidence'] is False
    with zipfile.ZipFile(io.BytesIO(first)) as archive:
        assert set(archive.namelist()) == {'manifest.json', 'LICENSE', *m.FILES}
        assert archive.read('LICENSE') == (ROOT/'LICENSE').read_bytes()
        manifest = json.loads(archive.read('manifest.json'))
        original = json.loads((ROOT/'extension/manifest.json').read_text())
        assert manifest['permissions'] == original['permissions'] == ['storage']
        assert manifest['host_permissions'] == ['https://chatgpt.com/*', 'http://127.0.0.1/*']
        assert manifest['content_scripts'][0]['matches'] == ['https://chatgpt.com/*']
        assert manifest['content_scripts'] == original['content_scripts']
        assert manifest['background'] == {'scripts': ['src/shared/contract.js','src/shared/transport.js','src/sw/service-worker.js']}
        assert manifest['browser_specific_settings']['gecko']['data_collection_permissions'] == {'required':['none']}
        for name in m.FILES:
            raw = (ROOT/'extension'/name).read_bytes()
            expected = raw[len(m.IMPORTS):] if name == 'src/sw/service-worker.js' else raw
            if name == 'src/options.html':
                expected = raw.replace(b'<script src="options.js"></script>', b'<script src="firefox/permissions.js"></script><script src="options.js"></script>')
            assert archive.read(name) == expected
        for info in archive.infolist():
            assert info.date_time == (1980,1,1,0,0,0) and info.compress_type == zipfile.ZIP_STORED
            assert info.external_attr >> 16 == 0o100644


@pytest.mark.parametrize('change',[
    lambda p:p['permissions'].append('tabs'),
    lambda p:p['content_scripts'][0].__setitem__('world','MAIN'),
    lambda p:p['content_scripts'][0].__setitem__('run_at','document_start'),
    lambda p:p['content_scripts'][0].__setitem__('all_frames',True),
    lambda p:p['host_permissions'].append('<all_urls>'),
    lambda p:p['content_scripts'][0]['matches'].append('https://claude.ai/*'),
    lambda p:p['content_scripts'][0]['js'].append('unexpected.js'),
    lambda p:p.__setitem__('externally_connectable',{'matches':['*://*/*']}),
    lambda p:p['background'].__setitem__('type','classic'),
    lambda p:p.__setitem__('options_page','outside.html'),
    lambda p:p.__setitem__('manifest_version',2),
])
def test_permission_or_execution_drift_refused(tmp_path,change):
    root=fixture(tmp_path); path=root/'extension/manifest.json'
    manifest=json.loads(path.read_text());change(manifest);path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError):m.package(root)


@pytest.mark.parametrize('payload',[b'import "https://outside.test/x";\n',m.IMPORTS+b'import "unexpected.js";',m.IMPORTS[1:]])
def test_unknown_module_execution_refused(tmp_path,payload):
    root=fixture(tmp_path);(root/'extension/src/sw/service-worker.js').write_bytes(payload)
    with pytest.raises(ValueError):m.package(root)


def test_source_link_refused(tmp_path):
    root=fixture(tmp_path);path=root/'extension/src/options.js';raw=path.read_bytes()
    path.unlink();other=tmp_path/'outside';other.write_bytes(raw);path.symlink_to(other)
    with pytest.raises(ValueError):m.package(root)


def test_missing_source_refused(tmp_path):
    root=fixture(tmp_path);(root/'extension/src/shared/transport.js').unlink()
    with pytest.raises(OSError):m.package(root)


def test_existing_different_output_and_output_link_preserved(tmp_path):
    script=ROOT/'scripts/build-firefox-extension.py';target=tmp_path/'archive.zip'
    def run():return subprocess.run([sys.executable,str(script),'--output',str(target)],capture_output=True,text=True)
    assert run().returncode==0 and run().returncode==0
    target.write_bytes(b'owner file');assert run().returncode==1 and target.read_bytes()==b'owner file'
    other=tmp_path/'other';other.write_bytes(b'other');target.unlink();target.symlink_to(other)
    assert run().returncode==1 and other.read_bytes()==b'other'


def test_unreviewed_project_license_refused(tmp_path):
 root=fixture(tmp_path);(root/'LICENSE').write_text('proprietary')
 with pytest.raises(ValueError):m.package(root)
