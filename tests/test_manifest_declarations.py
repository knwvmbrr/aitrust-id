"""Bound recorded declarations without inferring AI origin or borrowing evidence."""
import copy
import builtins
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import pytest

from protocol.corpus import CorpusError
from tools import manifest_inspection as parser
from tools import manifest_declarations as d

ROOT = Path(__file__).resolve().parents[1]
ACTIVE = 'urn:uuid:synthetic-active'
PREFIX = 'self#jumbf=/c2pa/' + ACTIVE


def report(actions=None):
    return {'active_manifest': ACTIVE, 'manifests': {ACTIVE: {'assertions': [
        {'label': 'c2pa.actions.v2', 'created': True, 'kind': 'Cbor', 'data': {
            'allActionsIncluded': False, 'actions': actions if actions is not None else [
                {'action': 'c2pa.created', 'digitalSourceType': d.GENERATIVE_CREATION}]}}]}},
        'validation_results': {'activeManifest': {'success': [
            {'code': 'claimSignature.validated', 'url': PREFIX + '/c2pa.signature'},
            {'code': 'assertion.dataHash.match', 'url': PREFIX + '/c2pa.assertions/c2pa.hash.data'},
            {'code': 'assertion.hashedURI.match', 'url': PREFIX + '/c2pa.assertions/c2pa.actions.v2'}],
            'informational': [{'code': 'signingCredential.ocsp.skipped'}],
            'failure': [{'code': 'signingCredential.untrusted', 'url': PREFIX + '/c2pa.signature'}]}}}


def observe(raw):
    return d.from_inspection(parser.summarize(raw, b'hand-built synthetic pixels'), raw)


def assert_no_origin(result):
    assert result['tags'] == [] and result['ai_origin'] == 'unknown'
    for field in ['content_truth_established', 'author_identity_established',
                  'independent_accuracy_evidence', 'production_assertion', 'complete_history_verified']:
        assert result[field] is False


def test_bound_creation_is_a_recorded_statement_not_fa_or_truth():
    result = observe(report())
    assert result['declaration_state'] == 'OBSERVED'
    assert result['declarations'] == [{'kind': 'generative_ai_creation_declared', 'action': 'c2pa.created',
                                        'assertion_index': 0, 'action_index': 0}]
    assert result['signer_trust'] == 'untrusted' and result['revocation'] == 'unknown_skipped'
    assert_no_origin(result)


def test_generation_and_generative_edit_are_compatible_not_a_human_sequence():
    result = observe(report([{'action': 'c2pa.created', 'digitalSourceType': d.GENERATIVE_CREATION},
                             {'action': 'c2pa.edited', 'digitalSourceType': d.GENERATIVE_EDIT}]))
    assert result['declaration_state'] == 'OBSERVED' and len(result['declarations']) == 2
    assert 'A creation action claims generative AI use.' in d.text_result(result)
    assert 'An editing action claims generative AI use.' in d.text_result(result)
    assert_no_origin(result)


@pytest.mark.parametrize('source', [None, 'http://cv.iptc.org/newscodes/digitalsourcetype/softwareImage',
    'http://cv.iptc.org/newscodes/digitalsourcetype/digitalCapture',
    'http://cv.iptc.org/newscodes/digitalsourcetype/humanEdits',
    'http://cv.iptc.org/newscodes/digitalsourcetype/algorithmicallyEnhanced',
    'http://cv.iptc.org/newscodes/digitalsourcetype/compositeSynthetic',
    d.GENERATIVE_CREATION.replace('http:', 'https:'), d.GENERATIVE_CREATION + ' ',
    d.GENERATIVE_CREATION.replace('trained', 'Trained'), 'org.example.ai',
    'PRIVATE_CANARY\x1b[2J'])
def test_absent_imprecise_or_custom_source_never_becomes_ai_evidence(source):
    action = {'action': 'c2pa.created'}
    if source is not None: action['digitalSourceType'] = source
    result = observe(report([action]))
    assert result['declaration_state'] == 'UNKNOWN' and result['declarations'] == []
    assert_no_origin(result)
    assert 'PRIVATE_CANARY' not in json.dumps(result)


def test_custom_action_cannot_reuse_a_known_source_type():
    result = observe(report([{'action': 'PRIVATE_CANARY.custom', 'digitalSourceType': d.GENERATIVE_CREATION}]))
    assert result['declaration_state'] == 'UNKNOWN' and result['declarations'] == []
    assert 'PRIVATE_CANARY' not in d.text_result(result)


