"""Authored quotation-context controls; no MT accuracy or release evidence."""
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import sys
import pytest
from protocol.corpus import CorpusError
from protocol.normalization import normalize_nfc
from tools import authority_quotation as q
from tools import language_observations as legacy

ROOT = Path(__file__).resolve().parents[1]


def observe(subject):
    return q.observe(subject, 'en')


def cli(subject, *arguments):
    return subprocess.run([sys.executable, str(ROOT/'scripts/authority-quotation.py'),
                           '--language', 'en', *map(str, arguments)], input=subject,
                          capture_output=True, timeout=10)


def test_quoted_mention_retained_without_outside_observation():
    text = 'The training example says "Experts agree".'
    assert len(legacy.observe('authority', text)['findings']) == 1
    brief, details = observe(text)
    assert brief['outside_supported_quotes_without_marker'] == 0
    assert brief['quoted_phrase_count'] == 1 and brief['state'] == 'NO_SUPPORTED_PATTERN'
    row = details['quoted_phrases'][0]
    assert text[slice(*row['phrase_span'])] == 'Experts agree'
    assert text[slice(*row['quote_span'])] == '"Experts agree"'
    assert row['source_marker_spans'] == []


def test_quoted_marker_cannot_attributed_to_unquoted_authority():
    text = 'Experts agree; the quoted example is "https://example.invalid".'
    assert not legacy.observe('authority', text)['findings']
    brief, details = observe(text)
    assert brief['outside_supported_quotes_without_marker'] == 1
    assert not details['outside_marked_phrases']
    assert details['outside_markerless_phrases'][0]['source_marker_spans'] == []


def test_marker_context_retained_and_url_stops_at_quote():
    text = '"Experts agree: https://example.invalid"; studies show benefits [12].'
    brief, details = observe(text)
    assert brief['quoted_phrase_count'] == 1
    assert brief['outside_supported_quotes_with_marker'] == 1
    quoted = details['quoted_phrases'][0]
    plain = details['outside_marked_phrases'][0]
    assert [text[slice(*s)] for s in quoted['source_marker_spans']] == ['https://example.invalid']
    assert [text[slice(*s)] for s in plain['source_marker_spans']] == ['[12]']


def test_citations_do_not_cross_between_quotes_or_literal_units():
    text = '"Experts agree" and "https://example.invalid". Studies show benefits.'
    brief, details = observe(text)
    assert brief['quoted_phrase_count'] == 1
    assert details['quoted_phrases'][0]['source_marker_spans'] == []
    assert brief['outside_supported_quotes_without_marker'] == 1
    assert not details['outside_marked_phrases']


def test_outside_marker_can_cross_quoted_gap_in_same_literal_unit():
    text = 'Experts agree; "a short example"; see [1].'
    brief, details = observe(text)
    assert brief['outside_supported_quotes_with_marker'] == 1
    assert text[slice(*details['outside_marked_phrases'][0]['source_marker_spans'][0])] == '[1]'


@pytest.mark.parametrize('text', ['Experts "agree".', '"Experts" agree.', 'Expertsexperts agree.',
                                  'Experts agreeness.', 'Experts\nagree.', 'Experts  agree.'])
def test_partial_or_cross_context_phrases_not_invented(text):
    brief, _ = observe(text)
    assert brief['outside_supported_quotes_without_marker'] == 0
    assert brief['quoted_phrase_count'] == 0


def test_multiline_quote_preserves_exact_subject_and_units():
    text = '"Experts agree.\nStudies show benefits". Doctors recommend it.'
    brief, details = observe(text)
    assert brief['quoted_phrase_count'] == 2
    assert brief['outside_supported_quotes_without_marker'] == 1
    assert all(row['quote_span'] == [0, text.index('"', 1)+1] for row in details['quoted_phrases'])
    for row in details['quoted_phrases'] + details['outside_markerless_phrases']:
        a, b = row['phrase_span']; c, d = row['unit_span']
        assert c <= a < b <= d


def test_normalized_identity_determinism_and_source_hashes():
    original = 'Cafe\u0301: "Experts agree". Studies show it.'
    text = normalize_nfc(original)
    brief, details = observe(original)
    assert details['subject_sha256'] == hashlib.sha256(text.encode()).hexdigest()
    assert text[slice(*details['quoted_phrases'][0]['phrase_span'])] == 'Experts agree'
    assert (brief, details) == observe(original)
    assert details['source_sha256'] == {p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in q.SOURCES}
    assert original not in json.dumps(details) and text not in json.dumps(details)


@pytest.mark.parametrize('text', ['"Experts agree', 'Experts agree"', '“Experts agree”',
                                  '«Experts agree»', '`Experts agree`', '"Experts \\"agree"',
                                  '', ' ', '\x00', '\ud800', 'x'*8001, None, 1])
def test_unsupported_input_refuses_without_guessing(text):
    with pytest.raises(CorpusError): observe(text)


