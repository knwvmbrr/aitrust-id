"""Inert bounded archive controls, no source/package execution or acquisition."""
import gzip
import io
from pathlib import Path
import sys
import tarfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import mcp_runtime_obligations as m


def archive(rows):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode='w', format=tarfile.USTAR_FORMAT) as t:
        for name, raw, kind in rows:
            info = tarfile.TarInfo(name)
            info.type = kind
            info.size = len(raw)
            if kind == tarfile.SYMTYPE:
                info.linkname = 'elsewhere'
            t.addfile(info, io.BytesIO(raw))
    return gzip.compress(buf.getvalue(), mtime=0)


class SourceControls(unittest.TestCase):
    def test_actual_grant_and_bounded_leading_notice_not_source_execution(self):
        raw = archive([('pkg/LICENSE', b'MIT License\nCopyright Example\n', tarfile.REGTYPE),
                       ('pkg/src/lib.c', b'/* Copyright Example */\n#include <stdio.h>\nint main() {}\n', tarfile.REGTYPE)])
        result, content = m.observe(raw, m.sha(raw))
        self.assertFalse(result['exact_compiled_closure'])
        self.assertEqual(result['members_observed'], 2)
        self.assertIn(b'/* Copyright Example */\n', content.values())
        self.assertFalse(any(b'int main' in x for x in content.values()))

    def test_wrong_archive_hash_never_decompresses(self):
        raw = archive([('pkg/LICENSE', b'MIT', tarfile.REGTYPE)])
        with patch.object(m.gzip, 'GzipFile', side_effect=AssertionError('must not parse')):
            with self.assertRaises(m.SourceError):
                m.observe(raw, '0'*64)

    def test_pax_bound_precedes_payload_read(self):
        info = tarfile.TarInfo('pax')
        info.type = tarfile.XHDTYPE
        info.size = 65537
        raw = gzip.compress(info.tobuf(tarfile.USTAR_FORMAT))
        with self.assertRaises(m.SourceError):
            m.observe(raw, m.sha(raw))

    def test_member_bound_precedes_payload_read(self):
        info = tarfile.TarInfo('pkg/LICENSE')
        info.size = m.MAX_MEMBER+1
        raw = gzip.compress(info.tobuf(tarfile.USTAR_FORMAT))
        with self.assertRaises(m.SourceError):
            m.observe(raw, m.sha(raw))

    def test_retained_link_and_unsafe_path_refuse(self):
        for name, kind in (('pkg/LICENSE', tarfile.SYMTYPE), ('../LICENSE', tarfile.REGTYPE)):
            raw = archive([(name, b'' if kind == tarfile.SYMTYPE else b'MIT', kind)])
            with self.assertRaises(m.SourceError):
                m.observe(raw, m.sha(raw))

    def test_no_test_keys_or_corpus_retention(self):
        raw = archive([('pkg/tests/example.c', b'/* Copyright Example */\nPRIVATE_FIXTURE\n', tarfile.REGTYPE),
                       ('pkg/tests/key.pem', b'PRIVATE_TEST_KEY', tarfile.REGTYPE),
                       ('pkg/LICENSE', b'MIT License', tarfile.REGTYPE)])
        result, content = m.observe(raw, m.sha(raw))
        self.assertEqual(len(result['retained']), 1)
        self.assertEqual(list(content.values()), [b'MIT License'])

    def test_duplicate_member_and_expanded_budget_refuse(self):
        raw = archive([('pkg/LICENSE', b'MIT', tarfile.REGTYPE)]*2)
        with self.assertRaises(m.SourceError):
            m.observe(raw, m.sha(raw))
        raw = archive([('pkg/LICENSE', b'MIT', tarfile.REGTYPE)])
        with patch.object(m, 'MAX_EXPANDED', 1024), self.assertRaises(m.SourceError):
            m.observe(raw, m.sha(raw))

    def test_malformed_pax_path_and_sparse_metadata_refuse(self):
        for raw in (b'9999 path=../escape\n', b'0 bad\n', b'25 GNU.sparse.map=0,2\n'):
            with self.assertRaises(m.SourceError):
                m.pax(raw)


if __name__ == '__main__':
    unittest.main()
