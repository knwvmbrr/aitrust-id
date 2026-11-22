"""Source-only Cargo/notice graph controls. No package/build/native execution."""
import copy
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch
from tools import c2pa_native_obligations as c

ROOT=Path(__file__).resolve().parents[1]


def lock(ambiguous=False):
    return ('version = 4\n[[package]]\nname="c2pa-c-ffi"\nversion="0.91.0"\ndependencies=['
            + ('"dep"' if ambiguous else '"dep 1.0.0","dep 2.0.0"') + ']\n'
            + ''.join(f'[[package]]\nname="dep"\nversion="{v}.0.0"\nsource="{c.REGISTRY}"\nchecksum="'+str(v)*64+'"\n' for v in [1,2])).encode()


def tar(rows):
    out=io.BytesIO()
    with tarfile.open(fileobj=out,mode='w:gz') as t:
        for name,value,kind in rows:
            info=tarfile.TarInfo(name);info.type=kind;info.size=len(value)
            t.addfile(info,io.BytesIO(value))
    return out.getvalue()


def minimal(extra=()):
    return tar([('demo-1.0.0/Cargo.toml',b'[package]\nname="demo"\nversion="1.0.0"\nlicense="MIT"\n',tarfile.REGTYPE),*extra])


class NativeGraphTests(unittest.TestCase):
    def test_exact_qualified_lock_edges_and_ambiguity(self):
        rows=c.lock_graph(lock());self.assertEqual(len(rows),3)
        root=next(r for r in rows if r['name']==c.ROOT_NAME)
        self.assertEqual(root['dependency_ids'],['dep@1.0.0','dep@2.0.0'])
        with self.assertRaises(ValueError):c.lock_graph(lock(True))
        with self.assertRaises(ValueError):c.lock_graph(lock().replace(b'dep 2.0.0',b'absent 2.0.0'))
        with self.assertRaises(ValueError):c.lock_graph(lock().replace(b'"dep 2.0.0"',b'"dep 1.0.0"'))

    def test_unknown_registry_checksum_and_root_refused(self):
        for raw in [lock().replace(c.REGISTRY.encode(),b'git+https://example.invalid/code'),
                    lock().replace(b'checksum="'+b'1'*64+b'"',b'checksum="bad"'),
                    lock().replace(b'name="c2pa-c-ffi"',b'name="unknown"')]:
            with self.assertRaises(ValueError):c.lock_graph(raw)

    def test_archive_regular_and_notice_authors_readme_selection(self):
        raw=minimal([('demo-1.0.0/AUTHORS',b'Copyright synthetic\nMIT license text',tarfile.REGTYPE),
                     ('demo-1.0.0/README.md',b'license declaration',tarfile.REGTYPE),
                     ('demo-1.0.0/src/lib.rs',b'not selected',tarfile.REGTYPE)])
        rows=c.archive(raw,'demo','1.0.0')
        self.assertEqual(set(rows),{'Cargo.toml','AUTHORS','README.md'})
        node={'id':'demo@1.0.0','name':'demo','version':'1.0.0','archive_sha256':'0'*64,'dependency_ids':[]}
        record=c.package_record(node,rows,{})
        self.assertEqual(len(record['notice_paths']),1);self.assertEqual(len(record['source_readme_paths']),1)
        self.assertEqual(record['unresolved'],[])

    def test_archive_traversal_link_duplicate_wrong_root_refused(self):
        cases=[('../outside',b'x',tarfile.REGTYPE),('demo-1.0.0/link',b'',tarfile.SYMTYPE),
               ('other-1.0.0/Cargo.toml',b'x',tarfile.REGTYPE),('demo-1.0.0/Cargo.toml',b'x',tarfile.REGTYPE)]
        for row in cases:
            with self.assertRaises(ValueError):c.archive(minimal([row]),'demo','1.0.0')

    def test_archive_caps_before_selected_read_and_pax(self):
        raw=minimal([('demo-1.0.0/LICENSE',b'x'*4096,tarfile.REGTYPE)])
        with patch.object(c,'MAX_RETAINED',100):
            with self.assertRaises(ValueError):c.archive(raw,'demo','1.0.0')
        with patch.object(c,'MAX_EXPANDED',2048):
            with self.assertRaises(ValueError):c.archive(raw,'demo','1.0.0')
        with patch.object(c,'MAX_FILES',1):
            with self.assertRaises(ValueError):c.archive(raw,'demo','1.0.0')

    def test_no_follow_fifo_size_and_drift(self):
        with tempfile.TemporaryDirectory(dir=Path(tempfile.gettempdir()).resolve()) as directory:
            p=Path(directory)/'source';p.write_bytes(b'synthetic')
            self.assertEqual(c.read(p),b'synthetic')
            link=Path(directory)/'link';link.symlink_to(p)
            with self.assertRaises(ValueError):c.read(link)
            fifo=Path(directory)/'fifo';os.mkfifo(fifo)
            with self.assertRaises(ValueError):c.read(fifo)
            with self.assertRaises(ValueError):c.read(p,2)
            actual=os.read
            def drift(fd,size):
                b=actual(fd,size);p.write_bytes(b'different');return b
            with patch.object(os,'read',side_effect=drift):
                with self.assertRaises(ValueError):c.read(p)

    def test_fixed_public_lock_hash_is_not_inferred_from_mutable_manifest(self):
        with self.assertRaises((ValueError,OSError)):c.root_source(Path('/nonexistent'),False)
        members={'Cargo.lock':lock(),'Cargo.toml.orig':b'x','.cargo_vcs_info.json':b'{}'}
        with patch.object(c,'load_cache',return_value=b'not executed'),patch.object(c,'archive',return_value=members):
            with self.assertRaises((ValueError,OSError)):c.root_source(Path('/nonexistent'),False)

    def test_actual_graph_consistency_and_fixed_false_claims(self):
        report=c.verify(ROOT)
        self.assertTrue(report['pass']);self.assertEqual(report['packages'],441)
        self.assertEqual(report['dependency_edges'],1131)
        self.assertFalse(report['actual_archive_replay']);self.assertFalse(report['permission_cleared'])

    def test_actual_graph_forged_dependency_license_clearance_refused(self):
        current=c.strict(c.read(ROOT/c.MANIFEST,32*1024**2));original=c.read
        changes=[]
        for key,value in [('permission_cleared',True),('distribution_approved',True)]:
            data=copy.deepcopy(current);data['claims'][key]=value;changes.append(data)
        data=copy.deepcopy(current);data['coverage']['complete_native_dependency_graph']=True;changes.append(data)
        data=copy.deepcopy(current);data['coverage']['complete_native_dependency_graph']=0;changes.append(data)
        data=copy.deepcopy(current);data['packages'][0]['dependency_ids']=[];changes.append(data)
        data=copy.deepcopy(current);data['packages'][0]['license_declared']='PROPRIETARY_APPROVED';changes.append(data)
        for data in changes:
            def reading(path,limit=c.MAX_RETAINED):
                return c.canonical(data) if Path(path)==ROOT/c.MANIFEST else original(path,limit)
            with patch.object(c,'read',side_effect=reading):
                with self.assertRaises((ValueError,KeyError)):c.verify(ROOT)

    def test_native_labels_are_sanitized_positive_only(self):
        manifest=c.strict(c.read(ROOT/'sbom/c2pa-native/native-labels.json'))
        self.assertEqual(len(manifest['observations']),2)
        for observation in manifest['observations']:
            self.assertEqual(len(observation['package_ids']),135)
            self.assertIs(observation['exhaustive'],False)
            self.assertIs(observation['binary_executed'],False)
            self.assertTrue(all('/' not in item and '@' in item for item in observation['package_ids']))

    def test_duplicate_json_private_fields_and_unknown_paths_refused(self):
        with self.assertRaises(ValueError):c.strict(b'{"a":1,"a":2}')
        with self.assertRaises(ValueError):c.strict(b'{"n":NaN}')
        for name in ['../private','/root','a//b','a\\b','a\x00b']:
            with self.assertRaises(ValueError):c.safe(name)
        for name in ['https://example.invalid/a','a/b','x\n']:
            with self.assertRaises(ValueError):c.url(name,'1.0.0')


if __name__=='__main__':unittest.main()
