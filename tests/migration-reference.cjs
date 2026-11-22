// Independent reference for TRUSTED published canonical vectors only.
// It deliberately does not stringify JSON: JS cannot preserve all JSON numbers.
// This is not a validator for private/untrusted records or a supported CLI.
'use strict';
const fs = require('node:fs');
const raw = fs.readFileSync(0, 'utf8');
if (Buffer.byteLength(raw) > 2 * 1024 * 1024) throw Error('Vector bound');
const target = process.argv[2];
const parsed = JSON.parse(raw);
if (!['0.1.0', '0.2.0'].includes(target) || target === parsed.spec_version ||
    !['0.1.0', '0.2.0'].includes(parsed.spec_version) ||
    Object.hasOwn(parsed, 'signature') || !parsed.evaluator?.preprocessing) throw Error('Unsupported vector');
// Canonical JSON has no inter-token whitespace. Scan strings and nesting rather
// than matching nested members or words in string values.
let depth = 0, replacement = null;
for (let i = 0; i < raw.length; i++) {
  const c = raw[i];
  if (c === '{' || c === '[') depth++;
  else if (c === '}' || c === ']') depth--;
  else if (c === '"') {
    const start = i++;
    while (i < raw.length) { if (raw[i] === '\\') i += 2; else if (raw[i] === '"') break; else i++; }
    const end = i + 1;
    if (depth === 1 && raw.slice(start, end) === '"spec_version"' && raw[end] === ':') {
      const from = end + 1, expected = JSON.stringify(parsed.spec_version);
      if (replacement || raw.slice(from, from + expected.length) !== expected) throw Error('Noncanonical vector');
      replacement = [from, from + expected.length];
    }
  }
}
if (!replacement) throw Error('Missing version');
process.stdout.write(raw.slice(0, replacement[0]) + JSON.stringify(target) + raw.slice(replacement[1]));
