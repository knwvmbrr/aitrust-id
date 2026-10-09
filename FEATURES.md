# FEATURES.md — the register

**Historical snapshot from 2026-10-07.** Counts and implementation descriptions
below are preserved audit history, not current claims. The authoritative 198-record
scope is `docs/master-scope.json`; executed behavior is in `state.json`, README
and dated `runs/`. Tests, adapters and public hosting now exist. The old no-test
and soft-fail statements are superseded. No tag has passed release validation.

Every capability this project has specified. **No row is ever deleted** — rows only change
state. A feature that gets cut moves to `dropped` *with a reason*, so nobody re-litigates a
decision from memory four months later.

**Owner: Claude (Cowork).** Codex may move a row to `built` and must list what it did and did
not do. **Only Claude moves a row to `verified`,** and only against the written acceptance
criterion — never against the code in front of it.

States: `spec'd` → `built` → `tested` → `verified` · plus `reserved` (deliberately not built)
and `dropped` (cut, with reason).

**Audited against the tree 2026-10-07.** Where this file and the code disagree, the code wins
and this file is wrong — tell me.

---

## The headline, stated plainly

| | Count |
|---|---|
| Features specified | 38 |
| Actually implemented in code | **3** |
| Covered by an automated test | **0** |
| Verified against a written criterion | **0** |

**There is no test suite in this repository.** No `tests/` directory, no pytest files, and the
CI workflow carries `|| true` fallbacks that make it pass regardless. The eval harness exists
but has no `results.json` to read because nothing has been run against fixtures.

That is the honest state and it is why we are not publishing a launch post this week.

---

## 1 · Specification

| ID | Feature | State | Evidence / gap |
|---|---|---|---|
| F-001 | Assertion envelope schema (JSON Schema 2020-12) | `built` | `spec/assertion.schema.json` — parses, but **no conformance test in CI** |
| F-002 | Nine-label taxonomy | `spec'd` | `spec/taxonomy.md` |
| F-003 | Signal registry — 20 registered IDs | `spec'd` | `spec/signals.md` |
| F-004 | Abstention as a first-class state (`UNK`) | `spec'd` | In schema; nothing emits it yet |
| F-005 | Per-tag confidence floors | `spec'd` | In taxonomy; **not enforced in code** |
| F-006 | Modality reservation — text, code, image, audio, video, document | `spec'd` | RFC-0003; enum updated 2026-10-06 |
| F-007 | Content never transported — hash + offsets only | `built` | Gateway returns no text. **Not test-asserted.** |
| F-008 | ed25519 assertion signing | `spec'd` | Schema has the field; **no signing code exists** |

## 2 · Detection — labels

| ID | Label | State | Reality |
|---|---|---|---|
| F-010 | `PS` piped installer | `built` | One regex in `services/evaluator/app.py` |
| F-011 | `PS` obfuscated payload | `built` | One regex |
| F-012 | `PS` credential exfil | `spec'd` | Signal registered, **no implementation** |
| F-013 | `PS` typosquat + offline package snapshot | `spec'd` | **No implementation, no snapshot file** |
| F-014 | `PS` use/mention discriminator | `spec'd` | Sprint C10. Without it, PS fires inside comments and quoted prose |
| F-015 | `HP` unsourced specificity | `built` | Crude regex: any percentage or year with no source marker nearby |
| F-016 | `HP` self-contradiction (NLI) | `spec'd` | Needs ONNX model. **Not present** |
| F-017 | `HP` duplicate loop | `spec'd` | Not implemented |
| F-018 | `HP` hedge collapse | `spec'd` | Not implemented |
| F-019 | `MT` urgency / false dilemma / authority appeal | `spec'd` | **Blocked** — needs annotated corpus + Krippendorff α ≥ 0.55 |
| F-020 | `NF` / `FI` corpus support + contradiction | `spec'd` | Needs local corpus indexing. Not built |
| F-021 | `FA` / `PA` provenance from capture point | `spec'd` | Depends on F-030 |
| F-022 | `IV` human attestation, signed | `spec'd` | Never machine-assigned. No signing path yet |
| F-023 | `PII_REDACTED` via Presidio | `built` | `services/anonymizer` — runs, **untested** |
| F-024 | `PII_OUTBOUND` pre-send warning | `spec'd` | Presidio already in stack. **Highest value-per-hour unbuilt feature** |
| F-025 | C2PA manifest consumption as provenance signal | `spec'd` | Interop position stated; no parser |

## 3 · Behavioral provenance (RFC-0001)

| ID | Feature | State |
|---|---|---|
| F-026 | `sig.keystroke_liveness.v1` | `spec'd` |
| F-027 | `sig.revision_churn.v1` | `spec'd` |
| F-028 | `sig.compose_monotonicity.v1` | `spec'd` |
| F-029 | `sig.outside_knowledge.v1` · `sig.attention_shape.v1` · `sig.paste_burst.v1` | `spec'd` |