@pytest.mark.parametrize('text', ['"" '*65, 'Experts agree; '*129, 'x. '*513, '[1] '*257])
def test_resource_bounds_refuse(text):
    with pytest.raises(CorpusError): observe(text)


def test_boundaries_and_no_network(monkeypatch):
    def forbidden(*args, **kwargs): raise AssertionError('Network must not be used')
    monkeypatch.setattr(socket, 'socket', forbidden)
    brief, details = observe("Someone's example: Experts agree.")
    assert brief['tags'] == []
    for field in ('source_lookup_performed', 'quote_endorsement_interpreted', 'intent_established',
                  'truth_established', 'independent_accuracy_evidence', 'network_used'):
        assert brief[field] is False
    assert details['subject_text_included'] is False
    assert len(observe('x'*8000)[0]) == len(brief)
    assert len(observe('"" '*64)[1]['quote_spans']) == 64


def test_cli_private_details_and_no_overwrite(tmp_path):
    tmp_path.chmod(0o700)
    text = b'PRIVATE_CANARY Experts agree; example "https://example.invalid".'
    destination = tmp_path/'details'
    result = cli(text, '--details', destination)
    assert result.returncode == 0 and not result.stderr
    brief = json.loads(result.stdout)
    assert brief['private_details_saved'] is True
    assert brief['outside_supported_quotes_without_marker'] == 1
    assert b'PRIVATE_CANARY' not in result.stdout + result.stderr
    assert 'subject_sha256' not in brief and 'source_sha256' not in brief
    assert destination.stat().st_mode & 0o777 == 0o700
    file = destination/'authority-quotation.json'
    assert file.stat().st_mode & 0o777 == 0o600
    before = file.read_bytes()
    assert b'PRIVATE_CANARY' not in before
    again = cli(text, '--details', destination)
    assert again.returncode == 2 and json.loads(again.stdout)['state'] == 'UNAVAILABLE'
    assert file.read_bytes() == before


@pytest.mark.parametrize('text', [b'PRIVATE_CANARY "Experts agree', b'\xffPRIVATE_CANARY', b'x'*32001])
def test_cli_failure_fixed_private_and_bounded(text):
    result = cli(text)
    assert result.returncode == 2 and not result.stderr
    assert json.loads(result.stdout) == {'state':'UNAVAILABLE', 'reason':'unsupported_authority_quotation_context', 'tags':[]}
    assert b'PRIVATE_CANARY' not in result.stdout


def test_cli_refuses_public_parent_and_symlink(tmp_path):
    tmp_path.chmod(0o755)
    assert cli(b'Experts agree.', '--details', tmp_path/'public').returncode == 2
    tmp_path.chmod(0o700)
    link = tmp_path/'link'; link.symlink_to(tmp_path, target_is_directory=True)
    assert cli(b'Experts agree.', '--details', link/'details').returncode == 2
    assert not (tmp_path/'details').exists()


def test_legacy_cli_survives_optional_candidate_module_failure():
    # The legacy executable never imports this opt-in module. An import blocker
    # simulates unavailable candidate code without changing source files.
    script = '''import importlib.abc, runpy, sys
class Block(importlib.abc.MetaPathFinder):
 def find_spec(self, fullname, path=None, target=None):
  if fullname == 'tools.authority_quotation': raise SyntaxError('unavailable candidate')
sys.meta_path.insert(0, Block())
sys.argv=['scripts/language-observations.py', sys.argv[1], '--language', 'en']
runpy.run_path('scripts/language-observations.py', run_name='__main__')
'''
    for kind, text in [('authority', 'Experts agree.'), ('urgency', 'Buy now.')]:
        result = subprocess.run([sys.executable, '-c', script, kind], input=text,
                                text=True, cwd=ROOT, capture_output=True, timeout=10)
        assert result.returncode == 0 and json.loads(result.stdout)['findings']


@pytest.mark.parametrize('failure', ['ImportError', 'SyntaxError'])
def test_candidate_cli_import_failure_is_fixed_unavailable(failure):
    script = '''import importlib.abc, runpy, sys
class Block(importlib.abc.MetaPathFinder):
 def find_spec(self, fullname, path=None, target=None):
  if fullname == 'tools.authority_quotation': raise ERROR('PRIVATE_IMPORT_CANARY')
sys.meta_path.insert(0, Block())
sys.argv=['scripts/authority-quotation.py', '--language', 'en']
runpy.run_path('scripts/authority-quotation.py', run_name='__main__')
'''.replace('ERROR', failure)
    result = subprocess.run([sys.executable, '-c', script], input='Experts agree.',
                            text=True, cwd=ROOT, capture_output=True, timeout=10)
    assert result.returncode == 2 and not result.stderr
    assert json.loads(result.stdout)['state'] == 'UNAVAILABLE'
    assert 'PRIVATE_IMPORT_CANARY' not in result.stdout
