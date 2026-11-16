"""Opt-in recorded action declarations, not an AI-origin detector or tag issuer."""
import hashlib
from pathlib import Path
import re

from protocol.corpus import CorpusError
from tools import manifest_inspection as parser

PROFILE = 'attached-png-action-declarations/1.0.0'
GENERATIVE_CREATION = 'http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia'
GENERATIVE_EDIT = 'http://cv.iptc.org/newscodes/digitalsourcetype/compositeWithTrainedAlgorithmicMedia'
PAIRS = {('c2pa.created', GENERATIVE_CREATION): 'generative_ai_creation_declared',
         ('c2pa.edited', GENERATIVE_EDIT): 'generative_ai_edit_declared'}
LABELS = {'c2pa.actions', 'c2pa.actions.v2'}
MAX_ASSERTIONS = 32
MAX_ACTIONS = 128
_HASH = re.compile(r'[a-f0-9]{64}\Z')
_MANIFEST = re.compile(r'urn:(?:uuid|c2pa):[A-Za-z0-9:._-]{1,180}\Z')


def require(value):
    if not value:
        raise CorpusError('Unsupported bounded action-declaration input.')


def envelope(inspection):
    """Copy a fixed minimal producer profile; never echo SDK metadata."""
    require(type(inspection) is dict and inspection.get('method') == parser.METHOD
            and inspection.get('tags') == [] and type(inspection.get('tags')) is list
            and inspection.get('content_truth_established') is False
            and inspection.get('author_identity_established') is False)
    state = inspection.get('state')
    require(state in ('OBSERVED', 'NOT_FOUND', 'UNAVAILABLE'))
    result = {'profile': PROFILE, 'profile_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'method': parser.METHOD, 'state': state, 'declaration_state': 'UNKNOWN',
        'reason': 'no_attached_manifest' if state == 'NOT_FOUND' else 'no_supported_declaration',
        'declarations': [], 'uninterpreted_action_count': 0, 'all_actions_included_claim': None,
        'complete_history_verified': False, 'scope': 'active_manifest_recorded_actions_only',
        'ai_origin': 'unknown', 'tags': [], 'content_truth_established': False,
        'author_identity_established': False, 'independent_accuracy_evidence': False,
        'production_assertion': False}
    if state != 'UNAVAILABLE':
        require(type(inspection.get('asset_sha256')) is str and _HASH.fullmatch(inspection['asset_sha256'])
                and type(inspection.get('asset_bytes')) is int
                and 0 < inspection['asset_bytes'] <= parser.MAX_ASSET_BYTES)
        result.update(asset_sha256=inspection['asset_sha256'], asset_bytes=inspection['asset_bytes'])
    if state == 'OBSERVED':
        for field, values in [('asset_binding', ('matched', 'mismatched', 'unknown')),
                              ('claim_signature', ('matched', 'mismatched', 'unknown')),
                              ('signer_trust', ('reported_trusted', 'untrusted', 'unknown')),
                              ('revocation', ('reported_revoked', 'unknown_skipped'))]:
            require(type(inspection.get(field)) is str and inspection[field] in values)
            result[field] = inspection[field]
    elif state == 'NOT_FOUND':
        require(inspection.get('revocation') == 'not_applicable')
        result['revocation'] = 'not_applicable'
    else:
        result.update(declaration_state='UNAVAILABLE', reason='inspection_unavailable_or_unsupported')
    return result


def unavailable():
    return envelope({'state': 'UNAVAILABLE', 'method': parser.METHOD, 'tags': [],
                     'content_truth_established': False, 'author_identity_established': False})


