// Frozen Unicode tables; data license: eval/vectors/unicode/LICENSE.txt.
const NORMALIZATION_ID = 'NFC-Unicode-15.0.0/v1';
const MAX_CODEPOINTS = 200_000;
const ccc = cp => TABLES.combining_classes[cp] || 0;
function decompose(cp, out) {
 if (cp >= 0xac00 && cp < 0xac00 + 11172) {
  const index = cp - 0xac00;
  out.push(0x1100 + Math.floor(index / 588), 0x1161 + Math.floor((index % 588) / 28));
  if (index % 28) out.push(0x11a7 + index % 28);
 } else if (Object.hasOwn(TABLES.canonical_decompositions, cp)) {
  for (const child of TABLES.canonical_decompositions[cp]) decompose(child, out);
 } else out.push(cp);
}
function pair(a, b) {
 if (a >= 0x1100 && a < 0x1113 && b >= 0x1161 && b < 0x1176)
  return 0xac00 + ((a - 0x1100) * 21 + b - 0x1161) * 28;
 if (a >= 0xac00 && a < 0xac00 + 11172 && (a - 0xac00) % 28 === 0 && b >= 0x11a8 && b < 0x11c3)
  return a + b - 0x11a7;
 return TABLES.compositions[a + ',' + b];
}
function normalizeNFC(text) {
 if (typeof text !== 'string' || text.length > MAX_CODEPOINTS * 2) throw Error('Invalid Unicode text');
 const decomposed = [];
 let count = 0;
 for (const char of text) {
  if (++count > MAX_CODEPOINTS) throw Error('Oversized Unicode text');
  const cp = char.codePointAt(0);
  if (cp >= 0xd800 && cp <= 0xdfff) throw Error('Unpaired surrogate');
  decompose(cp, decomposed);
 }
 const ordered = [], marks = [];
 function flush() { marks.sort((a,b) => ccc(a)-ccc(b)); for (const cp of marks) ordered.push(cp); marks.length=0; }
 for (const cp of decomposed) {
  if (ccc(cp)) marks.push(cp); else { flush(); ordered.push(cp); }
 }
 flush();
 const output = [];
 let starter = null, previous = 0;
 for (const cp of ordered) {
  const current = ccc(cp);
  const composed = starter !== null && (previous === 0 || previous < current) ? pair(output[starter], cp) : undefined;
  if (composed !== undefined) output[starter] = composed;
  else { if (current === 0) starter=output.length; output.push(cp); previous=current; }
 }
 return output.map(cp => String.fromCodePoint(cp)).join('');
}
