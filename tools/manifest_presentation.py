"""Fixed, privacy-minimal wording for the existing PNG inspection observations."""
from protocol.corpus import CorpusError
from tools.manifest_inspection import METHOD

BINDING = {
    'matched': 'Matches the recorded image bytes.',
    'mismatched': 'Does not match the recorded image bytes.',
    'unknown': 'Not established by this inspection.',
}
SIGNATURE = {
    'matched': 'The record signature matches.',
    'mismatched': 'The record signature does not match.',
    'unknown': 'Not established by this inspection.',
}
TRUST = {
    'reported_trusted': 'Reported trusted by the configured trust store.',
    'untrusted': 'Not trusted by the configured trust store; this alone is not fraud.',
    'unknown': 'Not established by this inspection.',
}
REVOCATION = {
    'reported_revoked': 'Reported revoked; this credential is not cleared.',
    'unknown_skipped': 'Unknown. Online revocation checks are disabled.',
}


def choice(value, sentences):
    if type(value) is not str or value not in sentences:
        raise CorpusError('Unsupported inspection presentation state.')
    return sentences[value]


def text_result(result):
    """Never interpolate an SDK payload or caller-controlled metadata value."""
    if (type(result) is not dict or result.get('method') != METHOD
            or type(result.get('tags')) is not list or result['tags'] != []
            or result.get('content_truth_established') is not False
            or result.get('author_identity_established') is not False
            or result.get('independent_accuracy_evidence', False) is not False):
        raise CorpusError('Unsupported inspection presentation envelope.')
    if 'private_report_saved' in result and result['private_report_saved'] is not True:
        raise CorpusError('Unsupported private export state.')
    state = result.get('state')
    lines = ['AI TRUST ID - PNG evidence check', 'Method: ' + METHOD + ' (PNG only).']
    if state == 'OBSERVED':
        lines += ['An attached Content Credential was inspected.',
            'Image binding: ' + choice(result.get('asset_binding'), BINDING),
            'Record signature: ' + choice(result.get('claim_signature'), SIGNATURE),
            'Signer trust: ' + choice(result.get('signer_trust'), TRUST),
            'Revocation: ' + choice(result.get('revocation'), REVOCATION)]
    elif state == 'NOT_FOUND':
        if result.get('revocation') != 'not_applicable':
            raise CorpusError('Unsupported missing-manifest state.')
        lines += ['No attached Content Credential was found in this supported PNG.',
            'Image binding: Not available.', 'Record signature: Not available.',
            'Signer trust: Not available.', 'Revocation: Not applicable.']
    elif state == 'UNAVAILABLE':
        lines += ['No valid inspection result was obtained.',
            'Check the supported PNG input and optional pinned SDK installation.']
    else:
        raise CorpusError('Unsupported inspection presentation outcome.')
    lines += ['AI origin: Unknown. This method does not determine whether AI made or edited the image.',
        'No tag issued. Image contents and authorship are not verified.']
    if result.get('private_report_saved') is True:
        lines += ['Your explicitly requested full report was saved privately; it may contain identifying metadata.']
    return '\n'.join(lines)
