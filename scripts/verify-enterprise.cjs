/**
 * Enterprise offering independence gate.
 *
 *   node scripts/verify-enterprise.cjs
 *
 * The six organization offerings were built from one factory, so every panel
 * rendered the same text: "What it checks" read "Proposed organization-only
 * capability" on all six, and "Use this tag" was one shared sentence with no
 * steps. Six offerings that cannot describe themselves independently are one
 * offering with six names.
 *
 * This gate catches cloned descriptions. Uniqueness alone does not prove correctness. It also checks the honesty
 * rules that matter more than the differentiation: nothing may claim a price,
 * an SLA or a running service, and reviewable plans must not be presented as active services.
 */
const assert = require('node:assert');

const FIELDS = ['claim','method','inputs','outputs','validation','today','job','outcome','privacy','release'];
// Words that would promise something that does not exist.
const FORBIDDEN = [
  [/\bSLA\b/i, 'promises an SLA', ['limits','validation','today','supported']],
  [/\bguarantee[sd]?\b/i, 'promises a guarantee', []],
  [/\bcertified\b/i, 'claims certification', []],
  [/\bper (?:seat|user|month|year)\b/i, 'states pricing', []],
  [/\$\d/, 'states a price', []],
];

(async () => {
  const { enterpriseTags: tags, personTags } = await import('../site/src/catalog.js');
  const { usage } = await import('../site/src/usage.js');
  const fails = [];
  const fail = (m) => fails.push(m);

  assert.ok(tags.length >= 6, 'expected at least six organization offerings');

  // 1. Every differentiating field must be unique across offerings.
  for (const field of FIELDS) {
    const seen = new Map();
    for (const t of tags) {
      const v = t[field];
      if (v === undefined || v === null || String(v).trim() === '') {
        fail(`${t.code}: ${field} is empty — an offering must describe itself`);
        continue;
      }
      if (seen.has(v)) fail(`${field} is identical on ${seen.get(v)} and ${t.code} — clone text`);
      seen.set(v, t.code);
    }
  }

  // 2. Bullet lists must be per-offering, not a shared placeholder.
  for (const list of ['supported','limits']) {
    const seen = new Map();
    for (const t of tags) {
      const items = t[list] || [];
      if (items.length < 3) fail(`${t.code}: ${list} has ${items.length} item(s); needs at least 3`);
      const key = JSON.stringify(items);
      if (seen.has(key)) fail(`${list} is identical on ${seen.get(key)} and ${t.code}`);
      seen.set(key, t.code);
      for (const item of items) {
        if (/^Proposed organization-only capability$/.test(item)) {
          fail(`${t.code}: ${list} still contains the placeholder bullet`);
        }
      }
    }
  }

  // 3. "Use this tag" must differ per offering.
  const nexts = new Map();
  for (const t of tags) {
    const u = usage(t);
    if (u.available) fail(`${t.code}: reports itself available; no organization service exists`);
    if (nexts.has(u.next)) fail(`usage next-step identical on ${nexts.get(u.next)} and ${t.code}`);
    nexts.set(u.next, t.code);
  }

  // 4. Honesty: no promise of a thing that does not exist.
  for (const t of tags) {
    for (const [re, why, allowed] of FORBIDDEN) {
      for (const [field, value] of Object.entries(t)) {
        if (typeof value !== 'string' || allowed.includes(field)) continue;
        if (re.test(value)) fail(`${t.code}.${field} ${why}: ${JSON.stringify(value.slice(0, 90))}`);
      }
      for (const field of ['supported','limits']) {
        for (const item of t[field] || []) {
          if (allowed.includes(field)) continue;
          if (re.test(item)) fail(`${t.code}.${field} ${why}: ${JSON.stringify(item.slice(0, 90))}`);
        }
      }
    }
    // 5. No literal escape sequences leaking into user-visible copy.
    for (const [field, value] of Object.entries(t)) {
      if (typeof value !== 'string') continue;
      if (/\\u[0-9a-fA-F]{4}|\\n|\\t/.test(value)) {
        fail(`${t.code}.${field} contains a literal escape sequence in user-visible copy`);
      }
    }

    // 6. Status and price must stay honest about not being for sale.
    if (!/not set|no checkout|not available/i.test(t.price)) {
      fail(`${t.code}: price does not state that nothing is purchasable`);
    }
    if (t.proposed !== true) fail(`${t.code}: proposed must be true until a service exists`);
    // 6. Anything offered "today" must be free and present-tense available.
    if (!/Available now —/.test((t.supported || []).join(' ')) && !/Nothing runs|no implementation/i.test(t.today)) {
      fail(`${t.code}: claims something today but lists no "Available now —" capability`);
    }
    // 7. Every limits list must keep the free-tier guarantee.
    if (!(t.limits || []).some((l) => /personal detection and evidence remain free/i.test(l))) {
      fail(`${t.code}: limits no longer state that the personal workflow stays free`);
    }
  }

  // 8. Every cited scope feature must EXIST in the published scope, and must
  // not be the same set on two offerings. A feature list is the strongest
  // evidence that an offering was written from its own record rather than
  // from a template.
  const scope = JSON.parse(require('node:fs').readFileSync('docs/master-scope.json','utf8'));
  const known = new Set(scope.records.map((r) => r.id));
  const seenFeatures = new Map();
  for (const t of tags) {
    if (!t.features || t.features.length < 2) {
      fail(`${t.code}: cites ${(t.features||[]).length} scope record(s); an offering grounded in the scope cites more than its own id`);
    }
    if (!t.features.includes(t.scopeId)) {
      fail(`${t.code}: does not cite its own scope record ${t.scopeId}`);
    }
    for (const id of t.features || []) {
      if (!known.has(id)) fail(`${t.code}: cites ${id}, which is not in docs/master-scope.json`);
    }
    const key = JSON.stringify([...(t.features||[])].sort());
    if (seenFeatures.has(key)) fail(`feature set identical on ${seenFeatures.get(key)} and ${t.code}`);
    seenFeatures.set(key, t.code);
  }

  // 9. Offerings must not borrow a person tag's validation text.
  for (const field of ['validation','privacy','release','claim','method']) {
    const personText = new Set(personTags.map((t) => t[field]));
    for (const t of tags) {
      if (personText.has(t[field])) fail(`${t.code}: reuses a person tag's ${field} text`);
    }
  }

  // Check the claims most likely to confuse a reader, against actual interfaces.
  const fs = require('node:fs');
  const manifest = JSON.parse(fs.readFileSync('extension/manifest.json','utf8'));
  const fleet = tags.find(t=>t.id==='fleet');
  for (const script of manifest.content_scripts || []) for (const match of script.matches || []) {
    if (!fleet.today.includes(new URL(match.replace('*','')).hostname)) fail('FLEET omits content-script page access');
  }
  for (const host of manifest.host_permissions || []) {
    if (!fleet.today.includes(new URL(host.replace('*','')).host)) fail('FLEET omits a permitted gateway host');
  }
  if (/whole surface|loopback (?:host )?only/i.test(fleet.today)) fail('FLEET describes host_permissions as the entire access surface');
  const {catalogueExport} = await import('../site/src/catalogue-export.js');
  for (const t of [...personTags,...tags]) {
    const saved=catalogueExport(t,usage(t),null,[]);
    if (saved.record_type!=='catalogue_description'||saved.evaluated_result!==false) fail(t.code+': definition export may be mistaken for a checked answer');
    for (const field of ['subject_hash','assertions','abstentions']) if (field in saved) fail(t.code+': definition export carries evaluated-result fields');
  }
  const audit=tags.find(t=>t.id==='audit');
  if (!/not a checked answer/.test(audit.today)) fail('AUDIT does not distinguish descriptions from checked results');
  if (/every tag panel.*complete versioned record/i.test(audit.today)) fail('AUDIT falsely promises evaluated results from catalogue panels');
  const sso=tags.find(t=>t.id==='sso');
  if (!/proposed/.test(sso.today)||!/not enforced/.test(sso.today)) fail('SSO presents design permissions as enforced access');
  if (!sso.features.includes('F-128')||!/decline receipt issuance/.test(sso.release)) fail('SSO drops optional author receipts');
  const support=tags.find(t=>t.id==='support');
  if (!/private.*security|private vulnerability/.test(support.today)) fail('SUPPORT must route security disclosure privately');
  if (tags.some(t=>t.references.some(r=>r.includes('private-host-operations')))) fail('Host capture points to unrelated private infrastructure operations');

  if (fails.length) {
    console.error(`\n${fails.length} FAILURE(S):`);
    for (const f of fails) console.error('  FAIL  ' + f);
    process.exitCode = 1;
    return;
  }
  console.log(`PASS — ${tags.length} organization offerings, independently described.`);
  console.log(`  ${FIELDS.length} fields unique per offering; supported/limits unique; usage unique.`);
  console.log(`  every cited scope record exists; feature sets unique: ${tags.map((t)=>t.code+'='+t.features.length).join(' ')}`);
  console.log('  Proposals remain unavailable; free personal workflow retained.');
  console.log('  Manifest page access disclosed; catalogue/result exports distinct; SSO consent preserved; private security routing stated.');
})().catch((e) => { console.error(e); process.exitCode = 1; });
