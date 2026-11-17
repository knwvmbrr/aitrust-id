"""Android packaging refusal controls with synthetic runtime members; no SDK/model downloads."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('android_build_controls',ROOT/'scripts/android-share-build.py')
build=importlib.util.module_from_spec(spec);spec.loader.exec_module(build)

class AndroidShare(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        base=Path(self.temp.name).resolve();self.root=base/'source';self.root.mkdir();self.runtime=base/'runtime';self.runtime.mkdir()
        paths=['scripts/build-device-detector.py','services/evaluator/app.py','protocol/normalization.py','protocol/unicode15-data.json','site/package-lock.json','sbom/notices/manifest.json','sbom/assets/notices.json','LICENSE','eval/vectors/unicode/LICENSE.txt','mobile/android/web/index.html','mobile/android/web/bridge.mjs']
        paths+=['site/public/device-licenses/'+n for n in ('pyodide-MPL-2.0.txt','python-license.txt','source.txt','unicode-license.txt')]
        for name in paths:
            dest=self.root/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,dest)
        (self.runtime/'package.json').write_text('{"version":"314.0.7"}')
        retained=json.loads((self.root/'sbom/assets/notices.json').read_text())
        # Unit fixtures are explicitly synthetic; actual pinned upstream bytes
        # are separately exercised by preparation and real-WASM parity evidence.
        for row in retained['runtime_members']:
            raw=('synthetic '+row['name']).encode();(self.runtime/row['name']).write_bytes(raw)
            row.update(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
        (self.root/'sbom/assets/notices.json').write_text(json.dumps(retained))
        self.oldroot,self.oldoutput=build.ROOT,build.OUTPUT
        build.ROOT=self.root;build.OUTPUT=self.root/'output/android-share'
        self.addCleanup(self.restore)
    def restore(self):build.ROOT,build.OUTPUT=self.oldroot,self.oldoutput
    def test_complete_package_binds_current_method_and_only_known_assets(self):
        result=build.prepare(self.runtime)
        manifest=json.loads((build.OUTPUT/'assets/asset-manifest.json').read_text())
        self.assertEqual(result['verified_runtime_members'],5);self.assertEqual(result['assets'],15)
        self.assertEqual(result['method_sha256'],hashlib.sha256((self.root/'services/evaluator/app.py').read_bytes()).hexdigest())
        self.assertEqual(len(manifest['files']),9)
        for name,row in manifest['files'].items():self.assertEqual(row['sha256'],hashlib.sha256((build.OUTPUT/'assets'/name).read_bytes()).hexdigest())
        self.assertFalse(result['independent_accuracy_evidence']);self.assertFalse(result['license_clearance'])
    def test_identical_source_preparation_is_byte_identical(self):
        build.prepare(self.runtime);before={p.relative_to(build.OUTPUT):p.read_bytes() for p in build.OUTPUT.rglob('*') if p.is_file()}
        build.prepare(self.runtime);after={p.relative_to(build.OUTPUT):p.read_bytes() for p in build.OUTPUT.rglob('*') if p.is_file()}
        self.assertEqual(before,after)
    def test_changed_runtime_bytes_are_refused_before_package_publication(self):
        (self.runtime/'pyodide.asm.wasm').write_bytes(b'changed')
        with self.assertRaises(ValueError):build.prepare(self.runtime)
        self.assertFalse((build.OUTPUT/'preparation.json').exists())
    def test_changed_runtime_version_is_refused(self):
        (self.runtime/'package.json').write_text('{"version":"unexpected"}')
        with self.assertRaises(ValueError):build.prepare(self.runtime)
    def test_changed_notice_is_refused(self):
        (self.root/'site/public/device-licenses/python-license.txt').write_text('changed notice')
        with self.assertRaises(ValueError):build.prepare(self.runtime)
        self.assertFalse((build.OUTPUT/'preparation.json').exists())
    def test_extra_existing_asset_cannot_be_silently_packaged(self):
        dest=build.OUTPUT/'assets/private-unlisted.txt';dest.parent.mkdir(parents=True);dest.write_text('must not package')
        with self.assertRaises(ValueError):build.prepare(self.runtime)
        self.assertEqual(dest.read_text(),'must not package')
    def test_output_link_does_not_modify_its_target(self):
        target=Path(self.temp.name)/'unrelated';target.write_text('preserved')
        dest=build.OUTPUT/'assets/method.py';dest.parent.mkdir(parents=True);dest.symlink_to(target)
        with self.assertRaises(ValueError):build.prepare(self.runtime)
        self.assertEqual(target.read_text(),'preserved')
    def test_missing_sdk_cannot_emit_a_successful_apk(self):
        build.prepare(self.runtime)
        with self.assertRaises(OSError):build.compile_apk(Path(self.temp.name)/'missing-sdk',Path(self.temp.name)/'missing-jdk')
        self.assertFalse((build.OUTPUT/'build.json').exists())
    def test_manifest_requests_no_network_capture_or_storage_permissions(self):
        manifest=ET.parse(ROOT/'mobile/android/AndroidManifest.xml').getroot();ns='{http://schemas.android.com/apk/res/android}'
        self.assertEqual(manifest.findall('uses-permission'),[])
        app=manifest.find('application');self.assertEqual(app.attrib[ns+'allowBackup'],'false');self.assertEqual(app.attrib[ns+'debuggable'],'false')
        activities=app.findall('activity');self.assertEqual(len(activities),1)
        filters=activities[0].findall('intent-filter')
        types=[data.attrib[ns+'mimeType'] for item in filters for data in item.findall('data')]
        self.assertEqual(types,['text/plain'])

if __name__=='__main__':unittest.main()
