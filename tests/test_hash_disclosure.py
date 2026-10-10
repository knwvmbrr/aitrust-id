"""A SHA-256 subject is a repeatable lookup key, not a privacy transformation."""
import importlib.util
from pathlib import Path
import pytest
from protocol.subjects import text_subject
ROOT=Path(__file__).resolve().parents[1]
def test_identical_text_links_without_user_identity():
    assert text_subject('same answer')['sha256']==text_subject('same answer')['sha256']
    assert text_subject('same answer')['sha256']!=text_subject('different answer')['sha256']
def test_small_dictionary_can_recover_low_entropy_answer():
    answers=['yes','no','maybe']; fingerprint=text_subject('no')['sha256']
    assert [value for value in answers if text_subject(value)['sha256']==fingerprint]==['no']
def test_published_boundary_and_real_correlations():
    spec=importlib.util.spec_from_file_location('hash_disclosure',ROOT/'scripts/verify-hash-disclosure.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    assert module.verify()['pass']
