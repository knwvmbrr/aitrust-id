"""Source integrity and non-executing build-info/archive refusal controls."""
import base64
import copy
import hashlib
import io
import json
from pathlib import Path
import shutil
import tarfile
import tempfile
import unittest
from tools import esbuild_cohort as c


def varint(n):
    out=bytearray()
    while n>=128:out.append((n&127)|128);n>>=7
    return bytes(out)+bytes([n])

def inline(version=b'go1.26.4',module=b'bounded module fixture'):
    return c.MAGIC+bytes([8,2])+b'\0'*16+varint(len(version))+version+varint(len(module))+module


class BuildInfo(unittest.TestCase):
    def test_missing_header_does_not_promote_embedded_string(self):
        result=c.build_info(b'fixture\0go1.26.4\0')
        self.assertEqual(result['status'],'unavailable');self.assertEqual(result['reason'],'marker_absent')
        self.assertIsNone(result['toolchain_version']);self.assertEqual(result['embedded_version_literals'],['go1.26.4'])
    def test_inline_header_is_metadata_without_authentication(self):
        result=c.build_info(inline())
        self.assertEqual(result['status'],'inline_metadata_observed');self.assertEqual(result['toolchain_version'],'go1.26.4')
        self.assertFalse(result['publisher_authenticated'])
    def test_ambiguous_unaligned_legacy_and_invalid_headers_refuse(self):
        variants=[inline()+inline(),b'x'+inline(),c.MAGIC+bytes([8,0])+b'\0'*16,inline()[:20],c.MAGIC+bytes([3,2])+b'\0'*16]
        for raw in variants:
            with self.subTest(raw=raw[:16]):self.assertEqual(c.build_info(raw)['status'],'unavailable')
    def test_malformed_lengths_and_utf8_refuse(self):
        variants=[inline(version=b'\xff'),c.MAGIC+bytes([8,2])+b'\0'*16+b'\xff'*10,inline()[:-3],c.MAGIC+bytes([8,2])+b'\0'*16+b'\x80\x00']
        for raw in variants:
            with self.subTest(size=len(raw)):self.assertEqual(c.build_info(raw)['status'],'unavailable')


class ArchiveControls(unittest.TestCase):
    def archive(self,entries):
        stream=io.BytesIO()
        with tarfile.open(fileobj=stream,mode='w:gz') as archive:
            for name,raw,kind in entries:
                info=tarfile.TarInfo(name);info.type=kind;info.size=len(raw)
                if kind==tarfile.SYMTYPE:info.linkname='elsewhere'
                archive.addfile(info,io.BytesIO(raw) if kind==tarfile.REGTYPE else None)
        return stream.getvalue()
    def test_unsafe_duplicate_and_link_members_refuse(self):
        for entries in [[('../outside',b'x',tarfile.REGTYPE)],[('package/a',b'x',tarfile.REGTYPE)]*2,[('package/a',b'',tarfile.SYMTYPE)]]:
            with self.subTest(entries=entries),self.assertRaises(ValueError):c.tar_members(self.archive(entries))
    def test_archive_integrity_precedes_binary_observation(self):
        row=c.selected(c.ROOT)[0]
        with self.assertRaises(ValueError):c.inspect_archive(b'corrupted archive',row)
    def test_safe_archive_is_read_in_memory(self):
        self.assertEqual(c.tar_members(self.archive([('package/README.md',b'example',tarfile.REGTYPE)])),{'package/README.md':b'example'})


class EvidenceControls(unittest.TestCase):
    def test_current_observed_evidence_stays_bounded(self):
        result=c.verify();self.assertTrue(result['pass']);self.assertEqual(result['platform_archives'],26)
        self.assertEqual(result['build_info_unavailable'],26);self.assertFalse(result['binary_bytes_replayed']);self.assertFalse(result['permission_cleared'])
    def clone(self,folder):
        root=Path(folder)
        manifest=json.loads((c.ROOT/c.MANIFEST).read_text())
        names=set(c.FILES)|{c.MANIFEST,'site/package-lock.json','sbom/native/manifest.json','sbom/notices/manifest.json'}|{x['path'] for x in manifest['source_texts']}
        for name in names:
            target=root/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(c.ROOT/name,target)
        return root,manifest
    def test_clearance_promotion_refuses(self):
        for field in ['permission_cleared','release_approved','publisher_signature_verified','reproducible_build_verified']:
            with self.subTest(field=field),tempfile.TemporaryDirectory() as folder:
                root,row=self.clone(folder);row[field]=True;(root/c.MANIFEST).write_text(json.dumps(row))
                with self.assertRaises(ValueError):c.verify(root)
    def test_modified_source_notice_and_missing_platform_refuse(self):
        for change in ['source','notice','platform']:
            with self.subTest(change=change),tempfile.TemporaryDirectory() as folder:
                root,row=self.clone(folder)
                if change=='source':(root/'scripts/verify-esbuild-cohort.py').write_text('changed')
                elif change=='notice':(root/row['source_texts'][0]['path']).write_text('changed notice')
                else:row['platform_artifacts'].pop();(root/c.MANIFEST).write_text(json.dumps(row))
                with self.assertRaises(ValueError):c.verify(root)
    def test_unavailable_cannot_be_changed_to_toolchain_identity(self):
        with tempfile.TemporaryDirectory() as folder:
            root,row=self.clone(folder);row['platform_artifacts'][0]['members'][0]['build_info']['toolchain_version']='go1.26.4';(root/c.MANIFEST).write_text(json.dumps(row))
            with self.assertRaises(ValueError):c.verify(root)

if __name__=='__main__':unittest.main()
