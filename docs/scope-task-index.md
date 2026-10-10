# Scope task index

All 202 source IDs remain covered. This is a crosswalk into the [one execution plan](scope-delivery.md), not a second roadmap. Package subtasks and gates supply the delivery criteria. Legacy grouping rows are traceability records, not extra detector implementations.

| Record/task | Preserved requirement | Work packages | Completion at latest audit |
|---|---|---|---|
| TASK-F-001 | Assertion envelope schema, JSON Schema 2020-12 | [WP-PROTOCOL](scope-delivery.md#wp-protocol) | 100% · [evidence/fix](scope-progress.md) |
| TASK-F-002 | Nine-label taxonomy (plus UNK, PII_REDACTED) | [WP-PROTOCOL](scope-delivery.md#wp-protocol) | 100% · [evidence/fix](scope-progress.md) |
| TASK-F-003 | Signal registry, 22 registered IDs with version suffixes | [WP-PROTOCOL](scope-delivery.md#wp-protocol) | 20% · [evidence/fix](scope-progress.md) |
| TASK-F-004 | Abstention as a first-class state — UNK | [TAG-UNK](scope-delivery.md#tag-unk) | 20% · [evidence/fix](scope-progress.md) |
| TASK-F-005 | Per-tag confidence floors | [WP-PROTOCOL](scope-delivery.md#wp-protocol) | 20% · [evidence/fix](scope-progress.md) |
| TASK-F-006 | Six-modality reservation with normative subject definitions | [WP-PROTOCOL](scope-delivery.md#wp-protocol) | 20% · [evidence/fix](scope-progress.md) |
| TASK-F-007 | Content-free assertion records | [WP-PROTOCOL](scope-delivery.md#wp-protocol) | 100% · [evidence/fix](scope-progress.md) |
| TASK-F-008 | Signed assertion integrity | [WP-INTEGRITY](scope-delivery.md#wp-integrity) | 20% · [evidence/fix](scope-progress.md) |
| TASK-F-009 | Evidence durability and cost-to-defeat assessment | [WP-INTEGRITY](scope-delivery.md#wp-integrity) | 20% · [evidence/fix](scope-progress.md) |
| TASK-F-078 | Conformance vectors for text and code subject hashes | [WP-PROTOCOL](scope-delivery.md#wp-protocol) | 100% · [evidence/fix](scope-progress.md) |
| TASK-F-079 | Route-specific privacy clauses with executed evidence | [WP-PRIVACY](scope-delivery.md#wp-privacy) | 40% · [evidence/fix](scope-progress.md) |
| TASK-F-080 | Subject hash documented as a correlation identifier, not an anonymisation | [WP-PRIVACY](scope-delivery.md#wp-privacy) | 60% · [evidence/fix](scope-progress.md) |
| TASK-F-076 | RFC process — template, 14-day comment, evidence requirement | [WP-GOVERNANCE](scope-delivery.md#wp-governance) | 40% · [evidence/fix](scope-progress.md) |
| TASK-F-077 | Dual licence: Apache-2.0 code, CC BY 4.0 spec | [WP-GOVERNANCE](scope-delivery.md#wp-governance) | 100% · [evidence/fix](scope-progress.md) |
| TASK-T-NF | NF Non-Fiction | [TAG-NF](scope-delivery.md#tag-nf) | 20% · [evidence/fix](scope-progress.md) |
| TASK-T-FI | FI Fiction / Fabricated | [TAG-FI](scope-delivery.md#tag-fi) | 20% · [evidence/fix](scope-progress.md) |
| TASK-T-HP | HP Hallucination Possible | [TAG-HP](scope-delivery.md#tag-hp) | 20% · [evidence/fix](scope-progress.md) |
| TASK-T-MT | MT Manipulative Tactic | [TAG-MT](scope-delivery.md#tag-mt) | 20% · [evidence/fix](scope-progress.md) |
| TASK-T-PS | PS Potential Scam / Risk | [TAG-PS](scope-delivery.md#tag-ps) | 80% · [evidence/fix](scope-progress.md) |
| TASK-T-IV | IV Independently Verified | [TAG-IV](scope-delivery.md#tag-iv) | 20% · [evidence/fix](scope-progress.md) |
| TASK-T-FA | FA Full AI Augmentation | [TAG-FA](scope-delivery.md#tag-fa) | 20% · [evidence/fix](scope-progress.md) |
| TASK-T-PA | PA Partially Augmented | [TAG-PA](scope-delivery.md#tag-pa) | 20% · [evidence/fix](scope-progress.md) |
| TASK-T-UNK | UNK Unknown | [TAG-UNK](scope-delivery.md#tag-unk) | 20% · [evidence/fix](scope-progress.md) |
| TASK-T-PII | PII_REDACTED | [TAG-PII_REDACTED](scope-delivery.md#tag-pii_redacted) | 60% · [evidence/fix](scope-progress.md) |
| TASK-T-OUT | PII_OUTBOUND | [TAG-PII_OUTBOUND](scope-delivery.md#tag-pii_outbound) | 20% · [evidence/fix](scope-progress.md) |
| TASK-F-010 | sig.piped_installer.v1 — curl/wget piped to a shell | [TAG-PS](scope-delivery.md#tag-ps) | 80% · [evidence/fix](scope-progress.md) |
| TASK-F-011 | sig.obfuscated_payload.v1 — base64/hex into eval/exec | [TAG-PS](scope-delivery.md#tag-ps) | 80% · [evidence/fix](scope-progress.md) |
| TASK-F-012 | sig.credential_exfil.v1 — reads a secret path, writes to a network sink | [TAG-PS](scope-delivery.md#tag-ps) | 20% · [evidence/fix](scope-progress.md) |
| TASK-F-013 | sig.typosquat.v1 — package name within edit distance 1–2 of a top-N name | [TAG-PS](scope-delivery.md#tag-ps) | 20% · [evidence/fix](scope-progress.md) |
| TASK-F-014 | Use/mention discriminator — is the command being recommended or discussed? | [TAG-PS](scope-delivery.md#tag-ps) | 80% · [evidence/fix](scope-progress.md) |
| TASK-F-015 | sig.unsourced_specificity.v1 — figures or dates with no provenance marker | [TAG-HP](scope-delivery.md#tag-hp) | 20% · [evidence/fix](scope-progress.md) |
| TASK-F-016 | sig.selfcontradiction.v1 — NLI entailment between sentence pairs | [TAG-HP](scope-delivery.md#tag-hp) | 20% · [evidence/fix](scope-progress.md) |
| TASK-F-017 | sig.duplicate_loop.v1 — n-gram repetition above threshold | [TAG-HP](scope-delivery.md#tag-hp) | 20% · [evidence/fix](scope-progress.md) |
| TASK-F-018 | sig.hedge_collapse.v1 — hedging absent where uncertainty is expected | [TAG-HP](scope-delivery.md#tag-hp) | 20% · [evidence/fix](scope-progress.md) |
| TASK-F-019a | sig.urgency_frame.v1 — time-pressure lexicon plus imperative density | [TAG-MT](scope-delivery.md#tag-mt) | 20% · [evidence/fix](scope-progress.md) |
| TASK-F-019b | sig.false_dilemma.v1 — binary framing where alternatives exist | [TAG-MT](scope-delivery.md#tag-mt) | 20% · [evidence/fix](scope-progress.md) |
| TASK-F-019c | sig.authority_appeal.v1 — unattributed appeals to expertise or consensus | [TAG-MT](scope-delivery.md#tag-mt) | 20% · [evidence/fix](scope-progress.md) |
| TASK-F-020a | sig.corpus_support.v1 — retrieval similarity against an attached local corpus | [TAG-NF](scope-delivery.md#tag-nf) | 20% · [evidence/fix](scope-progress.md) |
| TASK-F-020b | sig.corpus_contradiction.v1 — NLI contradiction against a retrieved passage | [TAG-FI](scope-delivery.md#tag-fi) | 20% · [evidence/fix](scope-progress.md) |
| TASK-F-081 | Bring-your-own corpus — the user attaches their own reference material locally | [WP-REFERENCES](scope-delivery.md#wp-references) | 100% · [evidence/fix](scope-progress.md) |
| TASK-F-026 | sig.keystroke_liveness.v1 — dwell and flight time distributions | [TAG-PA](scope-delivery.md#tag-pa) | 20% · [evidence/fix](scope-progress.md) |
| TASK-F-027 | sig.revision_churn.v1 — deleted-and-rewritten characters over final length | [TAG-PA](scope-delivery.md#tag-pa) | 20% · [evidence/fix](scope-progress.md) |
| TASK-F-028 | sig.compose_monotonicity.v1 — caret-position entropy | [TAG-PA](scope-delivery.md#tag-pa) | 20% · [evidence/fix](scope-progress.md) |
| TASK-F-029a | sig.outside_knowledge.v1 — a revision introduces something not derivable from the captured session | [TAG-PA](scope-delivery.md#tag-pa) | 20% · [evidence/fix](scope-progress.md) |
| TASK-F-029b | sig.attention_shape.v1 — read-pause-write rhythm from focus and visibility events | [TAG-PA](scope-delivery.md#tag-pa) | 20% · [evidence/fix](scope-progress.md) |
| TASK-F-029c | sig.paste_burst.v1 — large insertion with no preceding keystrokes | [TAG-PA](scope-delivery.md#tag-pa) | 20% · [evidence/fix](scope-progress.md) |
| TASK-F-025 | sig.c2pa_manifest.v1 — parses an attached C2PA manifest | [TAG-FA](scope-delivery.md#tag-fa) | 20% · [evidence/fix](scope-progress.md) |
| TASK-F-082 | Assistive input safety routing | [TAG-PA](scope-delivery.md#tag-pa) | 20% · [evidence/fix](scope-progress.md) |
| TASK-F-083 | The governing rule: a provenance signal may raise toward PA or FA but may never lower a tag toward a human-negative verdict. Absence of human signal produces UNK, never FA | [TAG-FA](scope-delivery.md#tag-fa) | 20% · [evidence/fix](scope-progress.md) |
| TASK-F-023 | Detected PII redaction | [TAG-PII_REDACTED](scope-delivery.md#tag-pii_redacted) | 60% · [evidence/fix](scope-progress.md) |
| TASK-F-041 | Detected redaction before local-service evaluation | [TAG-PII_REDACTED](scope-delivery.md#tag-pii_redacted) | 100% · [evidence/fix](scope-progress.md) |
| TASK-F-024 | PII_OUTBOUND pre-send warning — you are about to paste personal data into a model | [TAG-PII_OUTBOUND](scope-delivery.md#tag-pii_outbound) | 20% · [evidence/fix](scope-progress.md) |
| TASK-F-043 | No-egress network topology — internal: true, loopback binding | [WP-SERVICE](scope-delivery.md#wp-service) | 100% · [evidence/fix](scope-progress.md) |
| TASK-F-084 | No content logging — a verified clause, not a promise | [WP-PRIVACY](scope-delivery.md#wp-privacy) | 60% · [evidence/fix](scope-progress.md) |
| TASK-F-085 | No application-controlled content persistence | [WP-PRIVACY](scope-delivery.md#wp-privacy) | 60% · [evidence/fix](scope-progress.md) |
| TASK-F-086 | No telemetry, no analytics, no phone-home — in the extension or the services | [WP-PRIVACY](scope-delivery.md#wp-privacy) | 60% · [evidence/fix](scope-progress.md) |
| TASK-F-087 | Capture trust boundary, published plainly | [WP-PRIVACY](scope-delivery.md#wp-privacy) | 60% · [evidence/fix](scope-progress.md) |
| TASK-F-030 | MV3 MAIN-world capture — fetch patch plus ReadableStream.tee() | [WP-CAPTURE](scope-delivery.md#wp-capture) | 40% · [evidence/fix](scope-progress.md) |
| TASK-F-031 | DOM observer fallback for sites the fetch patch misses | [WP-CAPTURE](scope-delivery.md#wp-capture) | 60% · [evidence/fix](scope-progress.md) |
| TASK-F-088 | Response identity and revision binding | [WP-CAPTURE](scope-delivery.md#wp-capture) | 60% · [evidence/fix](scope-progress.md) |
| TASK-F-089 | Duplicate suppression — one badge per response | [WP-CAPTURE](scope-delivery.md#wp-capture) | 60% · [evidence/fix](scope-progress.md) |
| TASK-F-090 | Character-data mutation observation | [WP-CAPTURE](scope-delivery.md#wp-capture) | 60% · [evidence/fix](scope-progress.md) |
| TASK-F-032 | Streaming settle detection | [WP-CAPTURE](scope-delivery.md#wp-capture) | 60% · [evidence/fix](scope-progress.md) |
| TASK-F-037 | Per-vendor site adapters | [WP-CAPTURE](scope-delivery.md#wp-capture) | 60% · [evidence/fix](scope-progress.md) |
| TASK-F-033 | Closed shadow-root badge, monochrome | [WP-UX](scope-delivery.md#wp-ux) | 100% · [evidence/fix](scope-progress.md) |
| TASK-F-034 | Evidence panel showing the exact spans that triggered the tag | [WP-UX](scope-delivery.md#wp-ux) | 60% · [evidence/fix](scope-progress.md) |
| TASK-F-091 | Options page for the bearer token | [WP-PRIVACY](scope-delivery.md#wp-privacy) | 80% · [evidence/fix](scope-progress.md) |
| TASK-F-035 | Full screen-reader semantics, aria-live="polite" never assertive | [WP-UX](scope-delivery.md#wp-ux) | 60% · [evidence/fix](scope-progress.md) |
| TASK-F-092 | Keyboard-only operation — reach, open, read, close the panel | [WP-UX](scope-delivery.md#wp-ux) | 100% · [evidence/fix](scope-progress.md) |
| TASK-F-093 | Forced-colors and high-contrast support | [WP-UX](scope-delivery.md#wp-ux) | 100% · [evidence/fix](scope-progress.md) |
| TASK-F-094 | 200% zoom and reduced-motion support | [WP-UX](scope-delivery.md#wp-ux) | 100% · [evidence/fix](scope-progress.md) |
| TASK-F-095 | Monochrome-by-construction design — the movie/TV content-rating look | [WP-UX](scope-delivery.md#wp-ux) | 100% · [evidence/fix](scope-progress.md) |
| TASK-F-036 | Signature verification before render | [WP-INTEGRITY](scope-delivery.md#wp-integrity) | 20% · [evidence/fix](scope-progress.md) |
| TASK-F-096 | Graceful degradation — backend down, invalid token, unsupported page | [WP-SERVICE](scope-delivery.md#wp-service) | 60% · [evidence/fix](scope-progress.md) |
| TASK-F-097 | User-invoked labelling — select a response, ask for a check | [WP-CAPTURE](scope-delivery.md#wp-capture) | 60% · [evidence/fix](scope-progress.md) |
| TASK-F-040 | Gateway orchestration — redact, evaluate, calibrate, return | [WP-SERVICE](scope-delivery.md#wp-service) | 100% · [evidence/fix](scope-progress.md) |
| TASK-F-042 | Evaluator on redacted text only; self-reports as "rules-only" | [WP-SERVICE](scope-delivery.md#wp-service) | 100% · [evidence/fix](scope-progress.md) |
| TASK-F-098 | Presidio language assets baked into the image | [TAG-PII_REDACTED](scope-delivery.md#tag-pii_redacted) | 100% · [evidence/fix](scope-progress.md) |
| TASK-F-099 | Upstream response validation — status and shape checked before parsing | [WP-SERVICE](scope-delivery.md#wp-service) | 100% · [evidence/fix](scope-progress.md) |
| TASK-F-100 | Constant-time bearer token comparison | [WP-SERVICE](scope-delivery.md#wp-service) | 100% · [evidence/fix](scope-progress.md) |
| TASK-F-101 | Startup refusal of the example token change-me | [WP-SERVICE](scope-delivery.md#wp-service) | 100% · [evidence/fix](scope-progress.md) |
| TASK-F-102 | Modality validated against the schema enum; unsupported returns UNK + unsupported_modality | [WP-SERVICE](scope-delivery.md#wp-service) | 60% · [evidence/fix](scope-progress.md) |
| TASK-F-103 | Health checks reporting dependency readiness, not process liveness | [WP-SERVICE](scope-delivery.md#wp-service) | 100% · [evidence/fix](scope-progress.md) |
| TASK-F-104 | Defined dependency-failure behaviour | [WP-SERVICE](scope-delivery.md#wp-service) | 100% · [evidence/fix](scope-progress.md) |
| TASK-F-044 | Optional registry and retention proposal | [ORG-AUDIT](scope-delivery.md#org-audit) | 20% · [evidence/fix](scope-progress.md) |
| TASK-F-045 | Reporting intake, hash-only | [ORG-AUDIT](scope-delivery.md#org-audit) | 20% · [evidence/fix](scope-progress.md) |
| TASK-F-105 | One documented command: clean clone → running stack | [WP-MOBILE](scope-delivery.md#wp-mobile) | 60% · [evidence/fix](scope-progress.md) |
| TASK-F-050 | Gate thresholds in eval/gates.yaml — precision, recall, ECE, abstention band, latency, axe, α | [WP-VALIDATION](scope-delivery.md#wp-validation) | 60% · [evidence/fix](scope-progress.md) |
| TASK-F-051 | Executable evaluation harness | [WP-VALIDATION](scope-delivery.md#wp-validation) | 100% · [evidence/fix](scope-progress.md) |
| TASK-F-106 | Wilson confidence intervals, lower-bound gating, n published beside every figure | [WP-VALIDATION](scope-delivery.md#wp-validation) | 100% · [evidence/fix](scope-progress.md) |
| TASK-F-107 | Per-category failure breakdown on every metric | [WP-VALIDATION](scope-delivery.md#wp-validation) | 100% · [evidence/fix](scope-progress.md) |
| TASK-F-052 | PS fixture set | [TAG-PS](scope-delivery.md#tag-ps) | 100% · [evidence/fix](scope-progress.md) |
| TASK-F-108 | Frozen held-out split with a manifest hash, separate from the regression suite | [WP-VALIDATION](scope-delivery.md#wp-validation) | 60% · [evidence/fix](scope-progress.md) |
| TASK-F-109 | Dataset versioning and provenance per example | [WP-VALIDATION](scope-delivery.md#wp-validation) | 100% · [evidence/fix](scope-progress.md) |
| TASK-F-110 | Adversarial boundary examples for the use/mention discriminator | [TAG-PS](scope-delivery.md#tag-ps) | 100% · [evidence/fix](scope-progress.md) |
| TASK-F-053 | HP / MT / FI fixtures | [WP-VALIDATION](scope-delivery.md#wp-validation) | 20% · [evidence/fix](scope-progress.md) |
| TASK-F-056 | Krippendorff's α published for MT, ≥ 0.55 | [TAG-MT](scope-delivery.md#tag-mt) | 20% · [evidence/fix](scope-progress.md) |
| TASK-F-054 | CI that can actually fail | [WP-RELEASE](scope-delivery.md#wp-release) | 40% · [evidence/fix](scope-progress.md) |
| TASK-F-111 | Evaluator unit tests — the first tests in the repository | [WP-RELEASE](scope-delivery.md#wp-release) | 100% · [evidence/fix](scope-progress.md) |
| TASK-F-112 | Schema validation against real service responses, not just schema syntax | [WP-RELEASE](scope-delivery.md#wp-release) | 100% · [evidence/fix](scope-progress.md) |
| TASK-F-055 | axe-core accessibility gate, serious and critical at zero | [WP-UX](scope-delivery.md#wp-ux) | 100% · [evidence/fix](scope-progress.md) |
| TASK-F-113 | Measured latency budget on declared hardware | [WP-RELEASE](scope-delivery.md#wp-release) | 60% · [evidence/fix](scope-progress.md) |
| TASK-F-114 | Method-appropriate abstention measurement and policy | [WP-VALIDATION](scope-delivery.md#wp-validation) | 60% · [evidence/fix](scope-progress.md) |
| TASK-F-115 | Network-isolation verification — exec into each container and prove it cannot reach out | [WP-SERVICE](scope-delivery.md#wp-service) | 100% · [evidence/fix](scope-progress.md) |
| TASK-F-057 | SBOM plus Sigstore release signing | [WP-RELEASE](scope-delivery.md#wp-release) | 20% · [evidence/fix](scope-progress.md) |
| TASK-F-116 | Dependency lockfiles and hashes, not just version pins | [WP-RELEASE](scope-delivery.md#wp-release) | 60% · [evidence/fix](scope-progress.md) |
| TASK-F-117 | Model hash verification at load | [WP-RELEASE](scope-delivery.md#wp-release) | 100% · [evidence/fix](scope-progress.md) |
| TASK-F-118 | Calibration ledger — every published number reproducible by a third party | [WP-VALIDATION](scope-delivery.md#wp-validation) | 100% · [evidence/fix](scope-progress.md) |
| TASK-F-119 | Conformance test suite an outside implementer can run against their own build | [WP-RELEASE](scope-delivery.md#wp-release) | 60% · [evidence/fix](scope-progress.md) |
| TASK-F-120 | Evidence packets — committed transcripts per exit gate | [WP-RELEASE](scope-delivery.md#wp-release) | 60% · [evidence/fix](scope-progress.md) |
| TASK-F-121 | Receipt format binding an artifact hash to observed composition activity | [WP-RECEIPTS](scope-delivery.md#wp-receipts) | 20% · [evidence/fix](scope-progress.md) |
| TASK-F-122 | Receipt issuance — always a free path, by policy | [WP-RECEIPTS](scope-delivery.md#wp-receipts) | 20% · [evidence/fix](scope-progress.md) |
| TASK-F-123 | Receipt verification requiring no contact with us | [WP-RECEIPTS](scope-delivery.md#wp-receipts) | 20% · [evidence/fix](scope-progress.md) |
| TASK-F-124 | Independent RFC 3161 timestamping — we never operate the authority | [WP-RECEIPTS](scope-delivery.md#wp-receipts) | 20% · [evidence/fix](scope-progress.md) |
| TASK-F-125 | Per-device revocable keys plus a revocation transparency log | [WP-RECEIPTS](scope-delivery.md#wp-receipts) | 20% · [evidence/fix](scope-progress.md) |
| TASK-F-126 | Freshness model for offline verification against revocation | [WP-RECEIPTS](scope-delivery.md#wp-receipts) | 20% · [evidence/fix](scope-progress.md) |
| TASK-F-127 | Forgery-cost class as a first-class field on every receipt | [WP-RECEIPTS](scope-delivery.md#wp-receipts) | 20% · [evidence/fix](scope-progress.md) |
| TASK-F-128 | Anti-coercion rule — a conformant implementation may not make receipt issuance non-optional for the author | [WP-RECEIPTS](scope-delivery.md#wp-receipts) | 20% · [evidence/fix](scope-progress.md) |
| TASK-F-129 | Key custody and recovery for a non-technical author | [WP-RECEIPTS](scope-delivery.md#wp-receipts) | 20% · [evidence/fix](scope-progress.md) |
| TASK-F-130 | Group authorship — four signers or four receipts | [WP-RECEIPTS](scope-delivery.md#wp-receipts) | 20% · [evidence/fix](scope-progress.md) |
| TASK-F-131 | Receipt expiry and algorithm agility — ed25519 will not be safe forever | [WP-RECEIPTS](scope-delivery.md#wp-receipts) | 20% · [evidence/fix](scope-progress.md) |
| TASK-F-132 | aitrustid.com — landing and reference content, no-JS core | [WP-SITE](scope-delivery.md#wp-site) | 100% · [evidence/fix](scope-progress.md) |
| TASK-F-133 | Public status table distinguishing supported / experimental / reserved | [WP-SITE](scope-delivery.md#wp-site) | 100% · [evidence/fix](scope-progress.md) |
| TASK-F-134 | Limitations page, findable without being told where it is | [WP-SITE](scope-delivery.md#wp-site) | 100% · [evidence/fix](scope-progress.md) |
| TASK-F-135 | Report AI — public intake for AI content people want flagged | [WP-COMMUNITY](scope-delivery.md#wp-community) | 40% · [evidence/fix](scope-progress.md) |
| TASK-F-136 | Townhall — a community space for AI users to talk, with moderation | [WP-COMMUNITY](scope-delivery.md#wp-community) | 40% · [evidence/fix](scope-progress.md) |
| TASK-F-137 | Moderation ladder and escalation path derived from the code of conduct | [WP-COMMUNITY](scope-delivery.md#wp-community) | 40% · [evidence/fix](scope-progress.md) |
| TASK-F-073 | Security reporting and response-capacity planning | [WP-OPERATIONS](scope-delivery.md#wp-operations) | 60% · [evidence/fix](scope-progress.md) |
| TASK-F-074 | conduct@ with an enforcement ladder | [WP-COMMUNITY](scope-delivery.md#wp-community) | 40% · [evidence/fix](scope-progress.md) |
| TASK-F-138 | abuse@ and press@ | [WP-COMMUNITY](scope-delivery.md#wp-community) | 40% · [evidence/fix](scope-progress.md) |
| TASK-F-139 | Site accessibility held to the same gate as the extension | [WP-SITE](scope-delivery.md#wp-site) | 80% · [evidence/fix](scope-progress.md) |
| TASK-F-140 | Sanitised public roadmap — no personal execution material | [WP-SITE](scope-delivery.md#wp-site) | 100% · [evidence/fix](scope-progress.md) |
| TASK-F-141 | Pilot programme — small consenting group, feedback without collecting prompts or outputs | [WP-COMMUNITY](scope-delivery.md#wp-community) | 20% · [evidence/fix](scope-progress.md) |
| TASK-F-142 | Install and removal instructions, reproducible | [WP-SITE](scope-delivery.md#wp-site) | 80% · [evidence/fix](scope-progress.md) |
| TASK-F-075 | Two-entity structure — independent foundation holds spec and mark; implementations compete on top | [WP-GOVERNANCE](scope-delivery.md#wp-governance) | 20% · [evidence/fix](scope-progress.md) |
| TASK-F-143 | Certification-mark ownership and filing work | [WP-GOVERNANCE](scope-delivery.md#wp-governance) | 20% · [evidence/fix](scope-progress.md) |
| TASK-F-144 | Mark usage guidelines and a conformance statement template | [WP-GOVERNANCE](scope-delivery.md#wp-governance) | 20% · [evidence/fix](scope-progress.md) |
| TASK-F-145 | Certification programme — what a certifier must test, and how one is accredited | [WP-GOVERNANCE](scope-delivery.md#wp-governance) | 20% · [evidence/fix](scope-progress.md) |
| TASK-F-146 | Nonprofit formation and filings | [WP-GOVERNANCE](scope-delivery.md#wp-governance) | 20% · [evidence/fix](scope-progress.md) |
| TASK-F-147 | Conflict-of-interest recusal rule for maintainers with a commercial interest | [WP-GOVERNANCE](scope-delivery.md#wp-governance) | 40% · [evidence/fix](scope-progress.md) |
| TASK-F-148 | Qualified legal review of every biometric and privacy assurance | [WP-GOVERNANCE](scope-delivery.md#wp-governance) | 20% · [evidence/fix](scope-progress.md) |
| TASK-F-070 | Six invariants in CONTRIBUTING.md | [WP-GOVERNANCE](scope-delivery.md#wp-governance) | 100% · [evidence/fix](scope-progress.md) |
| TASK-F-071 | Threat model, 10 entries | [WP-OPERATIONS](scope-delivery.md#wp-operations) | 100% · [evidence/fix](scope-progress.md) |
| TASK-F-072 | ACCESSIBILITY.md as a release gate | [WP-UX](scope-delivery.md#wp-ux) | 20% · [evidence/fix](scope-progress.md) |
| TASK-F-149 | MAINTAINERS.md with per-maintainer scope | [WP-GOVERNANCE](scope-delivery.md#wp-governance) | 100% · [evidence/fix](scope-progress.md) |
| TASK-F-150 | CHANGELOG.md, state.json, docs/, runs/ | [WP-OPERATIONS](scope-delivery.md#wp-operations) | 100% · [evidence/fix](scope-progress.md) |
| TASK-F-151 | DECISIONS.md — 15 seeded decisions with dates and reasons | [WP-GOVERNANCE](scope-delivery.md#wp-governance) | 40% · [evidence/fix](scope-progress.md) |
| TASK-F-152 | Branch protection, CODEOWNERS, required status checks, Dependabot | [WP-OPERATIONS](scope-delivery.md#wp-operations) | 40% · [evidence/fix](scope-progress.md) |
| TASK-F-153 | Named ongoing ownership for security response and adapter maintenance | [WP-OPERATIONS](scope-delivery.md#wp-operations) | 100% · [evidence/fix](scope-progress.md) |
| TASK-F-060 | image | [WP-MODALITIES](scope-delivery.md#wp-modalities) | 20% · [evidence/fix](scope-progress.md) |
| TASK-F-061 | audio | [WP-MODALITIES](scope-delivery.md#wp-modalities) | 20% · [evidence/fix](scope-progress.md) |
| TASK-F-062 | video | [WP-MODALITIES](scope-delivery.md#wp-modalities) | 20% · [evidence/fix](scope-progress.md) |
| TASK-F-063 | document | [WP-MODALITIES](scope-delivery.md#wp-modalities) | 20% · [evidence/fix](scope-progress.md) |
| TASK-F-154 | text and code subject contracts | [WP-MODALITIES](scope-delivery.md#wp-modalities) | 100% · [evidence/fix](scope-progress.md) |
| TASK-F-155 | SynthID and vendor watermarking | [WP-INTEGRATIONS](scope-delivery.md#wp-integrations) | 20% · [evidence/fix](scope-progress.md) |
| TASK-F-156 | Additional browser and site adapters | [WP-INTEGRATIONS](scope-delivery.md#wp-integrations) | 20% · [evidence/fix](scope-progress.md) |
| TASK-F-157 | Newsroom integration — labels in an editorial workflow | [WP-INTEGRATIONS](scope-delivery.md#wp-integrations) | 20% · [evidence/fix](scope-progress.md) |
| TASK-F-158 | Agent identity — labelling output from autonomous agents | [WP-INTEGRATIONS](scope-delivery.md#wp-integrations) | 20% · [evidence/fix](scope-progress.md) |
| TASK-F-159 | Fleet deployment and policy management | [ORG-FLEET](scope-delivery.md#org-fleet) | 20% · [evidence/fix](scope-progress.md) |
| TASK-F-160 | Host-level capture agents | [ORG-HOST](scope-delivery.md#org-host) | 20% · [evidence/fix](scope-progress.md) |
| TASK-F-161 | Long-horizon retention and audit trails | [ORG-AUDIT](scope-delivery.md#org-audit) | 20% · [evidence/fix](scope-progress.md) |
| TASK-F-162 | SSO and directory integration | [ORG-SSO](scope-delivery.md#org-sso) | 20% · [evidence/fix](scope-progress.md) |
| TASK-F-163 | Support with an SLA | [ORG-SUPPORT](scope-delivery.md#org-support) | 20% · [evidence/fix](scope-progress.md) |
| TASK-X-01 | A paid API or any metered inference | [WP-BOUNDARIES](scope-delivery.md#wp-boundaries) | 20% · [evidence/fix](scope-progress.md) |
| TASK-X-02 | Any closed-source or paid dependency in the pipeline | [WP-BOUNDARIES](scope-delivery.md#wp-boundaries) | 20% · [evidence/fix](scope-progress.md) |
| TASK-X-03 | A central database of assertions | [WP-BOUNDARIES](scope-delivery.md#wp-boundaries) | 20% · [evidence/fix](scope-progress.md) |
| TASK-X-04 | Per-person keystroke templates or any biometric identity profile | [WP-BOUNDARIES](scope-delivery.md#wp-boundaries) | 20% · [evidence/fix](scope-progress.md) |
| TASK-X-05 | Any human-negative verdict from an absent signal | [WP-BOUNDARIES](scope-delivery.md#wp-boundaries) | 20% · [evidence/fix](scope-progress.md) |
| TASK-X-06 | Telemetry, usage analytics, crash reporting | [WP-BOUNDARIES](scope-delivery.md#wp-boundaries) | 20% · [evidence/fix](scope-progress.md) |
| TASK-X-07 | Competing with C2PA on image provenance | [WP-BOUNDARIES](scope-delivery.md#wp-boundaries) | 20% · [evidence/fix](scope-progress.md) |
| TASK-X-08 | Building image, audio or video detection in 1.0 | [WP-BOUNDARIES](scope-delivery.md#wp-boundaries) | 20% · [evidence/fix](scope-progress.md) |
| TASK-X-09 | Colour-coded labels | [WP-BOUNDARIES](scope-delivery.md#wp-boundaries) | 20% · [evidence/fix](scope-progress.md) |
| TASK-X-10 | aria-live="assertive" announcements | [WP-BOUNDARIES](scope-delivery.md#wp-boundaries) | 20% · [evidence/fix](scope-progress.md) |
| TASK-X-11 | Machine-assigned IV | [WP-BOUNDARIES](scope-delivery.md#wp-boundaries) | 20% · [evidence/fix](scope-progress.md) |
| TASK-X-12 | Mandatory receipts | [WP-BOUNDARIES](scope-delivery.md#wp-boundaries) | 20% · [evidence/fix](scope-progress.md) |
| TASK-X-13 | Signing in 0.1 | [WP-BOUNDARIES](scope-delivery.md#wp-boundaries) | 20% · [evidence/fix](scope-progress.md) |
| TASK-X-14 | The registry container in 0.1 | [WP-BOUNDARIES](scope-delivery.md#wp-boundaries) | 20% · [evidence/fix](scope-progress.md) |
| TASK-X-15 | Collecting prompts or outputs from pilot users | [WP-BOUNDARIES](scope-delivery.md#wp-boundaries) | 20% · [evidence/fix](scope-progress.md) |
| TASK-X-16 | "Outside knowledge proves human authorship" as an implementation requirement | [WP-BOUNDARIES](scope-delivery.md#wp-boundaries) | 20% · [evidence/fix](scope-progress.md) |
| TASK-F-019 | Legacy grouping for F-019a, F-019b, F-019c | [TAG-MT](scope-delivery.md#tag-mt) | 20% · [evidence/fix](scope-progress.md) |
| TASK-F-020 | Legacy grouping for F-020a, F-020b | [TAG-NF](scope-delivery.md#tag-nf), [TAG-FI](scope-delivery.md#tag-fi) | 20% · [evidence/fix](scope-progress.md) |
| TASK-F-021 | Legacy grouping for T-FA, T-PA | [TAG-FA](scope-delivery.md#tag-fa), [TAG-PA](scope-delivery.md#tag-pa) | 20% · [evidence/fix](scope-progress.md) |
| TASK-F-022 | Legacy grouping for T-IV | [TAG-IV](scope-delivery.md#tag-iv) | 20% · [evidence/fix](scope-progress.md) |
| TASK-F-029 | Legacy grouping for F-029a, F-029b, F-029c | [TAG-PA](scope-delivery.md#tag-pa) | 20% · [evidence/fix](scope-progress.md) |
| TASK-N-001 | Protocol compatibility and schema migration | [WP-PROTOCOL](scope-delivery.md#wp-protocol) | 20% · [evidence/fix](scope-progress.md) |
| TASK-N-002 | Separate pending, uncertain, unsupported, unavailable, and no-finding states | [TAG-UNK](scope-delivery.md#tag-unk) | 60% · [evidence/fix](scope-progress.md) |
| TASK-N-003 | Detector resource limits, cancellation, concurrency, and failure containment | [WP-SERVICE](scope-delivery.md#wp-service) | 100% · [evidence/fix](scope-progress.md) |
| TASK-N-004 | Consent, per-site pause, capture boundaries, reset and deletion | [WP-PRIVACY](scope-delivery.md#wp-privacy) | 60% · [evidence/fix](scope-progress.md) |
| TASK-N-005 | Label dispute, correction, and supersession workflow | [WP-COMMUNITY](scope-delivery.md#wp-community) | 40% · [evidence/fix](scope-progress.md) |
| TASK-N-006 | Versioned regression checks and revalidation triggers | [WP-VALIDATION](scope-delivery.md#wp-validation) | 60% · [evidence/fix](scope-progress.md) |
| TASK-N-007 | No automated promotional AI content network | [WP-BOUNDARIES](scope-delivery.md#wp-boundaries) | 20% · [evidence/fix](scope-progress.md) |
| TASK-N-008 | No child-safety report hosting | [WP-BOUNDARIES](scope-delivery.md#wp-boundaries) | 20% · [evidence/fix](scope-progress.md) |
| TASK-N-009 | No rogue-AI verdict inferred from output | [WP-BOUNDARIES](scope-delivery.md#wp-boundaries) | 20% · [evidence/fix](scope-progress.md) |
| TASK-N-010 | Personal/team/enterprise/proprietary tag offering boundaries | [ORG-PRIVATE](scope-delivery.md#org-private) | 40% · [evidence/fix](scope-progress.md) |
| TASK-T-UC | Unsafe Command | [TAG-UC](scope-delivery.md#tag-uc) | 20% · [evidence/fix](scope-progress.md) |
| TASK-T-SC | Scam Pattern | [TAG-SC](scope-delivery.md#tag-sc) | 20% · [evidence/fix](scope-progress.md) |
| TASK-T-BT | Automation Pattern | [TAG-BT](scope-delivery.md#tag-bt) | 20% · [evidence/fix](scope-progress.md) |
| TASK-N-011 | In-house research data, training and anomaly pipeline | [WP-RESEARCH](scope-delivery.md#wp-research) | 40% · [evidence/fix](scope-progress.md) |
| TASK-N-012 | Phone and offline on-device tag checker | [WP-MOBILE](scope-delivery.md#wp-mobile) | 80% · [evidence/fix](scope-progress.md) |
| TASK-N-013 | Native iPhone sharing into a tag check | [WP-MOBILE](scope-delivery.md#wp-mobile) | 20% · [evidence/fix](scope-progress.md) |
| TASK-N-014 | Native Android sharing into a tag check | [WP-MOBILE](scope-delivery.md#wp-mobile) | 20% · [evidence/fix](scope-progress.md) |
| TASK-N-015 | Blind PS review from a phone | [WP-VALIDATION](scope-delivery.md#wp-validation) | 60% · [evidence/fix](scope-progress.md) |