def test_ingredient_manifest_and_ingredient_assertion_cannot_supply_active_origin():
    raw = report([{'action': 'c2pa.created', 'digitalSourceType': 'softwareImage'}])
    raw['manifests']['urn:uuid:ingredient'] = copy.deepcopy(raw['manifests'][ACTIVE])
    raw['manifests']['urn:uuid:ingredient']['assertions'][0]['data']['actions'][0]['digitalSourceType'] = d.GENERATIVE_CREATION
    raw['manifests'][ACTIVE]['assertions'].append({'label': 'c2pa.ingredient.v3',
        'data': {'digitalSourceType': d.GENERATIVE_CREATION, 'private_metadata': 'PRIVATE_CANARY'}})
    result = observe(raw)
    assert result['declaration_state'] == 'UNKNOWN' and result['declarations'] == []
    assert 'PRIVATE_CANARY' not in json.dumps(result)


@pytest.mark.parametrize('index,uri', [(0, 'self#jumbf=/c2pa/urn:uuid:ingredient/c2pa.signature'),
    (1, 'self#jumbf=/c2pa/urn:uuid:ingredient/c2pa.assertions/c2pa.hash.data'),
    (2, 'self#jumbf=/c2pa/urn:uuid:ingredient/c2pa.assertions/c2pa.actions.v2'),
    (2, PREFIX + '/c2pa.assertions/c2pa.actions.v2__1'), (2, 'https://example.invalid/c2pa.actions.v2')])
def test_status_success_must_name_this_active_signature_image_and_assertion(index, uri):
    raw = report(); raw['validation_results']['activeManifest']['success'][index]['url'] = uri
    result = observe(raw)
    assert result['declaration_state'] == 'UNKNOWN' and result['declarations'] == []


def test_instance_requires_its_own_exact_hashed_uri_success():
    raw = report(); raw['manifests'][ACTIVE]['assertions'][0]['instance'] = 1
    assert observe(raw)['declaration_state'] == 'UNKNOWN'
    raw['validation_results']['activeManifest']['success'][2]['url'] += '__1'
    assert observe(raw)['declaration_state'] == 'OBSERVED'


@pytest.mark.parametrize('code,uri', [('assertion.dataHash.mismatch', PREFIX + '/c2pa.assertions/c2pa.hash.data'),
    ('claimSignature.mismatch', PREFIX + '/c2pa.signature'),
    ('assertion.hashedURI.mismatch', PREFIX + '/c2pa.assertions/c2pa.actions.v2'),
    ('future.uninterpretedFailure', PREFIX + '/c2pa.signature')])
def test_failure_wins_over_success_without_erasing_inspection_axes(code, uri):
    raw = report(); raw['validation_results']['activeManifest']['failure'].append({'code': code, 'url': uri})
    result = observe(raw)
    assert result['declaration_state'] == 'UNKNOWN' and result['declarations'] == []
    if code == 'assertion.dataHash.mismatch': assert result['asset_binding'] == 'mismatched' and result['claim_signature'] == 'matched'


def test_revoked_signer_remains_visible_even_when_a_bound_declaration_is_read():
    raw = report(); raw['validation_results']['activeManifest']['failure'].append({'code': 'signingCredential.ocsp.revoked'})
    result = observe(raw)
    assert result['declaration_state'] == 'OBSERVED' and result['revocation'] == 'reported_revoked'
    assert 'Reported revoked; this credential is not cleared.' in d.text_result(result)
    assert_no_origin(result)


@pytest.mark.parametrize('field', ['templates', 'changes', 'changed', 'related'])
def test_unresolved_template_region_and_related_scope_is_not_silently_promoted(field):
    raw = report(); data = raw['manifests'][ACTIVE]['assertions'][0]['data']
    if field == 'templates': data[field] = [{'action': '*', 'digitalSourceType': d.GENERATIVE_CREATION}]
    else: data['actions'][0][field] = []
    result = observe(raw)
    assert result['declaration_state'] == 'UNKNOWN' and result['declarations'] == []


def test_nonregional_metadata_and_unrelated_parameters_do_not_change_default_declaration():
    raw = report(); data = raw['manifests'][ACTIVE]['assertions'][0]['data']
    data['metadata'] = {'dateTime': 'PRIVATE_CANARY', 'reviewRatings': []}
    data['actions'][0]['parameters'] = {'org.example.description': 'PRIVATE_CANARY'}
    result = observe(raw)
    assert result['declaration_state'] == 'OBSERVED'
    assert 'PRIVATE_CANARY' not in json.dumps(result) + d.text_result(result)
    assert_no_origin(result)


