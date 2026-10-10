"""Protect code-point/byte interoperability and reject invalid subject inputs."""
import importlib.util
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('subject_contract',ROOT/'protocol/subjects.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def test_text_nfc_and_codepoints_not_utf16():
    assert m.text_subject('e\u0301')==m.text_subject('é')
    assert m.text_subject('🧪')['length']==1
    assert m.text_subject('A\r\nB')['sha256']!=m.text_subject('A\nB')['sha256']
def test_code_preserves_bytes_encoding_bom_and_line_endings():
    values=[b'\x00\xff',b'A\r\nB',b'A\nB',b'\xef\xbb\xbfA',b'A',b'e\xcc\x81',b'\xc3\xa9']
    assert len({m.code_subject(x)['sha256'] for x in values})==len(values)
@pytest.mark.parametrize('text',[None,123,b'bytes','\ud800','\udfff','a'*200_001])
def test_invalid_text_is_rejected(text):
    with pytest.raises(ValueError):m.text_subject(text)
@pytest.mark.parametrize('raw',[None,'text',bytearray(b'bytes'),b'a'*800_001])
def test_invalid_code_is_rejected(raw):
    with pytest.raises(ValueError):m.code_subject(raw)
def test_vector_corpus_matches_both_independent_implementations():
    spec=importlib.util.spec_from_file_location('verify_subjects',ROOT/'scripts/verify-subjects.py');v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
    assert v.verify()['vectors']==60
    assert v.verify()['reject_vectors']==8
