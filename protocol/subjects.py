"""Versioned text/code subject primitives; does not redact or classify content."""
import hashlib
from protocol.normalization import normalize_nfc, NORMALIZATION_ID

CONTRACT_VERSION = 'subject-v2'
MAX_TEXT_CHARACTERS = 200_000
MAX_CODE_BYTES = 800_000


def text_subject(redacted_text):
    """Hash already-redacted text after NFC, with Unicode code-point offsets."""
    if not isinstance(redacted_text, str) or len(redacted_text) > MAX_TEXT_CHARACTERS:
        raise ValueError('Invalid or oversized redacted text')
    normalized = normalize_nfc(redacted_text)
    try:
        raw = normalized.encode('utf-8', errors='strict')
    except UnicodeEncodeError:
        raise ValueError('Unpaired surrogate is not a Unicode scalar value') from None
    return {'sha256': hashlib.sha256(raw).hexdigest(), 'length': len(normalized),
            'offset_unit': 'unicode_codepoint', 'modality': 'text',
            'contract_version': CONTRACT_VERSION, 'normalization_id': NORMALIZATION_ID}


def code_subject(raw_bytes):
    """Hash exact code bytes; preserve encoding, whitespace, BOM and line endings."""
    if not isinstance(raw_bytes, bytes) or len(raw_bytes) > MAX_CODE_BYTES:
        raise ValueError('Invalid or oversized code bytes')
    return {'sha256': hashlib.sha256(raw_bytes).hexdigest(), 'length': len(raw_bytes),
            'offset_unit': 'byte', 'modality': 'code', 'contract_version': 'subject-v1'}