@pytest.mark.parametrize('region', [{}, None, [], 'PRIVATE_CANARY\x1b[2J https://example.invalid/location'])
def test_assertion_region_scope_is_unknown_even_with_bound_creation_and_safe_axes(region):
    raw = report(); raw['manifests'][ACTIVE]['assertions'][0]['data']['metadata'] = {'regionOfInterest': region}
    result = observe(raw)
    assert result['declaration_state'] == 'UNKNOWN' and result['declarations'] == []
    assert result['reason'] == 'assertion_region_of_interest_not_supported'
    text = d.text_result(result)
    assert 'The declaration has a region-of-interest scope; this profile cannot interpret it.' in text
    assert 'PRIVATE_CANARY' not in json.dumps(result) + text and '\x1b' not in text
    assert result['asset_binding'] == result['claim_signature'] == 'matched'
    assert_no_origin(result)


@pytest.mark.parametrize('value', [None, [], True, 'PRIVATE_CANARY'])
@pytest.mark.parametrize('field', ['metadata', 'parameters'])
def test_malformed_metadata_or_action_parameters_are_refused_without_echo(field, value):
    raw = report(); data = raw['manifests'][ACTIVE]['assertions'][0]['data']
    if field == 'metadata': data[field] = value
    else: data['actions'][0][field] = value
    with pytest.raises(CorpusError) as error: observe(raw)
    assert 'PRIVATE_CANARY' not in str(error.value)


@pytest.mark.parametrize('related', [None, [], {}, 'PRIVATE_CANARY\x1b[2J https://example.invalid/other'])
def test_unresolved_related_assertions_are_not_promoted_to_whole_asset_declarations(related):
    raw = report(); raw['manifests'][ACTIVE]['assertions'][0]['data']['actions'][0]['parameters'] = {'relatedAssertions': related}
    result = observe(raw)
    assert result['declaration_state'] == 'UNKNOWN' and result['declarations'] == []
    assert result['reason'] == 'related_assertions_not_supported'
    text = d.text_result(result)
    assert 'The action refers to other assertions; this profile cannot interpret their scope.' in text
    assert 'PRIVATE_CANARY' not in json.dumps(result) + text and '\x1b' not in text
    assert_no_origin(result)


@pytest.mark.parametrize('created', [None, False, 'true'])
def test_gathered_or_ambiguous_attribution_does_not_become_the_signers_declaration(created):
    raw = report(); raw['manifests'][ACTIVE]['assertions'][0]['created'] = created
    assert observe(raw)['declaration_state'] == 'UNKNOWN'


def test_multiple_inception_actions_are_unsupported_not_contradictory_origin():
    raw = report([{'action': 'c2pa.created', 'digitalSourceType': d.GENERATIVE_CREATION},
                  {'action': 'c2pa.created', 'digitalSourceType': 'http://cv.iptc.org/newscodes/digitalsourcetype/digitalCapture'}])
    result = observe(raw)
    assert result['declaration_state'] == 'UNKNOWN' and result['declarations'] == []
    assert result['reason'] == 'multiple_inception_actions_not_supported'
    text = d.text_result(result)
    assert 'The record contains multiple creation/opening actions; this profile cannot interpret it.' in text
    assert 'conflict' not in text.lower() and 'contradict' not in text.lower()
    assert 'No supported, bound action declaration was established.' in text
    assert_no_origin(result)


def test_claimed_complete_history_is_not_verified_complete_history():
    raw = report(); raw['manifests'][ACTIVE]['assertions'][0]['data']['allActionsIncluded'] = True
    result = observe(raw)
    assert result['all_actions_included_claim'] is True and result['complete_history_verified'] is False


def test_private_names_locations_descriptions_and_terminal_strings_are_never_echoed():
    raw = report(); marker = 'PRIVATE_CANARY\x1b[2J https://example.invalid/location'
    raw['manifests'][ACTIVE].update(title=marker, author=marker, location=marker)
    raw['manifests'][ACTIVE]['assertions'][0]['data']['actions'][0].update(description=marker, softwareAgent={'name': marker})
    result = observe(raw)
    for text in [json.dumps(result), d.text_result(result)]:
        assert 'PRIVATE_CANARY' not in text and '\x1b' not in text and 'https://' not in text


@pytest.mark.parametrize('mutation', [
    lambda raw: raw['manifests'][ACTIVE].update(assertions=[{}] * 33),
    lambda raw: raw['manifests'][ACTIVE]['assertions'][0]['data'].update(actions=[{}] * 129),
    lambda raw: raw['manifests'][ACTIVE]['assertions'][0]['data'].update(allActionsIncluded='true'),
    lambda raw: raw['manifests'][ACTIVE]['assertions'][0]['data'].update(allActionsIncluded=None),
    lambda raw: raw['manifests'][ACTIVE]['assertions'][0]['data']['actions'][0].update(digitalSourceType={}),
    lambda raw: raw['manifests'][ACTIVE]['assertions'][0]['data']['actions'][0].update(digitalSourceType=None),
    lambda raw: raw['manifests'][ACTIVE]['assertions'][0]['data']['actions'][0].update(action=[]),
    lambda raw: raw['manifests'][ACTIVE]['assertions'][0].update(instance=True),
    lambda raw: raw['manifests'][ACTIVE]['assertions'].append(copy.deepcopy(raw['manifests'][ACTIVE]['assertions'][0])),
])
def test_malformed_or_oversized_action_data_refused(mutation):
    raw = report(); mutation(raw)
    with pytest.raises(CorpusError): observe(raw)


