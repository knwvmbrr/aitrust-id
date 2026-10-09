# Three-layer master scope

All 202 records and their dispositions remain preserved. UC, SC and BT remain proposals; no rename or new release is implied. Jobs/outcomes define scope, not implementation. Read the [execution plan](scope-delivery.md) and [task index](scope-task-index.md) for accountable work packages. `state.json` and `runs/` hold executed truth.

| ID | Layer | Baseline job | Outcome | Work package |
|---|---|---|---|---|
| F-001 | 2 | Specify and deliver assertion envelope schema, JSON Schema 2020-12. | Any tool can read a label and know exactly what it claims | WP-PROTOCOL |
| F-002 | 2 | Specify and deliver nine-label taxonomy (plus UNK, PII_REDACTED). | A fixed vocabulary, so a label means the same thing everywhere | WP-PROTOCOL |
| F-003 | 2 | Specify and deliver signal registry, 22 registered IDs with version suffixes. | A third party can reproduce any assertion from the signal IDs it cites | WP-PROTOCOL |
| F-004 | 2 | Specify and deliver abstention as a first-class state — UNK. | The tool says "I don't know" instead of guessing at you | TAG-UNK |
| F-005 | 2 | Specify and deliver per-tag confidence floors. | No tag is shown below the confidence its evidence supports | WP-PROTOCOL |
| F-006 | 2 | Specify and deliver six-modality reservation with normative subject definitions. | Implementers agree on what is being hashed before anyone builds images or audio | WP-PROTOCOL |
| F-007 | 2 | Return hashes, offsets, and metadata without embedding evaluated text | Recipients can inspect a tag record without the assertion containing content; local content transfer is disclosed. | WP-PROTOCOL |
| F-008 | 2 | Sign an exact canonical tag record with an identified key | Recipients verify signer and record integrity without treating the signature as proof of truth. | WP-INTEGRITY |
| F-009 | 2 | Specify and deliver cost-to-defeat ladder — statistical / behavioural / structural / cryptographic. | You can judge how a label will age, not just whether it is accurate today | WP-INTEGRITY |
| F-078 | 2 | Specify and deliver conformance vectors for text and code subject hashes. | Two independent implementations produce the same hash for the same input | WP-PROTOCOL |
| F-079 | 2 | Specify and deliver five-clause privacy guarantee replacing "no content in transit or at rest". | A guarantee that is true, clause by clause, each with a test | WP-PRIVACY |
| F-080 | 2 | Specify and deliver subject hash documented as a correlation identifier, not an anonymisation. | You are not misled about what the hash protects | WP-PRIVACY |
| F-076 | 2 | Specify and deliver rFC process — template, 14-day comment, evidence requirement. | The taxonomy cannot drift into noise by accretion | WP-GOVERNANCE |
| F-077 | 2 | Specify and deliver dual licence: Apache-2.0 code, CC BY 4.0 spec. | Free use and free reimplementation, permanently | WP-GOVERNANCE |
| T-NF | 1 | Extract checkable claims and compare them with the supplied, versioned reference corpus. | The reader sees which claim is supported by which source and passage, and the limits of that support. | TAG-NF |
| T-FI | 1 | Distinguish contradicted claims from citations that cannot be resolved within the declared reference set. | The reader can inspect the contradiction or resolution failure without being told an entire author or work is fabricated. | TAG-FI |
| T-HP | 1 | Identify validated inconsistency and unsupported-specificity indicators without equating them with proven falsehood. | The reader knows which inconsistency or unsupported detail warrants checking and why. | TAG-HP |
| T-MT | 1 | Evaluate contextual pressure, constrained-choice framing and unsupported authority appeals. | The reader sees the framing and relevant context, with a measured disagreement/uncertainty boundary. | TAG-MT |
| T-PS | 1 | Complete the existing bounded command-risk release, then expand risk capabilities as separately validated increments. | The reader sees the hazardous instruction pattern before acting, with exact evidence and a challenge path. | TAG-PS |
| T-IV | 1 | Bind an explicit human review and its scope to the exact subject/version reviewed. | The reader knows who reviewed what, against which evidence and when, including withdrawal or correction. | TAG-IV |
| T-FA | 1 | Evaluate positive origin evidence for full AI generation within an explicitly observed or attested workflow. | The reader sees the origin assertion, source of evidence and supported observation window. | TAG-FA |
| T-PA | 1 | Describe supported AI contribution and subsequent human modification within the observed workflow. | The reader can distinguish documented contribution/edit events from unobserved authorship. | TAG-PA |
| T-UNK | 1 | Represent insufficient evaluated evidence separately from pending, no-finding, unsupported and unavailable results. | A reader can tell what was evaluated and why a tag could not provide its claim. | TAG-UNK |
| T-PII | 1 | Verify that supported detections were actually transformed before downstream local-service evaluation. | The reader knows what category-level transformation occurred and that detection may miss information. | TAG-PII_REDACTED |
| T-OUT | 1 | Warn about supported personal-information detections before a selected send action and let the user edit or cancel. | The user controls disclosure before sending, without an invisible copy of their prompt. | TAG-PII_OUTBOUND |
| F-010 | 1 | Specify and deliver sig.piped_installer.v1 — curl/wget piped to a shell. | A finding identifies this exact signal and the relevant subject spans. | TAG-PS |
| F-011 | 1 | Specify and deliver sig.obfuscated_payload.v1 — base64/hex into eval/exec. | A finding identifies this exact signal and the relevant subject spans. | TAG-PS |
| F-012 | 1 | Specify and deliver sig.credential_exfil.v1 — reads a secret path, writes to a network sink. | A finding identifies this exact signal and the relevant subject spans. | TAG-PS |
| F-013 | 1 | Specify and deliver sig.typosquat.v1 — package name within edit distance 1–2 of a top-N name. | A finding identifies this exact signal and the relevant subject spans. | TAG-PS |
| F-014 | 1 | Specify and deliver use/mention discriminator — is the command being recommended or discussed?. | A finding identifies this exact signal and the relevant subject spans. | TAG-PS |
| F-015 | 1 | Specify and deliver sig.unsourced_specificity.v1 — figures or dates with no provenance marker. | A finding identifies this exact signal and the relevant subject spans. | TAG-HP |
| F-016 | 1 | Specify and deliver sig.selfcontradiction.v1 — NLI entailment between sentence pairs. | A finding identifies this exact signal and the relevant subject spans. | TAG-HP |
| F-017 | 1 | Specify and deliver sig.duplicate_loop.v1 — n-gram repetition above threshold. | A finding identifies this exact signal and the relevant subject spans. | TAG-HP |
| F-018 | 1 | Specify and deliver sig.hedge_collapse.v1 — hedging absent where uncertainty is expected. | A finding identifies this exact signal and the relevant subject spans. | TAG-HP |
| F-019a | 1 | Specify and deliver sig.urgency_frame.v1 — time-pressure lexicon plus imperative density. | A finding identifies this exact signal and the relevant subject spans. | TAG-MT |
| F-019b | 1 | Specify and deliver sig.false_dilemma.v1 — binary framing where alternatives exist. | A finding identifies this exact signal and the relevant subject spans. | TAG-MT |
| F-019c | 1 | Specify and deliver sig.authority_appeal.v1 — unattributed appeals to expertise or consensus. | A finding identifies this exact signal and the relevant subject spans. | TAG-MT |
| F-020a | 1 | Specify and deliver sig.corpus_support.v1 — retrieval similarity against an attached local corpus. | A finding identifies this exact signal and the relevant subject spans. | TAG-NF |
| F-020b | 1 | Specify and deliver sig.corpus_contradiction.v1 — NLI contradiction against a retrieved passage. | A finding identifies this exact signal and the relevant subject spans. | TAG-FI |
| F-081 | 1 | Specify and deliver bring-your-own corpus — the user attaches their own reference material locally. | A finding identifies this exact signal and the relevant subject spans. | WP-REFERENCES |
| F-026 | 1 | Specify and deliver sig.keystroke_liveness.v1 — dwell and flight time distributions. | Observed interaction is documented without unsupported authorship or identity claims. | TAG-PA |
| F-027 | 1 | Specify and deliver sig.revision_churn.v1 — deleted-and-rewritten characters over final length. | Observed interaction is documented without unsupported authorship or identity claims. | TAG-PA |
| F-028 | 1 | Specify and deliver sig.compose_monotonicity.v1 — caret-position entropy. | Observed interaction is documented without unsupported authorship or identity claims. | TAG-PA |
| F-029a | 1 | Specify and deliver sig.outside_knowledge.v1 — a revision introduces something not derivable from the captured session. | Observed interaction is documented without unsupported authorship or identity claims. | TAG-PA |
| F-029b | 1 | Specify and deliver sig.attention_shape.v1 — read-pause-write rhythm from focus and visibility events. | Observed interaction is documented without unsupported authorship or identity claims. | TAG-PA |
| F-029c | 1 | Specify and deliver sig.paste_burst.v1 — large insertion with no preceding keystrokes. | Observed interaction is documented without unsupported authorship or identity claims. | TAG-PA |
| F-025 | 1 | Specify and deliver sig.c2pa_manifest.v1 — parses an attached C2PA manifest. | Observed interaction is documented without unsupported authorship or identity claims. | TAG-FA |
| F-082 | 1 | Suppress unsuitable timing analysis without assigning human attestation | Assistive-input users receive no negative authorship inference or automatic IV claim. | TAG-PA |
| F-083 | 1 | Specify and deliver the governing rule: a provenance signal may raise toward PA or FA but may never lower a tag toward a human-negative verdict. Absence of human signal produces UNK, never FA. | Observed interaction is documented without unsupported authorship or identity claims. | TAG-FA |
| F-023 | 2 | Remove recognized entities before evaluation | Detected entities are redacted; coverage and missed-detection limitations remain visible. | TAG-PII_REDACTED |
| F-041 | 2 | Specify and deliver redaction ordering guarantee — anonymise, then evaluate, always. | The order cannot silently invert in a refactor | TAG-PII_REDACTED |
| F-024 | 2 | Specify and deliver pII_OUTBOUND pre-send warning — you are about to paste personal data into a model. | Catches the mistake before it leaves your machine, not after | TAG-PII_OUTBOUND |
| F-043 | 2 | Specify and deliver no-egress network topology — internal: true, loopback binding. | Nothing you read leaves the machine during evaluation | WP-SERVICE |
| F-084 | 2 | Specify and deliver no content logging — a verified clause, not a promise. | Your text is not sitting in a log file you did not know about | WP-PRIVACY |
| F-085 | 2 | Prevent content writes in documented application paths | Verified application storage paths contain no evaluated content; operating-system limits are disclosed. | WP-PRIVACY |
| F-086 | 2 | Keep local evaluation free of automatic telemetry; separate any approved in-house research contribution under N-011. | Local tags remain usable without contributing data; remote collection is unconnected. | WP-PRIVACY |
| F-087 | 2 | Specify and deliver capture trust boundary, published plainly. | You know a label attests "this client observed this text at this time" — not who wrote it | WP-PRIVACY |
| F-030 | 2 | Specify and deliver mV3 MAIN-world capture — fetch patch plus ReadableStream.tee(). | Labels appear where you already read AI output, with no copy-paste | WP-CAPTURE |
| F-031 | 2 | Specify and deliver dOM observer fallback for sites the fetch patch misses. | Coverage when a site streams in a way the tap cannot see | WP-CAPTURE |
| F-088 | 2 | Bind every result to its captured response and content revision | Delayed or stale results never attach to a different response. | WP-CAPTURE |
| F-089 | 2 | Specify and deliver duplicate suppression — one badge per response. | You see one label, not a stack of five | WP-CAPTURE |
| F-090 | 2 | Specify and deliver character-data mutation observation. | Streamed responses that rewrite text nodes still get captured | WP-CAPTURE |
| F-032 | 2 | Debounce changes while tracking completion and content revisions | A pause is not presented as guaranteed completion; revisions invalidate stale results. | WP-CAPTURE |
| F-037 | 2 | Specify and deliver per-vendor site adapters. | Reliable capture per site instead of a guess that works sometimes | WP-CAPTURE |
| F-033 | 2 | Specify and deliver closed shadow-root badge, monochrome. | A label the page cannot read or restyle. Not spoof-proof — that claim was wrong (C8) | WP-UX |
| F-034 | 2 | Specify and deliver evidence panel showing the exact spans that triggered the tag. | You can see why, and argue with it | WP-UX |
| F-091 | 2 | Specify and deliver options page for the bearer token. | Setup actually completes | WP-PRIVACY |
| F-035 | 2 | Specify and deliver full screen-reader semantics, aria-live="polite" never assertive. | The label is announced without interrupting what you are reading | WP-UX |
| F-092 | 2 | Specify and deliver keyboard-only operation — reach, open, read, close the panel. | No mouse required, ever | WP-UX |
| F-093 | 2 | Specify and deliver forced-colors and high-contrast support. | Works in Windows High Contrast and custom colour modes | WP-UX |
| F-094 | 2 | Specify and deliver 200% zoom and reduced-motion support. | Readable magnified; no animation if you asked for none | WP-UX |
| F-095 | 2 | Specify and deliver monochrome-by-construction design — the movie/TV content-rating look. | Nothing depends on colour, so colour-blindness is a non-issue by design — and the label reads as institutional rather than as branding | WP-UX |
| F-036 | 2 | Specify and deliver signature verification before render. | The badge refuses to display a verdict it cannot authenticate | WP-INTEGRITY |
| F-096 | 2 | Specify and deliver graceful degradation — backend down, invalid token, unsupported page. | A broken setup tells you what is wrong instead of failing silently | WP-SERVICE |
| F-097 | 2 | Specify and deliver user-invoked labelling — select a response, ask for a check. | Correct attribution even when automatic capture cannot be trusted | WP-CAPTURE |
| F-040 | 2 | Specify and deliver gateway orchestration — redact, evaluate, calibrate, return. | Local tag processing exposes success and dependency failures explicitly. | WP-SERVICE |
| F-042 | 2 | Specify and deliver evaluator on redacted text only; self-reports as "rules-only". | Local tag processing exposes success and dependency failures explicitly. | WP-SERVICE |
| F-098 | 2 | Specify and deliver presidio language assets baked into the image. | Local tag processing exposes success and dependency failures explicitly. | TAG-PII_REDACTED |
| F-099 | 2 | Specify and deliver upstream response validation — status and shape checked before parsing. | Local tag processing exposes success and dependency failures explicitly. | WP-SERVICE |
| F-100 | 2 | Specify and deliver constant-time bearer token comparison. | Local tag processing exposes success and dependency failures explicitly. | WP-SERVICE |
| F-101 | 2 | Specify and deliver startup refusal of the example token change-me. | Local tag processing exposes success and dependency failures explicitly. | WP-SERVICE |
| F-102 | 2 | Specify and deliver modality validated against the schema enum; unsupported returns UNK + unsupported_modality. | Local tag processing exposes success and dependency failures explicitly. | WP-SERVICE |
| F-103 | 2 | Specify and deliver health checks reporting dependency readiness, not process liveness. | Local tag processing exposes success and dependency failures explicitly. | WP-SERVICE |
| F-104 | 2 | Specify and deliver defined dependency-failure behaviour. | Local tag processing exposes success and dependency failures explicitly. | WP-SERVICE |
| F-044 | 2 | Specify and deliver registry dashboard — hashes only, 30-day retention. | Local tag processing exposes success and dependency failures explicitly. | ORG-AUDIT |
| F-045 | 2 | Specify and deliver reporting intake, hash-only. | Local tag processing exposes success and dependency failures explicitly. | ORG-AUDIT |
| F-105 | 2 | Specify and deliver one documented command: clean clone → running stack. | Local tag processing exposes success and dependency failures explicitly. | WP-MOBILE |
| F-050 | 2 | Specify and deliver gate thresholds in eval/gates.yaml — precision, recall, ECE, abstention band, latency, axe, α. | Versioned verification evidence determines whether the applicable acceptance criteria passed. | WP-VALIDATION |
| F-051 | 2 | Derive metrics from evaluator outputs on versioned fixtures | Reports expose confusion counts, denominators, category failures, and applicable uncertainty. | WP-VALIDATION |
| F-106 | 2 | Specify and deliver wilson confidence intervals, lower-bound gating, n published beside every figure. | Versioned verification evidence determines whether the applicable acceptance criteria passed. | WP-VALIDATION |
| F-107 | 2 | Specify and deliver per-category failure breakdown on every metric. | Versioned verification evidence determines whether the applicable acceptance criteria passed. | WP-VALIDATION |
| F-052 | 2 | Specify and deliver pS fixture set. | Versioned verification evidence determines whether the applicable acceptance criteria passed. | TAG-PS |
| F-108 | 2 | Specify and deliver frozen held-out split with a manifest hash, separate from the regression suite. | Versioned verification evidence determines whether the applicable acceptance criteria passed. | WP-VALIDATION |
| F-109 | 2 | Specify and deliver dataset versioning and provenance per example. | Versioned verification evidence determines whether the applicable acceptance criteria passed. | WP-VALIDATION |
| F-110 | 2 | Specify and deliver adversarial boundary examples for the use/mention discriminator. | Versioned verification evidence determines whether the applicable acceptance criteria passed. | TAG-PS |
| F-053 | 2 | Specify and deliver hP / MT / FI fixtures. | Versioned verification evidence determines whether the applicable acceptance criteria passed. | WP-VALIDATION |
| F-056 | 2 | Specify and deliver krippendorff's α published for MT, ≥ 0.55. | Versioned verification evidence determines whether the applicable acceptance criteria passed. | TAG-MT |
| F-054 | 2 | Specify and deliver cI that can actually fail. | Versioned verification evidence determines whether the applicable acceptance criteria passed. | WP-RELEASE |
| F-111 | 2 | Specify and deliver evaluator unit tests — the first tests in the repository. | Versioned verification evidence determines whether the applicable acceptance criteria passed. | WP-RELEASE |
| F-112 | 2 | Specify and deliver schema validation against real service responses, not just schema syntax. | Versioned verification evidence determines whether the applicable acceptance criteria passed. | WP-RELEASE |
| F-055 | 2 | Specify and deliver axe-core accessibility gate, serious and critical at zero. | Versioned verification evidence determines whether the applicable acceptance criteria passed. | WP-UX |
| F-113 | 2 | Specify and deliver latency budget enforcement — p95 ≤ 100ms. | Versioned verification evidence determines whether the applicable acceptance criteria passed. | WP-RELEASE |
| F-114 | 2 | Specify and deliver abstention-rate band enforcement, 0.02–0.35. | Versioned verification evidence determines whether the applicable acceptance criteria passed. | WP-VALIDATION |
| F-115 | 2 | Specify and deliver network-isolation verification — exec into each container and prove it cannot reach out. | Versioned verification evidence determines whether the applicable acceptance criteria passed. | WP-SERVICE |
| F-057 | 2 | Specify and deliver sBOM plus Sigstore release signing. | Versioned verification evidence determines whether the applicable acceptance criteria passed. | WP-RELEASE |
| F-116 | 2 | Specify and deliver dependency lockfiles and hashes, not just version pins. | Versioned verification evidence determines whether the applicable acceptance criteria passed. | WP-RELEASE |
| F-117 | 2 | Specify and deliver model hash verification at load. | Versioned verification evidence determines whether the applicable acceptance criteria passed. | WP-RELEASE |
| F-118 | 2 | Specify and deliver calibration ledger — every published number reproducible by a third party. | Versioned verification evidence determines whether the applicable acceptance criteria passed. | WP-VALIDATION |
| F-119 | 2 | Specify and deliver conformance test suite an outside implementer can run against their own build. | Versioned verification evidence determines whether the applicable acceptance criteria passed. | WP-RELEASE |
| F-120 | 2 | Specify and deliver evidence packets — committed transcripts per exit gate. | Versioned verification evidence determines whether the applicable acceptance criteria passed. | WP-RELEASE |
| F-121 | 1 | Specify and deliver receipt format binding an artifact hash to observed composition activity. | An author or verifier can inspect the defined composition evidence and its limits. | WP-RECEIPTS |
| F-122 | 1 | Specify and deliver receipt issuance — always a free path, by policy. | An author or verifier can inspect the defined composition evidence and its limits. | WP-RECEIPTS |
| F-123 | 1 | Specify and deliver receipt verification requiring no contact with us. | An author or verifier can inspect the defined composition evidence and its limits. | WP-RECEIPTS |
| F-124 | 1 | Specify and deliver independent RFC 3161 timestamping — we never operate the authority. | An author or verifier can inspect the defined composition evidence and its limits. | WP-RECEIPTS |
| F-125 | 1 | Specify and deliver per-device revocable keys plus a revocation transparency log. | An author or verifier can inspect the defined composition evidence and its limits. | WP-RECEIPTS |
| F-126 | 1 | Specify and deliver freshness model for offline verification against revocation. | An author or verifier can inspect the defined composition evidence and its limits. | WP-RECEIPTS |
| F-127 | 1 | Specify and deliver forgery-cost class as a first-class field on every receipt. | An author or verifier can inspect the defined composition evidence and its limits. | WP-RECEIPTS |
| F-128 | 1 | Specify and deliver anti-coercion rule — a conformant implementation may not make receipt issuance non-optional for the author. | An author or verifier can inspect the defined composition evidence and its limits. | WP-RECEIPTS |
| F-129 | 1 | Specify and deliver key custody and recovery for a non-technical author. | An author or verifier can inspect the defined composition evidence and its limits. | WP-RECEIPTS |
| F-130 | 1 | Specify and deliver group authorship — four signers or four receipts. | An author or verifier can inspect the defined composition evidence and its limits. | WP-RECEIPTS |
| F-131 | 1 | Specify and deliver receipt expiry and algorithm agility — ed25519 will not be safe forever. | An author or verifier can inspect the defined composition evidence and its limits. | WP-RECEIPTS |
| F-132 | 3 | Specify and deliver aitrustid.com — landing and reference content, no-JS core. | A person can access the public tag workflow and its support process. | WP-SITE |
| F-133 | 3 | Specify and deliver public status table distinguishing supported / experimental / reserved. | A person can access the public tag workflow and its support process. | WP-SITE |
| F-134 | 3 | Specify and deliver limitations page, findable without being told where it is. | A person can access the public tag workflow and its support process. | WP-SITE |
| F-135 | 3 | Specify and deliver report AI — public intake for AI content people want flagged. | A person can access the public tag workflow and its support process. | WP-COMMUNITY |
| F-136 | 3 | Provide public live community discussions and official replies with safe publication controls. | Everyone can read public community messages and company replies; private reports and research remain outside the public stream. | WP-COMMUNITY |
| F-137 | 3 | Apply a documented moderation and appeal process with public safe action records. | People see moderation reasons and appeal routes without removed secrets, private reports or reporter identities being republished. | WP-COMMUNITY |
| F-073 | 3 | Specify and deliver security@ with a 72-hour response promise. | A person can access the public tag workflow and its support process. | WP-OPERATIONS |
| F-074 | 3 | Specify and deliver conduct@ with an enforcement ladder. | A person can access the public tag workflow and its support process. | WP-COMMUNITY |
| F-138 | 3 | Specify and deliver abuse@ and press@. | A person can access the public tag workflow and its support process. | WP-COMMUNITY |
| F-139 | 3 | Specify and deliver site accessibility held to the same gate as the extension. | A person can access the public tag workflow and its support process. | WP-SITE |
| F-140 | 3 | Specify and deliver sanitised public roadmap — no personal execution material. | A person can access the public tag workflow and its support process. | WP-SITE |
| F-141 | 3 | Specify and deliver pilot programme — small consenting group, feedback without collecting prompts or outputs. | A person can access the public tag workflow and its support process. | WP-COMMUNITY |
| F-142 | 3 | Specify and deliver install and removal instructions, reproducible. | A person can access the public tag workflow and its support process. | WP-SITE |
| F-075 | 3 | Specify and deliver two-entity structure — independent foundation holds spec and mark; implementations compete on top. | Responsibilities and decisions are documented without implying an operating institution exists. | WP-GOVERNANCE |
| F-143 | 3 | Specify and deliver certification mark — filed, owned by the foundation. | Responsibilities and decisions are documented without implying an operating institution exists. | WP-GOVERNANCE |
| F-144 | 3 | Specify and deliver mark usage guidelines and a conformance statement template. | Responsibilities and decisions are documented without implying an operating institution exists. | WP-GOVERNANCE |
| F-145 | 3 | Specify and deliver certification programme — what a certifier must test, and how one is accredited. | Responsibilities and decisions are documented without implying an operating institution exists. | WP-GOVERNANCE |
| F-146 | 3 | Specify and deliver nonprofit formation and filings. | Responsibilities and decisions are documented without implying an operating institution exists. | WP-GOVERNANCE |
| F-147 | 3 | Specify and deliver conflict-of-interest recusal rule for maintainers with a commercial interest. | Responsibilities and decisions are documented without implying an operating institution exists. | WP-GOVERNANCE |
| F-148 | 3 | Specify and deliver qualified legal review of every biometric and privacy assurance. | Responsibilities and decisions are documented without implying an operating institution exists. | WP-GOVERNANCE |
| F-070 | 3 | Specify and deliver six invariants in CONTRIBUTING.md. | Responsibilities and decisions are documented without implying an operating institution exists. | WP-GOVERNANCE |
| F-071 | 3 | Specify and deliver threat model, 10 entries. | Responsibilities and decisions are documented without implying an operating institution exists. | WP-OPERATIONS |
| F-072 | 3 | Specify and deliver aCCESSIBILITY.md as a release gate. | Responsibilities and decisions are documented without implying an operating institution exists. | WP-UX |
| F-149 | 3 | Specify and deliver mAINTAINERS.md with per-maintainer scope. | Responsibilities and decisions are documented without implying an operating institution exists. | WP-GOVERNANCE |
| F-150 | 3 | Specify and deliver cHANGELOG.md, state.json, docs/, runs/. | Responsibilities and decisions are documented without implying an operating institution exists. | WP-OPERATIONS |
| F-151 | 3 | Specify and deliver dECISIONS.md — 15 seeded decisions with dates and reasons. | Responsibilities and decisions are documented without implying an operating institution exists. | WP-GOVERNANCE |
| F-152 | 3 | Specify and deliver branch protection, CODEOWNERS, required status checks, Dependabot. | Responsibilities and decisions are documented without implying an operating institution exists. | WP-OPERATIONS |
| F-153 | 3 | Specify and deliver named ongoing ownership for security response and adapter maintenance. | Responsibilities and decisions are documented without implying an operating institution exists. | WP-OPERATIONS |
| F-060 | 1 | Specify and deliver image. | Independent implementers have an explicit subject contract before support is claimed. | WP-MODALITIES |
| F-061 | 1 | Specify and deliver audio. | Independent implementers have an explicit subject contract before support is claimed. | WP-MODALITIES |
| F-062 | 1 | Specify and deliver video. | Independent implementers have an explicit subject contract before support is claimed. | WP-MODALITIES |
| F-063 | 1 | Specify and deliver document. | Independent implementers have an explicit subject contract before support is claimed. | WP-MODALITIES |
| F-154 | 1 | Specify and deliver text and code subject contracts. | Independent implementers have an explicit subject contract before support is claimed. | WP-MODALITIES |
| F-155 | 3 | Specify and deliver synthID and vendor watermarking. | The application extends supported tags without disabling the personal workflow. | WP-INTEGRATIONS |
| F-156 | 3 | Specify and deliver additional browser and site adapters. | The application extends supported tags without disabling the personal workflow. | WP-INTEGRATIONS |
| F-157 | 3 | Specify and deliver newsroom integration — labels in an editorial workflow. | The application extends supported tags without disabling the personal workflow. | WP-INTEGRATIONS |
| F-158 | 3 | Specify and deliver agent identity — labelling output from autonomous agents. | The application extends supported tags without disabling the personal workflow. | WP-INTEGRATIONS |
| F-159 | 3 | Specify and deliver fleet deployment and policy management. | The application extends supported tags without disabling the personal workflow. | ORG-FLEET |
| F-160 | 3 | Specify and deliver host-level capture agents. | The application extends supported tags without disabling the personal workflow. | ORG-HOST |
| F-161 | 3 | Specify and deliver long-horizon retention and audit trails. | The application extends supported tags without disabling the personal workflow. | ORG-AUDIT |
| F-162 | 3 | Specify and deliver sSO and directory integration. | The application extends supported tags without disabling the personal workflow. | ORG-SSO |
| F-163 | 3 | Specify and deliver support with an SLA. | The application extends supported tags without disabling the personal workflow. | ORG-SUPPORT |
| X-01 | 2 | Prevent introduction of: A paid API or any metered inference | The product excludes a paid api or any metered inference, and changes are reviewed against this boundary. | WP-BOUNDARIES |
| X-02 | 2 | Prevent introduction of: Any closed-source or paid dependency in the pipeline | The product excludes any closed-source or paid dependency in the pipeline, and changes are reviewed against this boundary. | WP-BOUNDARIES |
| X-03 | 2 | Prevent unapproved central collection; review consented in-house research storage under N-011. | No central collection is active; provider, consent and retention must be resolved before connection. | WP-BOUNDARIES |
| X-04 | 2 | Prevent introduction of: Per-person keystroke templates or any biometric identity profile | The product excludes per-person keystroke templates or any biometric identity profile, and changes are reviewed against this boundary. | WP-BOUNDARIES |
| X-05 | 2 | Prevent introduction of: Any human-negative verdict from an absent signal | The product excludes any human-negative verdict from an absent signal, and changes are reviewed against this boundary. | WP-BOUNDARIES |
| X-06 | 2 | Keep automatic telemetry disabled; treat approved research contribution as a separate consented workflow. | Using a tag does not automatically upload usage or content; collection remains unconnected. | WP-BOUNDARIES |
| X-07 | 2 | Prevent introduction of: Competing with C2PA on image provenance | The product excludes competing with c2pa on image provenance, and changes are reviewed against this boundary. | WP-BOUNDARIES |
| X-08 | 2 | Defer from the initial release: Building image, audio or video detection in 1.0 | The capability remains tracked for a later release and is not advertised as supported. | WP-BOUNDARIES |
| X-09 | 2 | Prevent introduction of: Colour-coded labels | The product excludes colour-coded labels, and changes are reviewed against this boundary. | WP-BOUNDARIES |
| X-10 | 2 | Prevent introduction of: aria-live="assertive" announcements | The product excludes aria-live="assertive" announcements, and changes are reviewed against this boundary. | WP-BOUNDARIES |
| X-11 | 2 | Prevent introduction of: Machine-assigned IV | The product excludes machine-assigned iv, and changes are reviewed against this boundary. | WP-BOUNDARIES |
| X-12 | 2 | Prevent introduction of: Mandatory receipts | The product excludes mandatory receipts, and changes are reviewed against this boundary. | WP-BOUNDARIES |
| X-13 | 2 | Defer from the initial release: Signing in 0.1 | The capability remains tracked for a later release and is not advertised as supported. | WP-BOUNDARIES |
| X-14 | 2 | Defer from the initial release: The registry container in 0.1 | The capability remains tracked for a later release and is not advertised as supported. | WP-BOUNDARIES |
| X-15 | 2 | Prevent introduction of: Collecting prompts or outputs from pilot users | The product excludes collecting prompts or outputs from pilot users, and changes are reviewed against this boundary. | WP-BOUNDARIES |
| X-16 | 2 | Prevent introduction of: "Outside knowledge proves human authorship" as an implementation requirement | The product excludes "outside knowledge proves human authorship" as an implementation requirement, and changes are reviewed against this boundary. | WP-BOUNDARIES |
| F-019 | 1 | Specify and deliver legacy grouping for F-019a, F-019b, F-019c. | The named capability has observable behavior and is tracked independently of implementation status. | TAG-MT |
| F-020 | 1 | Specify and deliver legacy grouping for F-020a, F-020b. | The named capability has observable behavior and is tracked independently of implementation status. | TAG-NF, TAG-FI |
| F-021 | 1 | Specify and deliver legacy grouping for T-FA, T-PA. | The named capability has observable behavior and is tracked independently of implementation status. | TAG-FA, TAG-PA |
| F-022 | 1 | Specify and deliver legacy grouping for T-IV. | The named capability has observable behavior and is tracked independently of implementation status. | TAG-IV |
| F-029 | 1 | Specify and deliver legacy grouping for F-029a, F-029b, F-029c. | The named capability has observable behavior and is tracked independently of implementation status. | TAG-PA |
| N-001 | 2 | Specify and deliver protocol compatibility and schema migration. | The named capability has observable behavior and is tracked independently of implementation status. | WP-PROTOCOL |
| N-002 | 2 | Specify and deliver separate pending, uncertain, unsupported, unavailable, and no-finding states. | The named capability has observable behavior and is tracked independently of implementation status. | TAG-UNK |
| N-003 | 2 | Specify and deliver detector resource limits, cancellation, concurrency, and failure containment. | The named capability has observable behavior and is tracked independently of implementation status. | WP-SERVICE |
| N-004 | 2 | Specify and deliver consent, per-site pause, capture boundaries, reset and deletion. | The named capability has observable behavior and is tracked independently of implementation status. | WP-PRIVACY |
| N-005 | 2 | Specify and deliver label dispute, correction, and supersession workflow. | The named capability has observable behavior and is tracked independently of implementation status. | WP-COMMUNITY |
| N-006 | 2 | Specify and deliver versioned regression checks and revalidation triggers. | The named capability has observable behavior and is tracked independently of implementation status. | WP-VALIDATION |
| N-007 | 3 | Specify and deliver no automated promotional AI content network. | The named capability has observable behavior and is tracked independently of implementation status. | WP-BOUNDARIES |
| N-008 | 3 | Specify and deliver no child-safety report hosting. | The named capability has observable behavior and is tracked independently of implementation status. | WP-BOUNDARIES |
| N-009 | 1 | Specify and deliver no rogue-AI verdict inferred from output. | The named capability has observable behavior and is tracked independently of implementation status. | WP-BOUNDARIES |
| N-010 | 3 | Specify and deliver personal/team/enterprise/proprietary tag offering boundaries. | The named capability has observable behavior and is tracked independently of implementation status. | ORG-PRIVATE |
| T-UC | 1 | Research a clearer command-risk tag name/claim while preserving PS until a change is accepted. | A proposed migration explains exactly which meaning changes and how old PS records remain interpretable. | TAG-UC |
| T-SC | 1 | Research whether contextual fraud indicators support a useful, bounded possible-scam finding. | The reader can inspect each validated indicator and dismiss a warning without an accusation of intent. | TAG-SC |
| T-BT | 1 | Research positive automation evidence without judging people from style, speed or absent human signals. | A finding reports supported automation evidence within a defined workflow, without labeling an ordinary person a bot. | TAG-BT |
| N-011 | 3 | Organize approved tag outputs in a remotely hosted, controlled open-source data stack for independently reviewed training and pattern analysis. | Versioned records, independent labels and approved examples support reproducible improvement without making collection a dependency of local tags. | WP-RESEARCH |
| N-012 | 3 | Run a version-bound tag method on a phone without an account, extension or local containers. | A person copies an answer from any app and receives a bounded PS preview without uploading the answer. | WP-MOBILE |
| N-013 | 3 | Receive selected text through an iPhone Share extension with explicit user action. | A person checks shared text without manual copy-and-paste while retaining control of disclosure. | WP-MOBILE |
| N-014 | 3 | Receive selected text through an Android OS share interface with explicit user action. | A person checks shared text without manual copy-and-paste while retaining control of disclosure. | WP-MOBILE |
| N-015 | 3 | Read a frozen reviewer JSON file, collect independent labels and export exact item fields for comparison. | Reviewers can label without developer setup or detector predictions; incomplete and changed files fail coordinator comparison. | WP-VALIDATION |
