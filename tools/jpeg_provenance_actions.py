"""Minimal active-record projections. Report strings never become public prose.

The paired-code/URI approach follows manifest_declarations.py; this is an
independent JPEG profile, not a PNG dependency or an FA/PA adapter.
"""
import re
from tools.jpeg_provenance_io import need

PROFILE = 'jpeg-credential-actions/1.0.0'
PAIRS = {('c2pa.created', 'http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia'):
         'generative_creation_declared',
         ('c2pa.edited', 'http://cv.iptc.org/newscodes/digitalsourcetype/compositeWithTrainedAlgorithmicMedia'):
         'generative_edit_declared'}
FLAGS = {'tags': [], 'ai_origin': 'unknown', 'content_truth_established': False,
         'author_identity_established': False, 'complete_history_verified': False,
         'independent_accuracy_evidence': False, 'production_assertion': False}
REASONS = {'sdk_unavailable', 'sdk_platform_unsupported', 'sdk_pin_mismatch', 'sdk_preloaded',
           'source_changed', 'input_unavailable', 'input_changed', 'input_limit', 'metadata_limit',
           'unsupported_format', 'unsupported_variant', 'malformed_structure', 'trailing_data',
           'worker_deadline', 'worker_output_limit', 'worker_unavailable', 'report_limit',
           'report_unsupported', 'trust_input_unsupported', 'invalid_request'}


def base(state, reason):
    return {'profile': PROFILE, 'state': state, 'reason': reason,
            'asset_binding': 'unknown', 'claim_signature': 'unknown', 'signer_trust': 'unknown',
            'revocation': 'unknown_not_fetched', 'declaration_state': 'UNKNOWN', 'declarations': [],
            'uninterpreted_action_count': 0, 'all_actions_included_claim': None,
            'scope': 'active_manifest_recorded_actions_only', **{**FLAGS, 'tags': []}}


def unavailable(reason):
    return base('UNAVAILABLE', reason if reason in REASONS else 'worker_unavailable')