def test_missing_manifest_and_native_failure_are_unknown_or_unavailable_never_human():
    minimum = {'state': 'NOT_FOUND', 'method': parser.METHOD, 'tags': [], 'asset_sha256': 'a' * 64,
               'asset_bytes': 1, 'revocation': 'not_applicable', 'content_truth_established': False, 'author_identity_established': False}
    result = d.from_inspection(minimum, None)
    assert result['declaration_state'] == 'UNKNOWN'; assert_no_origin(result)
    result = d.unavailable(); assert result['declaration_state'] == 'UNAVAILABLE'; assert_no_origin(result)


def test_frozen_declarations_are_authored_statements_not_origin_labels():
    folder = ROOT/'tests/fixtures/c2pa-declarations-2026'
    fixture = json.loads((folder/'manifest.json').read_text())
    assert fixture['fixture_only'] and not fixture['private_keys_written'] and not fixture['independent_accuracy_evidence']
    assert fixture['generator_sha256'] == hashlib.sha256((folder/'generate.py').read_bytes()).hexdigest()
    for name, expected in fixture['files'].items():
        raw = (folder/name).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == expected
        parser.png_container(raw)


def cli_module():
    spec = importlib.util.spec_from_file_location('declaration_cli', ROOT / 'scripts/inspect-manifest.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module


def test_optional_profile_cli_and_worker_refusal(monkeypatch, capsys):
    cli = cli_module(); raw = report()
    monkeypatch.setattr(cli.tool, 'inspect', lambda _: (parser.summarize(raw, b'pixels'), raw))
    monkeypatch.setattr(sys, 'argv', ['inspect-manifest', '--image', 'PRIVATE_CANARY', '--profile', 'action-declarations-v1', '--format', 'text'])
    assert cli.main() == 0
    output = capsys.readouterr(); assert not output.err and 'PRIVATE_CANARY' not in output.out
    assert 'A creation action claims generative AI use.' in output.out
    monkeypatch.setattr(cli.tool, 'worker', lambda: pytest.fail('Profile must not run in worker protocol'))
    monkeypatch.setattr(sys, 'argv', ['inspect-manifest', '--worker', '--profile', 'action-declarations-v1'])
    assert cli.main() == 2
    output = capsys.readouterr(); assert not output.out and not output.err


def test_failed_profile_returns_controlled_unavailable_without_native_error(monkeypatch, capsys):
    cli = cli_module()
    def fail(_): raise CorpusError('PRIVATE_CANARY')
    monkeypatch.setattr(cli.tool, 'inspect', fail)
    monkeypatch.setattr(sys, 'argv', ['inspect-manifest', '--image', '/PRIVATE_CANARY', '--profile', 'action-declarations-v1'])
    assert cli.main() == 2
    output = capsys.readouterr(); value = json.loads(output.out)
    assert value['declaration_state'] == 'UNAVAILABLE' and 'PRIVATE_CANARY' not in output.out and not output.err


@pytest.mark.parametrize('failure', [ImportError('PRIVATE_CANARY'), SyntaxError('PRIVATE_CANARY')])
def test_optional_profile_import_failure_is_contained_before_parsing(monkeypatch, capsys, failure):
    cli = cli_module(); original = builtins.__import__
    def controlled_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == 'tools' and 'manifest_declarations' in fromlist:
            raise failure
        return original(name, globals, locals, fromlist, level)
    monkeypatch.setattr(builtins, '__import__', controlled_import)
    raw = report()
    monkeypatch.setattr(cli.tool, 'inspect', lambda _: (parser.summarize(raw, b'pixels'), raw))
    monkeypatch.setattr(sys, 'argv', ['inspect-manifest', '--image', 'input.png'])
    assert cli.main() == 0
    assert json.loads(capsys.readouterr().out)['state'] == 'OBSERVED'
    monkeypatch.setattr(cli.tool, 'inspect', lambda _: pytest.fail('Broken profile must refuse before native parsing'))
    monkeypatch.setattr(sys, 'argv', ['inspect-manifest', '--image', '/PRIVATE_CANARY', '--profile', 'action-declarations-v1', '--format', 'text'])
    assert cli.main() == 2
    output = capsys.readouterr()
    assert 'No valid declaration inspection result' in output.out
    assert 'PRIVATE_CANARY' not in output.out and not output.err