def from_inspection(inspection, report):
    """Interpret only the same bounded inspector call's paired private report.

    This function does not authenticate arbitrary caller JSON. The CLI obtains
    both arguments together from the pinned, resource-bounded file inspector.
    """
    result = envelope(inspection)
    if result['state'] != 'OBSERVED':
        require(report is None)
        return result
    require(type(report) is dict and type(report.get('active_manifest')) is str)
    active = report['active_manifest']; require(_MANIFEST.fullmatch(active))
    require(type(report.get('manifests')) is dict and active in report['manifests'])
    manifest = report['manifests'][active]; require(type(manifest) is dict)
    assertions = manifest.get('assertions', [])
    require(type(assertions) is list and len(assertions) <= MAX_ASSERTIONS)
    validation = report.get('validation_results'); require(type(validation) is dict)
    groups = validation.get('activeManifest'); parser.status_groups(groups)
    prefix = 'self#jumbf=/c2pa/' + active

    def exact_success(code, uri):
        return (any(row.get('code') == code and row.get('url') == uri
                    for row in groups.get('success', []))
                and not any(row.get('url') == uri and row.get('code') not in
                            {'signingCredential.untrusted', 'signingCredential.ocsp.revoked'}
                            for row in groups.get('failure', [])))

    if result['asset_binding'] != 'matched' or result['claim_signature'] != 'matched':
        result['reason'] = 'asset_or_signature_not_matched'; return result
    if not exact_success('claimSignature.validated', prefix + '/c2pa.signature'):
        result['reason'] = 'active_signature_binding_not_proven'; return result
    if not any(exact_success('assertion.dataHash.match', prefix + '/c2pa.assertions/c2pa.hash.data' + suffix)
               for suffix in ['', *['__' + str(i) for i in range(1, MAX_ASSERTIONS)]]):
        result['reason'] = 'active_image_binding_not_proven'; return result

    declarations, histories, instances = [], [], set()
    total_actions = inception_actions = uninterpreted = 0
    for assertion_index, assertion in enumerate(assertions):
        require(type(assertion) is dict and type(assertion.get('label')) is str)
        if assertion['label'] not in LABELS:
            continue
        require(set(assertion) <= {'label', 'data', 'instance', 'kind', 'created'})
        instance = assertion.get('instance', 0)
        require(type(instance) is int and 0 <= instance < MAX_ASSERTIONS)
        identity = (assertion['label'], instance)
        require(identity not in instances); instances.add(identity)
        if assertion.get('created') is not True:
            result['reason'] = 'action_attribution_not_supported'; return result
        if assertion.get('kind') not in (None, 'Cbor'):
            result['reason'] = 'action_encoding_not_supported'; return result
        uri = prefix + '/c2pa.assertions/' + assertion['label'] + ('__' + str(instance) if instance else '')
        if not exact_success('assertion.hashedURI.match', uri):
            result['reason'] = 'active_action_assertion_binding_not_proven'; return result
        data = assertion.get('data'); require(type(data) is dict)
        require(set(data) <= {'actions', 'allActionsIncluded', 'templates', 'metadata', 'softwareAgents'})
        if 'metadata' in data:
            require(type(data['metadata']) is dict)
            if 'regionOfInterest' in data['metadata']:
                result['reason'] = 'assertion_region_of_interest_not_supported'; return result
        if 'templates' in data:
            result['reason'] = 'action_templates_not_supported'; return result
        complete = data.get('allActionsIncluded')
        require('allActionsIncluded' not in data or type(complete) is bool); histories.append(complete)
        actions = data.get('actions')
        require(type(actions) is list and 1 <= len(actions) <= MAX_ACTIONS)
        total_actions += len(actions); require(total_actions <= MAX_ACTIONS)
        for action_index, action in enumerate(actions):
            require(type(action) is dict and type(action.get('action')) is str and 1 <= len(action['action']) <= 128)
            if any(field in action for field in ('changes', 'changed', 'related')):
                result['reason'] = 'regional_or_related_actions_not_supported'; return result
            if 'parameters' in action:
                require(type(action['parameters']) is dict)
                if 'relatedAssertions' in action['parameters']:
                    result['reason'] = 'related_assertions_not_supported'; return result
            source_type = action.get('digitalSourceType')
            require('digitalSourceType' not in action or type(source_type) is str and 1 <= len(source_type) <= 256)
            if action['action'] in ('c2pa.created', 'c2pa.opened'):
                inception_actions += 1
            kind = PAIRS.get((action['action'], source_type))
            if kind is None:
                uninterpreted += 1; continue
            declarations.append({'kind': kind, 'action': action['action'],
                                 'assertion_index': assertion_index, 'action_index': action_index})
    result['uninterpreted_action_count'] = uninterpreted
    if histories:
        result['all_actions_included_claim'] = False if False in histories else True if all(x is True for x in histories) else None
    if inception_actions > 1:
        result.update(declaration_state='UNKNOWN', reason='multiple_inception_actions_not_supported')
        return result
    if any(row['code'] not in {'signingCredential.untrusted', 'signingCredential.ocsp.revoked'}
           for row in groups.get('failure', [])):
        result['reason'] = 'other_active_validation_failure'; return result
    if declarations:
        result.update(declaration_state='OBSERVED', reason='bound_recorded_action_declarations', declarations=declarations)
    return result


def text_result(result):
    """Render controlled words only; never print the report's embedded strings."""
    from tools.manifest_presentation import text_result as inspection_text
    require(type(result) is dict and result.get('profile') == PROFILE
            and result.get('ai_origin') == 'unknown'
            and result.get('complete_history_verified') is False
            and result.get('production_assertion') is False)
    state = result.get('declaration_state')
    require(state in ('OBSERVED', 'UNKNOWN', 'UNAVAILABLE'))
    rows = result.get('declarations'); require(type(rows) is list and len(rows) <= MAX_ACTIONS)
    counts = {'generative_ai_creation_declared': 0, 'generative_ai_edit_declared': 0}
    for row in rows:
        require(type(row) is dict and type(row.get('kind')) is str and row['kind'] in counts)
        counts[row['kind']] += 1
    require(bool(rows) == (state == 'OBSERVED'))
    lines = [inspection_text(result)]
    if state == 'OBSERVED':
        if counts['generative_ai_creation_declared']:
            lines += ['Recorded declaration: A creation action claims generative AI use.']
        if counts['generative_ai_edit_declared']:
            lines += ['Recorded declaration: An editing action claims generative AI use.']
        lines += ['These are statements in the bound record, not independently established image origin.']
    elif state == 'UNKNOWN':
        lines += ['Recorded declaration: Unknown. No supported, bound action declaration was established.']
        if result.get('reason') == 'multiple_inception_actions_not_supported':
            lines += ['The record contains multiple creation/opening actions; this profile cannot interpret it.']
        elif result.get('reason') == 'assertion_region_of_interest_not_supported':
            lines += ['The declaration has a region-of-interest scope; this profile cannot interpret it.']
        elif result.get('reason') == 'related_assertions_not_supported':
            lines += ['The action refers to other assertions; this profile cannot interpret their scope.']
    else:
        lines += ['Recorded declaration: Unavailable.']
    lines += ['Only supported active-record actions are inspected; complete history is not verified.']
    return '\n'.join(lines)