## 4 · Browser extension

| ID | Feature | State | Reality |
|---|---|---|---|
| F-030 | **MV3 MAIN-world capture** | `spec'd` | `tap.js` written, **never run against a real site.** The thesis blocker. |
| F-031 | DOM observer fallback | `spec'd` | In `bridge.js`, unproven |
| F-032 | Settle detection (600ms debounce) | `spec'd` | Written, unproven |
| F-033 | Closed shadow-root badge | `built` | `badge.js` — **no fixture page, so never rendered** |
| F-034 | Evidence panel with spans | `built` | Same — unrendered |
| F-035 | Full screen-reader semantics | `built` | Code is written correctly. **Zero manual SR testing done.** |
| F-036 | Signature verification before render | `spec'd` | Depends on F-008 |
| F-037 | Site adapters | `spec'd` | Only a README. **No adapter exists for any site.** |

## 5 · Services

| ID | Feature | State | Reality |
|---|---|---|---|
| F-040 | Gateway orchestration + calibration | `built` | Runs. Floors hardcoded, not read from taxonomy |
| F-041 | Presidio anonymizer, redact-before-evaluate | `built` | Order is correct in code; **not test-asserted** |
| F-042 | Evaluator, redacted text only | `built` | Rules-only; honestly self-reports as `"rules-only"` |
| F-043 | **No-egress network topology** | `built` | `internal: true` in compose. **Never actually verified by exec'ing into the container** |
| F-044 | Registry dashboard, hashes only | `built` | Streamlit skeleton, no data path |
| F-045 | Reporting intake (hash-only) | `spec'd` | **Blocked** on the illegal-content routing policy — correctly |

## 6 · Evaluation & CI

| ID | Feature | State | Reality |
|---|---|---|---|
| F-050 | Gate thresholds | `spec'd` | `eval/gates.yaml` written |
| F-051 | Harness computing P / R / ECE | `built` | `eval/harness.py` exists, **has never run — no `results.json`** |
| F-052 | PS fixture set | `built` | **24 lines.** Sprint requires ≥60 positives **and** ≥60 adversarial negatives. You cannot measure 0.93 precision on 24 examples. |
| F-053 | HP / MT / FI fixtures | `spec'd` | None exist |
| F-054 | CI actually blocking | `spec'd` | Workflow has `|| true` — **it cannot fail** |
| F-055 | axe-core accessibility gate | `spec'd` | Needs a fixture page (F-033) |
| F-056 | Krippendorff α published for MT | `spec'd` | Blocks F-019 |
| F-057 | SBOM + Sigstore signing | `spec'd` | Not started |

## 7 · Reserved — deliberately not built (RFC-0003)

| ID | Modality | State | Why |
|---|---|---|---|
| F-060 | `image` | `reserved` | C2PA + SynthID are better at this; consume, don't compete |
| F-061 | `audio` | `reserved` | Voice-clone detection is an arms race against specialists |
| F-062 | `video` | `reserved` | Outside any local-CPU budget |
| F-063 | `document` | `reserved` | **Open question: may deserve to jump ahead of image** — text layer is tractable, and contracts / invoices / medical letters are where harm concentrates |

## 8 · Governance & docs

| ID | Feature | State |
|---|---|---|
| F-070 | Six invariants in CONTRIBUTING | `built` |
| F-071 | Threat model, 10 entries | `built` |
| F-072 | ACCESSIBILITY.md as a release gate | `built` |
| F-073 | SECURITY.md with a 72-hour promise | `built` — **the promised inbox does not exist yet** |
| F-074 | CODE_OF_CONDUCT with enforcement ladder | `built` — conduct@ inbox does not exist yet |
| F-075 | GOVERNANCE — two-entity structure | `spec'd` |
| F-076 | RFC process | `built` — template + 3 live RFCs |
| F-077 | Dual licence: Apache-2.0 code, CC BY 4.0 spec | `built` — **LICENSE is still a stub, not the real text** |

---

## What we may honestly claim today

> "A published specification for evidence-backed AI content labels, with a reference
> implementation in progress. Two detection rules work. Nothing is tested yet."

## What we may NOT claim

- That any label is accurate — **no measurement exists**
- That the extension works — **capture has never been run**
- That it's accessible — the code is right, but **nothing has been screen-reader tested**
- That no-egress holds — **it has never been exercised**

## The five things that must be true before launch

1. **F-030** — capture proven on one real site, or the architecture changes
2. **A test suite exists** and CI can actually fail
3. **F-052** — PS fixtures at ≥60/60 so the 0.93 gate means something
4. **F-073/F-074** — the promised inboxes exist, or the promises get removed
5. **F-077** — real Apache-2.0 text

## Audit log

- **2026-10-07 — Claude.** First full audit against the tree. 38 features specified, 3
  implemented, 0 tested, 0 verified. Register created.
