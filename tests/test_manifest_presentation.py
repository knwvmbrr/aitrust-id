"""Readable image evidence must not become an origin verdict or metadata echo."""
import copy
import importlib.util
import json
from pathlib import Path
import sys

import pytest

from protocol.corpus import CorpusError
from tools import manifest_inspection as parser
from tools.manifest_presentation import text_result

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('manifest_cli', ROOT / 'scripts/inspect-manifest.py')
cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli)


def observed():
    return parser.summarize({'active_manifest': 'example', 'manifests': {'example': {}},
        'validation_results': {'activeManifest': {'success': [
            {'code': 'claimSignature.validated'}, {'code': 'assertion.dataHash.match'}],
            'failure': [{'code': 'signingCredential.untrusted'}]}}}, b'invented image')


def envelope(state):
    return {'state': state, 'method': parser.METHOD, 'tags': [],
            'content_truth_established': False, 'author_identity_established': False}


def test_altered_binding_and_intact_signature_are_both_visible():
    value = observed(); value['asset_binding'] = 'mismatched'
    text = text_result(value)
    assert 'Image binding: Does not match the recorded image bytes.' in text
    assert 'Record signature: The record signature matches.' in text
    assert 'Revocation: Unknown. Online revocation checks are disabled.' in text
    assert 'AI origin: Unknown.' in text and 'No tag issued.' in text


def test_unknown_validation_is_not_a_clean_pass():
    value = observed()
    for field in ['asset_binding', 'claim_signature', 'signer_trust']: value[field] = 'unknown'
    text = text_result(value)
    assert text.count('Not established by this inspection.') == 3
    assert 'AI origin: Unknown.' in text


def test_reported_trust_and_revocation_do_not_imply_ai_origin_or_truth():
    value = observed(); value['signer_trust'] = 'reported_trusted'; value['revocation'] = 'reported_revoked'
    text = text_result(value)
    assert 'Signer trust: Reported trusted by the configured trust store.' in text
    assert 'Revocation: Reported revoked; this credential is not cleared.' in text
    assert 'AI origin: Unknown.' in text and 'Image contents and authorship are not verified.' in text


def test_binding_match_does_not_erase_a_signature_mismatch():
    value = observed(); value['claim_signature'] = 'mismatched'
    text = text_result(value)
    assert 'Image binding: Matches the recorded image bytes.' in text
    assert 'Record signature: The record signature does not match.' in text
    assert 'No tag issued.' in text


def test_no_marker_remains_unknown_not_human_or_ai_generated():
    value = envelope('NOT_FOUND'); value['revocation'] = 'not_applicable'
    text = text_result(value)
    assert 'No attached Content Credential was found' in text
    assert 'AI origin: Unknown.' in text
    assert 'Record signature: Not available.' in text


def test_unavailable_is_not_a_completed_origin_check():
    text = text_result(envelope('UNAVAILABLE'))
    assert 'No valid inspection result was obtained.' in text
    assert 'AI origin: Unknown.' in text and 'No tag issued.' in text


def test_known_states_cannot_smuggle_embedded_private_or_terminal_text():
    value = observed(); marker = 'PRIVATE_CANARY\x1b[2J https://example.invalid/private'
    value.update(author=marker, location=marker, path=marker, sharing_warning=marker,
                 assertions=[{'label': marker}], active_validation={'failure': [{'code': marker}]})
    text = text_result(value)
    assert 'PRIVATE_CANARY' not in text and '\x1b' not in text
    assert 'https://' not in text and value['asset_sha256'] not in text
    assert len(text) < 1000


@pytest.mark.parametrize('field,value', [
    ('method', 'PRIVATE_CANARY'), ('tags', ['FA']), ('tags', ()),
    ('content_truth_established', True), ('author_identity_established', True),
    ('independent_accuracy_evidence', True), ('state', 'VALID'),
    ('asset_binding', 'PRIVATE_CANARY\nVALID'), ('asset_binding', ['matched']),
    ('claim_signature', True), ('signer_trust', 'trusted'), ('revocation', 'good'),
    ('private_report_saved', 'PRIVATE_CANARY'),
])
def test_invalid_observation_is_refused_without_echo(field, value):
    result = observed(); result[field] = value
    with pytest.raises(CorpusError) as error: text_result(result)
    assert 'PRIVATE_CANARY' not in str(error.value)


def test_missing_marker_rejects_a_revocation_clearance():
    result = envelope('NOT_FOUND'); result['revocation'] = 'good'
    with pytest.raises(CorpusError): text_result(result)


def test_private_export_notice_does_not_name_output_location():
    result = observed(); result['private_report_saved'] = True
    result['private_report_path'] = '/PRIVATE_CANARY/export.json'
    text = text_result(result)
    assert 'saved privately; it may contain identifying metadata.' in text
    assert 'PRIVATE_CANARY' not in text


def test_default_json_and_explicit_json_keep_identical_consumer_output(monkeypatch, capsys):
    value = observed()
    monkeypatch.setattr(cli.tool, 'inspect', lambda _: (copy.deepcopy(value), None))
    outputs = []
    for tail in [[], ['--format', 'json']]:
        monkeypatch.setattr(sys, 'argv', ['inspect-manifest', '--image', 'PRIVATE_CANARY', *tail])
        assert cli.main() == 0
        outputs.append(capsys.readouterr().out)
    assert outputs[0] == outputs[1]
    result = json.loads(outputs[0]); assert result['state'] == 'OBSERVED'
    assert 'method_sha256' in result and 'PRIVATE_CANARY' not in outputs[0]


def test_cli_native_failure_returns_text_unavailable_without_error_or_path(monkeypatch, capsys):
    def fail(_): raise CorpusError('PRIVATE_CANARY\x1b[2J')
    monkeypatch.setattr(cli.tool, 'inspect', fail)
    monkeypatch.setattr(sys, 'argv', ['inspect-manifest', '--image', '/PRIVATE_CANARY/input', '--format', 'text'])
    assert cli.main() == 2
    output = capsys.readouterr()
    assert not output.err and 'PRIVATE_CANARY' not in output.out and '\x1b' not in output.out
    assert 'No valid inspection result was obtained.' in output.out


def test_text_worker_invocation_refused_before_entering_native_parser(monkeypatch, capsys):
    monkeypatch.setattr(cli.tool, 'worker', lambda: pytest.fail('Native worker should not run'))
    monkeypatch.setattr(sys, 'argv', ['inspect-manifest', '--worker', '--format', 'text'])
    assert cli.main() == 2
    output = capsys.readouterr(); assert not output.out and not output.err


def test_bad_text_envelope_is_refused_before_private_export(monkeypatch, capsys):
    value = observed(); value['claim_signature'] = 'PRIVATE_CANARY'
    monkeypatch.setattr(cli.tool, 'inspect', lambda _: (value, {'PRIVATE_CANARY': 'raw'}))
    monkeypatch.setattr(cli.tool, 'save_private', lambda *_: pytest.fail('Invalid result must not be exported'))
    monkeypatch.setattr(sys, 'argv', ['inspect-manifest', '--image', 'image.png',
                                     '--format', 'text', '--private-report', '/PRIVATE_CANARY/result'])
    assert cli.main() == 2
    output = capsys.readouterr()
    assert 'No valid inspection result was obtained.' in output.out
    assert 'PRIVATE_CANARY' not in output.out and not output.err