def project(report):
    """Only called on this invocation's pinned reader report, not imported JSON."""
    need(type(report) is dict, 'report_unsupported')
    active, manifests = report.get('active_manifest'), report.get('manifests')
    need(type(active) is str and re.fullmatch(r'urn:(?:uuid|c2pa):[A-Za-z0-9:._-]{1,180}', active)
         and type(manifests) is dict and 1 <= len(manifests) <= 32 and active in manifests,
         'report_unsupported')
    manifest = manifests[active]
    need(type(manifest) is dict, 'report_unsupported')
    assertions = manifest.get('assertions', [])
    need(type(assertions) is list and len(assertions) <= 32, 'report_unsupported')
    validation = report.get('validation_results')
    need(type(validation) is dict and type(validation.get('activeManifest')) is dict, 'report_unsupported')
    groups = validation['activeManifest']
    need(set(groups) <= {'success', 'failure', 'informational'}, 'report_unsupported')
    for key, rows in groups.items():
        need(type(rows) is list and len(rows) <= 2048, 'report_limit')
        for row in rows:
            need(type(row) is dict and type(row.get('code')) is str
                 and re.fullmatch(r'[A-Za-z0-9_.-]{1,100}', row['code'])
                 and ('url' not in row or type(row['url']) is str and len(row['url']) <= 1024),
                 'report_unsupported')
    success, failure = groups.get('success', []), groups.get('failure', [])
    prefix = 'self#jumbf=/c2pa/'+active
    def matches(code, uri):
        return any(r.get('code') == code and r.get('url') == uri for r in success)
    def bad(uri):
        return any(r.get('url') == uri and r['code'] not in
                   {'signingCredential.untrusted', 'signingCredential.ocsp.revoked'} for r in failure)
    def exact(code, uri):
        return matches(code, uri) and not bad(uri)
    def failed(code):
        return any(r['code'] == code for r in failure)
    result = base('OBSERVED', 'no_supported_bound_declaration')
    signature_uri = prefix+'/c2pa.signature'
    result['claim_signature'] = ('mismatched' if failed('claimSignature.mismatch') else
        'matched' if exact('claimSignature.validated', signature_uri) else 'unknown')
    image_uris = [prefix+'/c2pa.assertions/c2pa.hash.data'+('' if i == 0 else '__'+str(i)) for i in range(32)]
    result['asset_binding'] = ('mismatched' if failed('assertion.dataHash.mismatch') else
        'matched' if any(exact('assertion.dataHash.match', u) for u in image_uris) else 'unknown')
    result['signer_trust'] = ('untrusted' if failed('signingCredential.untrusted') else
        'sdk_reported_trusted' if any(r['code'] == 'signingCredential.trusted' and r.get('url') == signature_uri
                                    for r in success) else 'unknown')
    result['revocation'] = 'reported_revoked' if failed('signingCredential.ocsp.revoked') else 'unknown_not_fetched'
    # A claim can remain signed while its bytes or another active assertion fail.
    if result['asset_binding'] != 'matched' or result['claim_signature'] != 'matched':
        result['reason'] = 'asset_or_signature_not_matched'; return result
    if any(r['code'] not in {'signingCredential.untrusted', 'signingCredential.ocsp.revoked'} for r in failure):
        result['reason'] = 'other_active_validation_failure'; return result
    declarations, histories, seen = [], [], set()
    total = inception = uninterpreted = 0
    for ai, assertion in enumerate(assertions):
        need(type(assertion) is dict and type(assertion.get('label')) is str, 'report_unsupported')
        label = assertion['label']
        if label not in ('c2pa.actions', 'c2pa.actions.v2'):
            continue
        need(set(assertion) <= {'label', 'data', 'instance', 'kind', 'created'}, 'report_unsupported')
        instance = assertion.get('instance', 0)
        need(type(instance) is int and 0 <= instance < 32 and (label, instance) not in seen, 'report_unsupported')
        seen.add((label, instance))
        if assertion.get('created') is not True or assertion.get('kind') not in (None, 'Cbor'):
            result['reason'] = 'unsupported_action_attribution'; return result
        uri = prefix+'/c2pa.assertions/'+label+('' if instance == 0 else '__'+str(instance))
        if not exact('assertion.hashedURI.match', uri):
            result['reason'] = 'action_assertion_not_bound'; return result
        data = assertion.get('data')
        need(type(data) is dict and set(data) <= {'actions', 'allActionsIncluded', 'templates', 'metadata', 'softwareAgents'}, 'report_unsupported')
        if 'templates' in data:
            result['reason'] = 'unsupported_action_scope'; return result
        if 'metadata' in data:
            need(type(data['metadata']) is dict, 'report_unsupported')
            if 'regionOfInterest' in data['metadata']:
                result['reason'] = 'unsupported_action_scope'; return result
        history = data.get('allActionsIncluded')
        need('allActionsIncluded' not in data or type(history) is bool, 'report_unsupported')
        histories.append(history)
        actions = data.get('actions')
        need(type(actions) is list and 1 <= len(actions) <= 128, 'report_unsupported')
        total += len(actions); need(total <= 128, 'report_limit')
        for ji, action in enumerate(actions):
            need(type(action) is dict and type(action.get('action')) is str
                 and 1 <= len(action['action']) <= 128, 'report_unsupported')
            if any(k in action for k in ('changes', 'changed', 'related')):
                result['reason'] = 'unsupported_action_scope'; return result
            parameters = action.get('parameters', {})
            need(type(parameters) is dict, 'report_unsupported')
            if 'relatedAssertions' in parameters:
                result['reason'] = 'unsupported_action_scope'; return result
            source = action.get('digitalSourceType')
            need(source is None or type(source) is str and 0 < len(source) <= 256, 'report_unsupported')
            inception += action['action'] in ('c2pa.created', 'c2pa.opened')
            kind = PAIRS.get((action['action'], source))
            if kind:
                declarations.append({'kind': kind, 'assertion_index': ai, 'action_index': ji})
            else:
                uninterpreted += 1
    if inception > 1:
        result['reason'] = 'multiple_inception_actions'; return result
    result['uninterpreted_action_count'] = uninterpreted
    if histories:
        result['all_actions_included_claim'] = False if False in histories else True if all(x is True for x in histories) else None
    if declarations:
        result.update(declaration_state='OBSERVED', declarations=declarations, reason='bound_recorded_declarations')
    return result
