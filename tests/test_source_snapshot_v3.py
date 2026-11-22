"""Bounded source-capacity controls; large stream cases run on disposable CI."""
import gzip
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import source_snapshot as v1
import source_snapshot_v2 as v2
import source_snapshot_v3 as s

COMMIT = 'a'*40


def metadata():
    return json.dumps({'profile': s.PROFILE, 'source_commit': COMMIT,
        'kind': 'development_source_snapshot', 'tag_release_validated': False,
        'installed_dependencies_included': False, 'files': []}, sort_keys=True,
        separators=(',', ':')).encode()


def header(name, size):
    info = tarfile.TarInfo(s.PREFIX+name)
    info.size = size
    info.mode = 0o644
    info.mtime = info.uid = info.gid = 0
    info.uname = info.gname = ''
    return info.tobuf(format=tarfile.USTAR_FORMAT)


def encoded_tar(records, extra=b''):
    raw = b''.join(header(n, len(data))+data+b'\0'*((-len(data)) % 512)
                   for n, data in records) + b'\0'*1024
    raw += b'\0'*((-len(raw)) % tarfile.RECORDSIZE)
    return gzip.compress(raw+extra, mtime=0)


class SmallCompatibility(unittest.TestCase):
    def test_immutable_modules_and_separate_limits(self):
        for name, expected in [('source_snapshot.py', '24df10061afea39710fb65799d54d386c177caed80629a4f15bc5384fc2c17ee'),
                               ('source_snapshot_v2.py', 'baa1ce4b9b0066ad4161d472d5d3df190f6e7bc5817b29c58ce35686f130fb46')]:
            self.assertEqual(hashlib.sha256((ROOT/'scripts'/name).read_bytes()).hexdigest(), expected)
        self.assertEqual((v1.MAX_TOTAL, v2.MAX_TOTAL, s.MAX_TOTAL, s.MAX_METADATA),
                         (128_000_000, 128_000_000, 256_000_000, 5_000_000))
        self.assertEqual((s.MAX_FILES, s.MAX_FILE, s.MAX_ARCHIVE), (16384, 32_000_000, 64_000_000))
        self.assertIs(s.read_file, v1.read_file)

    def small_archive(self):
        with tempfile.TemporaryDirectory(prefix='owned-source-v3-') as tmp:
            root = Path(tmp).resolve()
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            (root/'public.txt').write_bytes(b'Synthetic public source.\n')
            (root/'empty.txt').write_bytes(b'')
            subprocess.run(['git', '-C', str(root), 'add', '.'], check=True)
            subprocess.run(['git', '-C', str(root), '-c', 'user.name=Owned fixture',
                            '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'Synthetic'], check=True)
            commit = s.git(root, 'rev-parse', 'HEAD').decode().strip()
            raw = s.build(root, commit)
            self.assertEqual(raw, v1.build(root, commit))
            self.assertEqual(raw, v2.build(root, commit))
            self.assertEqual(s.inspect(raw, commit), v2.inspect(raw, commit))
            self.assertEqual(s.inspect(raw, commit)['source_files'], 2)
            return raw, commit

    def test_actual_small_git_archive_bytes_and_results_match(self):
        self.small_archive()
        with tempfile.TemporaryDirectory(prefix='owned-isolated-source-cli-') as temp:
            stage = Path(temp).resolve()
            repo = stage/'project';scripts = repo/'scripts';scripts.mkdir(parents=True)
            names = ('source_snapshot.py', 'source_snapshot_v2.py', 'source_snapshot_v3.py',
                     'build-source-snapshot.py', 'verify-source-provenance.py')
            for name in names:
                (scripts/name).write_bytes((ROOT/'scripts'/name).read_bytes())
            (repo/'README.md').write_bytes(b'Owned synthetic CLI source.\n')
            subprocess.run(['git', 'init', '-q', str(repo)], check=True)
            subprocess.run(['git', '-C', str(repo), 'add', '.'], check=True)
            subprocess.run(['git', '-C', str(repo), '-c', 'user.name=Owned CLI fixture',
                            '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'Synthetic'], check=True)
            commit = s.git(repo, 'rev-parse', 'HEAD').decode().strip()
            for name in ('build-source-snapshot.py', 'verify-source-provenance.py'):
                help_result = subprocess.run([sys.executable, '-I', '-S', '-B', str(scripts/name), '--help'],
                    cwd=stage, capture_output=True, timeout=10)
                self.assertEqual(help_result.returncode, 0)
                self.assertEqual(help_result.stderr, b'')
            output = stage/'public-source.tar.gz'
            result = subprocess.run([sys.executable, '-I', '-S', '-B', str(scripts/'build-source-snapshot.py'),
                '--commit', commit, '--output', str(output)], cwd=stage, capture_output=True, timeout=15)
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stderr, b'')
            self.assertEqual(json.loads(result.stdout), {'pass': True, **s.inspect(output.read_bytes(), commit)})
            self.assertEqual(json.loads(result.stdout)['source_files'], 6)

    def test_source_metadata_separate_accounting_and_old_globals(self):
        raw, commit = self.small_archive()
        with patch.object(s, 'MAX_TOTAL', len(b'Synthetic public source.\n')):
            self.assertEqual(s.inspect(raw, commit)['source_files'], 2)
        self.assertEqual(v1.MAX_TOTAL, 128_000_000)
        self.assertEqual(v2.MAX_TOTAL, 128_000_000)


class RefusalBoundaries(unittest.TestCase):
    def test_count_refuses_before_any_blob_read(self):
        listing = (b'100644 blob '+b'a'*40+b' 1\tx.txt\0')*16385
        with patch.object(s, 'git', side_effect=[COMMIT.encode()+b'\n', listing]) as git:
            with self.assertRaisesRegex(ValueError, 'Committed source limit'):
                s.build(ROOT, COMMIT)
            self.assertEqual(git.call_count, 2)

    def test_per_file_refuses_before_blob_read(self):
        listing = b'100644 blob '+b'a'*40+b' 32000001\tx.txt\0'
        with patch.object(s, 'git', side_effect=[COMMIT.encode()+b'\n', listing]) as git:
            with self.assertRaisesRegex(ValueError, 'Committed source limit'):
                s.build(ROOT, COMMIT)
            self.assertEqual(git.call_count, 2)
        raw = gzip.compress(header(s.META, len(metadata()))+metadata()+b'\0'*((-len(metadata()))%512)
                            +header('x.txt', 32_000_001), mtime=0)
        with self.assertRaisesRegex(ValueError, 'Source member limit'):
            s.inspect(raw, COMMIT)

    def test_total_source_limit_refuses_before_first_blob_read(self):
        listing = b''.join(b'100644 blob '+b'a'*40+b' '+str(size).encode()+b'\tf'+str(i).encode()+b'\0'
                           for i, size in enumerate([32_000_000]*8+[1]))
        with patch.object(s, 'git', side_effect=[COMMIT.encode()+b'\n', listing]) as git:
            with self.assertRaisesRegex(ValueError, 'Committed source limit'):
                s.build(ROOT, COMMIT)
            self.assertEqual(git.call_count, 2)

    def test_metadata_declared_limit_precedes_collection_or_parse(self):
        raw = gzip.compress(header(s.META, 5_000_001), mtime=0)
        with patch.object(s, 'parse', side_effect=AssertionError('metadata must not be parsed')) as parse:
            with self.assertRaisesRegex(ValueError, 'metadata must be first and bounded'):
                s.inspect(raw, COMMIT)
            parse.assert_not_called()

    def test_compressed_limit_precedes_inflater_construction(self):
        raw = b'X'*(64_000_000+1)
        with patch.object(s.zlib, 'decompressobj', side_effect=AssertionError('late compressed bound')) as decoder:
            with self.assertRaisesRegex(ValueError, 'archive limit'):
                s.inspect(raw, COMMIT)
            decoder.assert_not_called()

    def test_bounded_writer_refuses_before_growing(self):
        out = s._BoundedOutput()
        with patch.object(s, 'MAX_ARCHIVE', 3):
            out.write(b'abc')
            with self.assertRaisesRegex(ValueError, 'Compressed archive limit'):
                out.write(b'd')
            self.assertEqual(out.getvalue(), b'abc')

    def test_inspection_count_includes_metadata_without_extra_source_slot(self):
        raw = encoded_tar([(s.META, metadata()), *[(f'f{i:05d}', b'') for i in range(16385)]])
        with self.assertRaisesRegex(ValueError, 'Source member limit'):
            s.inspect(raw, COMMIT)

    def test_raw_source_limit_streams_without_full_payload_allocation(self):
        out = io.BytesIO()
        with gzip.GzipFile(fileobj=out, mode='wb', mtime=0) as stream:
            data = metadata();stream.write(header(s.META, len(data))+data+b'\0'*((-len(data)) % 512))
            block = b'\0'*65536
            for i in range(8):
                stream.write(header(f'f{i}', 32_000_000))
                remaining = 32_000_000
                while remaining:
                    n = min(len(block), remaining);stream.write(block[:n]);remaining -= n
            stream.write(header('overflow', 1))
        with self.assertRaisesRegex(ValueError, 'Expanded source limit'):
            s.inspect(out.getvalue(), COMMIT)

    def test_expansion_bound_includes_zero_record_padding(self):
        out = io.BytesIO()
        with gzip.GzipFile(fileobj=out, mode='wb', mtime=0) as stream:
            remaining = s.expanded_limit()+1
            block = b'\0'*65536
            while remaining:
                n = min(remaining, len(block));stream.write(block[:n]);remaining -= n
        with self.assertRaisesRegex(ValueError, 'Expanded archive limit'):
            s.inspect(out.getvalue(), COMMIT)

    def test_truncation_crc_concat_trailing_hidden_data_refuse(self):
        value = json.loads(metadata())
        value['files'] = [{'path': 'x.txt', 'mode': 420, 'bytes': 1,
                           'sha256': hashlib.sha256(b'x').hexdigest()}]
        canonical = json.dumps(value, sort_keys=True, separators=(',', ':')).encode()
        members = [(s.META, canonical), ('x.txt', b'x')]
        raw = encoded_tar(members)
        self.assertEqual(s.inspect(raw, COMMIT)['source_bytes'], 1)
        changed = bytearray(raw);changed[-8] ^= 1
        variants = [raw[:-1], bytes(changed), raw+gzip.compress(b'',mtime=0), raw+b'X',
                    encoded_tar(members,extra=b'not source'),
                    encoded_tar(members,extra=b'\0'*tarfile.RECORDSIZE)]
        expanded = gzip.decompress(raw)
        source_offset = 512 + ((len(canonical)+511)//512)*512
        for attr, setting in [('linkname', 'hidden-unused-path')]:
            info = tarfile.TarInfo.frombuf(expanded[source_offset:source_offset+512], 'ascii', 'strict')
            setattr(info, attr, setting)
            changed_header = info.tobuf(format=tarfile.USTAR_FORMAT)
            self.assertNotEqual(changed_header, expanded[source_offset:source_offset+512])
            variants.append(gzip.compress(expanded[:source_offset]+changed_header+expanded[source_offset+512:], mtime=0))
        for variant in variants:
            with self.subTest(bytes=len(variant)), self.assertRaises(ValueError):
                s.inspect(variant, COMMIT)

    def test_exact_metadata_encoding_rejects_numeric_aliases_whitespace_and_order(self):
        value = json.loads(metadata())
        value['files'] = [{'path': 'x.txt', 'mode': 420, 'bytes': 1,
                           'sha256': hashlib.sha256(b'x').hexdigest()}]
        canonical = json.dumps(value, sort_keys=True, separators=(',', ':')).encode()
        raw = encoded_tar([(s.META, canonical), ('x.txt', b'x')])
        self.assertEqual(s.inspect(raw, COMMIT)['source_bytes'], 1)
        variants = [canonical.replace(b'"bytes":1', b'"bytes":true'),
                    canonical.replace(b'"bytes":1', b'"bytes":1.0'),
                    canonical.replace(b'"mode":420', b'"mode":420.0'),
                    json.dumps(value, sort_keys=True, indent=2).encode(),
                    json.dumps(dict(reversed(list(value.items()))), separators=(',', ':')).encode()]
        for changed in variants:
            self.assertNotEqual(changed, canonical)
            with self.subTest(bytes=len(changed)), self.assertRaises(ValueError):
                s.inspect(encoded_tar([(s.META, changed), ('x.txt', b'x')]), COMMIT)

    def test_bool_file_size_cannot_impersonate_zero(self):
        value = json.loads(metadata())
        value['files'] = [{'path': 'empty.txt', 'mode': 420, 'bytes': False,
                           'sha256': hashlib.sha256(b'').hexdigest()}]
        raw = encoded_tar([(s.META, json.dumps(value).encode()), ('empty.txt', b'')])
        with self.assertRaisesRegex(ValueError, 'record types refused'):
            s.inspect(raw, COMMIT)

    def test_member_padding_is_charged_and_must_be_zero(self):
        source = b'x';meta = metadata()
        raw = header(s.META,len(meta))+meta+b'\0'*((-len(meta))%512)+header('x.txt',1)+source+b'X'+b'\0'*510+b'\0'*1024
        raw += b'\0'*((-len(raw))%tarfile.RECORDSIZE)
        with self.assertRaisesRegex(ValueError, 'Nonzero source member padding'):
            s.inspect(gzip.compress(raw,mtime=0),COMMIT)


if __name__ == '__main__':
    unittest.main()
