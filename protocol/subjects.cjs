// Independent Node implementation of subject-v2. No redaction or classification.
const { normalizeNFC, NORMALIZATION_ID } = require('./normalization.cjs');
const { createHash } = require('node:crypto');
const digest = bytes => createHash('sha256').update(bytes).digest('hex');
function textSubject(text) {
  if (typeof text !== 'string' || [...text].length > 200_000) throw new Error('Invalid redacted text');
  for (const char of text) {
    const cp = char.codePointAt(0);
    if (cp >= 0xd800 && cp <= 0xdfff) throw new Error('Unpaired surrogate');
  }
  const normalized = normalizeNFC(text);
  return { sha256: digest(Buffer.from(normalized, 'utf8')), length: [...normalized].length,
    offset_unit: 'unicode_codepoint', modality: 'text', contract_version: 'subject-v2', normalization_id: NORMALIZATION_ID };
}
function codeSubject(bytes) {
  if (!Buffer.isBuffer(bytes) || bytes.length > 800_000) throw new Error('Invalid code bytes');
  return { sha256: digest(bytes), length: bytes.length, offset_unit: 'byte',
    modality: 'code', contract_version: 'subject-v1' };
}
module.exports = { textSubject, codeSubject };
