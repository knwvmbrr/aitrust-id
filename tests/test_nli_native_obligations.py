"""Finite source/notice controls; no packages, model, network or native execution."""
import copy
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools import nli_native_obligations as n


def tar(rows):
    result=io.BytesIO()
    with tarfile.open(fileobj=result,mode='w:gz')as out:
        for name,data,kind in rows:
            item=tarfile.TarInfo(name);item.size=len(data);item.type=kind
            out.addfile(item,io.BytesIO(data))
    return result.getvalue()


class NativeObligations(unittest.TestCase):
    def test_archive_selected_and_empty_text(self):
        raw=tar([('demo/Cargo.toml',b'[package]\nname="demo"\nversion="1"',tarfile.REGTYPE),('demo/LICENSE',b'original',tarfile.REGTYPE),('demo/src/lib.rs',b'data only',tarfile.REGTYPE)])
        rows,stats=n.archive(raw)
        self.assertEqual(set(rows),{'demo/Cargo.toml','demo/LICENSE'})
        self.assertEqual(stats['source_files_observed'],1)
        self.assertEqual(n.member_bytes(ROOT,{'path':None,'bytes':0,'sha256':n.sha(b'')}),b'')

    def test_archive_unsafe_duplicate_and_bounds(self):
        for name,kind in [('../outside',tarfile.REGTYPE),('demo/link',tarfile.SYMTYPE)]:
            with self.assertRaises(ValueError):n.archive(tar([(name,b'',kind)]))
        with self.assertRaises(ValueError):n.archive(tar([('demo/LICENSE',b'x',tarfile.REGTYPE)]*2))
        raw=tar([('demo/LICENSE',b'x'*4096,tarfile.REGTYPE)])
        with patch.object(n,'MAX_EXPANDED',1024),self.assertRaises(ValueError):n.archive(raw)
        with patch.object(n,'MAX_RETAINED',1024),self.assertRaises(ValueError):n.archive(raw)

    def test_pax_metadata_is_bounded_before_tarfile_allocation(self):
        result=io.BytesIO()
        with tarfile.open(fileobj=result,mode='w:gz',format=tarfile.PAX_FORMAT)as out:
            item=tarfile.TarInfo('demo/LICENSE');item.size=1;item.pax_headers={'comment':'x'*40000};out.addfile(item,io.BytesIO(b'x'))
        with patch.object(n,'MAX_EXPANDED',2048),self.assertRaises(ValueError):n.archive(result.getvalue())

    def test_strict_json_and_source_io(self):
        with self.assertRaises(ValueError):n.document(b'{"a":1,"a":2}')
        with self.assertRaises(ValueError):n.document(b'{"n":NaN}')
        with tempfile.TemporaryDirectory()as temp:
            root=Path(temp).resolve();p=root/'source';p.write_bytes(b'inert');link=root/'link';link.symlink_to(p);fifo=root/'fifo';os.mkfifo(fifo)
            self.assertEqual(n.read(p),b'inert')
            for path in(link,fifo):
                with self.assertRaises((OSError,ValueError)):n.read(path)
            with self.assertRaises(ValueError):n.read(p,1)

    def test_cargo_qualified_edges_and_wrong_dependency_type(self):
        raw=b'version=4\n[[package]]\nname="demo"\nversion="1.0.0"\ndependencies=["other"]\n[[package]]\nname="other"\nversion="1.0.0"\n'
        rows=n.cargo_graph(raw);self.assertEqual(rows[0]['dependency_ids'],['other@1.0.0'])
        with self.assertRaises(ValueError):n.cargo_graph(raw.replace(b'["other"]',b'{other="ignored"}'))
        with self.assertRaises(ValueError):n.cargo_graph(raw.replace(b'"other"\nversion',b'"missing"\nversion'))

    def test_actual_checkout_graph_is_not_archive_or_permission_clearance(self):
        report=n.verify(ROOT)
        self.assertTrue(report['pass']);self.assertFalse(report['actual_source_archive_replay'])
        self.assertEqual(report['native_wheel_occurrences'],16)
        self.assertFalse(report['permission_cleared']);self.assertFalse(report['complete_native_dependency_graph'])

    def test_coherent_mutable_evidence_rebind_refused_by_code_anchor(self):
        raw=n.read(ROOT/n.EVIDENCE,16*1024**2);data=n.document(raw);data['source_archives'][0]['sha256']='0'*64;fake=n.canonical(data);real=n.read
        def read(path,limit=n.MAX_RETAINED):return fake if Path(path)==ROOT/n.EVIDENCE else real(path,limit)
        with patch.object(n,'read',side_effect=read),self.assertRaises(ValueError):n.expected(ROOT)

    def test_permission_or_unknown_package_promotion_refused(self):
        data=n.document(n.read(ROOT/n.MANIFEST,16*1024**2));real=n.read
        for change in('permission','package'):
            row=copy.deepcopy(data)
            if change=='permission':row['claims']['permission_cleared']=True
            else:row['packages'][0]['name']='unobserved-package'
            fake=n.canonical(row)
            def read(path,limit=n.MAX_RETAINED):return fake if Path(path)==ROOT/n.MANIFEST else real(path,limit)
            with patch.object(n,'read',side_effect=read),self.assertRaises(ValueError):n.verify(ROOT)

    def test_actual_cli_fixed_diagnostics_and_wrong_cache_refused(self):
        result=subprocess.run([sys.executable,'-I','-S','-B',str(ROOT/'scripts/verify-nli-native-obligations.py'),'--PRIVATE_CANARY'],capture_output=True,timeout=10)
        self.assertEqual(result.returncode,1);self.assertEqual(result.stdout,b'');self.assertNotIn(b'PRIVATE_CANARY',result.stderr)
        with tempfile.TemporaryDirectory()as temp:
            result=subprocess.run([sys.executable,'-I','-S','-B',str(ROOT/'scripts/verify-nli-native-obligations.py'),'--source-cache',str(Path(temp)/'PRIVATE_CANARY')],capture_output=True,timeout=15)
            self.assertEqual(result.returncode,1);self.assertNotIn(b'PRIVATE_CANARY',result.stdout+result.stderr)


if __name__=='__main__':unittest.main()
