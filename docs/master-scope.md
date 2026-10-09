# Three-layer master scope

All legacy IDs are retained. UC, SC, and BT remain proposals under RFC-0004; PS is not silently renamed. Baseline jobs and outcomes are scope definitions, not implementation claims. Source legal and pricing assertions are not adopted.

| ID | Layer | Baseline job | Outcome |
|---|---|---|---|
| F-001 | 2 | Specify and deliver assertion envelope schema, JSON Schema 2020-12. | Any tool can read a label and know exactly what it claims |
| F-002 | 2 | Specify and deliver nine-label taxonomy (plus UNK, PII_REDACTED). | A fixed vocabulary, so a label means the same thing everywhere |
| F-003 | 2 | Specify and deliver signal registry, 22 registered IDs with version suffixes. | A third party can reproduce any assertion from the signal IDs it cites |
| F-004 | 2 | Specify and deliver abstention as a first-class state — UNK. | The tool says "I don't know" instead of guessing at you |
| F-005 | 2 | Specify and deliver per-tag confidence floors. | No tag is shown below the confidence its evidence supports |
| F-006 | 2 | Specify and deliver six-modality reservation with normative subject definitions. | Implementers agree on what is being hashed before anyone builds images or audio |
| F-007 | 2 | Return hashes, offsets, and metadata without embedding evaluated text | Recipients can inspect a tag record without the assertion containing content; local content transfer is disclosed. |
| F-008 | 2 | Sign an exact canonical tag record with an identified key | Recipients verify signer and record integrity without treating the signature as proof of truth. |
| F-009 | 2 | Specify and deliver cost-to-defeat ladder — statistical / behavioural / structural / cryptographic. | You can judge how a label will age, not just whether it is accurate today |
| F-078 | 2 | Specify and deliver conformance vectors for text and code subject hashes. | Two independent implementations produce the same hash for the same input |
| F-079 | 2 | Specify and deliver five-clause privacy guarantee replacing "no content in transit or at rest". | A guarantee that is true, clause by clause, each with a test |
| F-080 | 2 | Specify and deliver subject hash documented as a correlation identifier, not an anonymisation. | You are not misled about what the hash protects |
| F-076 | 2 | Specify and deliver rFC process — template, 14-day comment, evidence requirement. | The taxonomy cannot drift into noise by accretion |
| F-077 | 2 | Specify and deliver dual licence: Apache-2.0 code, CC BY 4.0 spec. | Free use and free reimplementation, permanently |
| T-NF | 1 | Specify and deliver nF Non-Fiction. | A recipient sees the bounded claim, supporting evidence, and its uncertainty. |
| T-FI | 1 | Specify and deliver fI Fiction / Fabricated. | A recipient sees the bounded claim, supporting evidence, and its uncertainty. |
| T-HP | 1 | Specify and deliver hP Hallucination Possible. | A recipient sees the bounded claim, supporting evidence, and its uncertainty. |
| T-MT | 1 | Specify and deliver mT Manipulative Tactic. | A recipient sees the bounded claim, supporting evidence, and its uncertainty. |
| T-PS | 1 | Specify and deliver pS Potential Scam / Risk. | A recipient sees the bounded claim, supporting evidence, and its uncertainty. |
| T-IV | 1 | Specify and deliver iV Independently Verified. | A recipient sees the bounded claim, supporting evidence, and its uncertainty. |
| T-FA | 1 | Specify and deliver fA Full AI Augmentation. | A recipient sees the bounded claim, supporting evidence, and its uncertainty. |
| T-PA | 1 | Specify and deliver pA Partially Augmented. | A recipient sees the bounded claim, supporting evidence, and its uncertainty. |
| T-UNK | 1 | Specify and deliver uNK Unknown. | A recipient sees the bounded claim, supporting evidence, and its uncertainty. |
| T-PII | 1 | Specify and deliver pII_REDACTED. | A recipient sees the bounded claim, supporting evidence, and its uncertainty. |
| T-OUT | 1 | Specify and deliver pII_OUTBOUND. | A recipient sees the bounded claim, supporting evidence, and its uncertainty. |
| F-010 | 1 | Specify and deliver sig.piped_installer.v1 — curl/wget piped to a shell. | A finding identifies this exact signal and the relevant subject spans. |
| F-011 | 1 | Specify and deliver sig.obfuscated_payload.v1 — base64/hex into eval/exec. | A finding identifies this exact signal and the relevant subject spans. |
| F-012 | 1 | Specify and deliver sig.credential_exfil.v1 — reads a secret path, writes to a network sink. | A finding identifies this exact signal and the relevant subject spans. |
| F-013 | 1 | Specify and deliver sig.typosquat.v1 — package name within edit distance 1–2 of a top-N name. | A finding identifies this exact signal and the relevant subject spans. |
| F-014 | 1 | Specify and deliver use/mention discriminator — is the command being recommended or discussed?. | A finding identifies this exact signal and the relevant subject spans. |
| F-015 | 1 | Specify and deliver sig.unsourced_specificity.v1 — figures or dates with no provenance marker. | A finding identifies this exact signal and the relevant subject spans. |
| F-016 | 1 | Specify and deliver sig.selfcontradiction.v1 — NLI entailment between sentence pairs. | A finding identifies this exact signal and the relevant subject spans. |
| F-017 | 1 | Specify and deliver sig.duplicate_loop.v1 — n-gram repetition above threshold. | A finding identifies this exact signal and the relevant subject spans. |
| F-018 | 1 | Specify and deliver sig.hedge_collapse.v1 — hedging absent where uncertainty is expected. | A finding identifies this exact signal and the relevant subject spans. |
| F-019a | 1 | Specify and deliver sig.urgency_frame.v1 — time-pressure lexicon plus imperative density. | A finding identifies this exact signal and the relevant subject spans. |
| F-019b | 1 | Specify and deliver sig.false_dilemma.v1 — binary framing where alternatives exist. | A finding identifies this exact signal and the relevant subject spans. |
| F-019c | 1 | Specify and deliver sig.authority_appeal.v1 — unattributed appeals to expertise or consensus. | A finding identifies this exact signal and the relevant subject spans. |
| F-020a | 1 | Specify and deliver sig.corpus_support.v1 — retrieval similarity against an attached local corpus. | A finding identifies this exact signal and the relevant subject spans. |
| F-020b | 1 | Specify and deliver sig.corpus_contradiction.v1 — NLI contradiction against a retrieved passage. | A finding identifies this exact signal and the relevant subject spans. |
| F-081 | 1 | Specify and deliver bring-your-own corpus — the user attaches their own reference material locally. | A finding identifies this exact signal and the relevant subject spans. |
| F-026 | 1 | Specify and deliver sig.keystroke_liveness.v1 — dwell and flight time distributions. | Observed interaction is documented without unsupported authorship or identity claims. |
| F-027 | 1 | Specify and deliver sig.revision_churn.v1 — deleted-and-rewritten characters over final length. | Observed interaction is documented without unsupported authorship or identity claims. |
| F-028 | 1 | Specify and deliver sig.compose_monotonicity.v1 — caret-position entropy. | Observed interaction is documented without unsupported authorship or identity claims. |
| F-029a | 1 | Specify and deliver sig.outside_knowledge.v1 — a revision introduces something not derivable from the captured session. | Observed interaction is documented without unsupported authorship or identity claims. |
| F-029b | 1 | Specify and deliver sig.attention_shape.v1 — read-pause-write rhythm from focus and visibility events. | Observed interaction is documented without unsupported authorship or identity claims. |
| F-029c | 1 | Specify and deliver sig.paste_burst.v1 — large insertion with no preceding keystrokes. | Observed interaction is documented without unsupported authorship or identity claims. |
| F-025 | 1 | Specify and deliver sig.c2pa_manifest.v1 — parses an attached C2PA manifest. | Observed interaction is documented without unsupported authorship or identity claims. |
| F-082 | 1 | Suppress unsuitable timing analysis without assigning human attestation | Assistive-input users receive no negative authorship inference or automatic IV claim. |
| F-083 | 1 | Specify and deliver the governing rule: a provenance signal may raise toward PA or FA but may never lower a tag toward a human-negative verdict. Absence of human signal produces UNK, never FA. | Observed interaction is documented without unsupported authorship or identity claims. |
| F-023 | 2 | Remove recognized entities before evaluation | Detected entities are redacted; coverage and missed-detection limitations remain visible. |
| F-041 | 2 | Specify and deliver redaction ordering guarantee — anonymise, then evaluate, always. | The order cannot silently invert in a refactor |
| F-024 | 2 | Specify and deliver pII_OUTBOUND pre-send warning — you are about to paste personal data into a model. | Catches the mistake before it leaves your machine, not after |
| F-043 | 2 | Specify and deliver no-egress network topology — internal: true, loopback binding. | Nothing you read leaves the machine during evaluation |
| F-084 | 2 | Specify and deliver no content logging — a verified clause, not a promise. | Your text is not sitting in a log file you did not know about |
| F-085 | 2 | Prevent content writes in documented application paths | Verified application storage paths contain no evaluated content; operating-system limits are disclosed. |
| F-086 | 2 | Keep local evaluation free of automatic telemetry; separate any approved in-house research contribution under N-011. | Local tags remain usable without contributing data; remote collection is unconnected. |
| F-087 | 2 | Specify and deliver capture trust boundary, published plainly. | You know a label attests "this client observed this text at this time" — not who wrote it |
| F-030 | 2 | Specify and deliver mV3 MAIN-world capture — fetch patch plus ReadableStream.tee(). | Labels appear where you already read AI output, with no copy-paste |
| F-031 | 2 | Specify and deliver dOM observer fallback for sites the fetch patch misses. | Coverage when a site streams in a way the tap cannot see |
| F-088 | 2 | Bind every result to its captured response and content revision | Delayed or stale results never attach to a different response. |
| F-089 | 2 | Specify and deliver duplicate suppression — one badge per response. | You see one label, not a stack of five |
| F-090 | 2 | Specify and deliver character-data mutation observation. | Streamed responses that rewrite text nodes still get captured |
| F-032 | 2 | Debounce changes while tracking completion and content revisions | A pause is not presented as guaranteed completion; revisions invalidate stale results. |
| F-037 | 2 | Specify and deliver per-vendor site adapters. | Reliable capture per site instead of a guess that works sometimes |
| F-033 | 2 | Specify and deliver closed shadow-root badge, monochrome. | A label the page cannot read or restyle. Not spoof-proof — that claim was wrong (C8) |
| F-034 | 2 | Specify and deliver evidence panel showing the exact spans that triggered the tag. | You can see why, and argue with it |
| F-091 | 2 | Specify and deliver options page for the bearer token. | Setup actually completes |
| F-035 | 2 | Specify and deliver full screen-reader semantics, aria-live="polite" never assertive. | The label is announced without interrupting what you are reading |
| F-092 | 2 | Specify and deliver keyboard-only operation — reach, open, read, close the panel. | No mouse required, ever |
| F-093 | 2 | Specify and deliver forced-colors and high-contrast support. | Works in Windows High Contrast and custom colour modes |
| F-094 | 2 | Specify and deliver 200% zoom and reduced-motion support. | Readable magnified; no animation if you asked for none |
| F-095 | 2 | Specify and deliver monochrome-by-construction design — the movie/TV content-rating look. | Nothing depends on colour, so colour-blindness is a non-issue by design — and the label reads as institutional rather than as branding |
| F-036 | 2 | Specify and deliver signature verification before render. | The badge refuses to display a verdict it cannot authenticate |
| F-096 | 2 | Specify and deliver graceful degradation — backend down, invalid token, unsupported page. | A broken setup tells you what is wrong instead of failing silently |
| F-097 | 2 | Specify and deliver user-invoked labelling — select a response, ask for a check. | Correct attribution even when automatic capture cannot be trusted |
| F-040 | 2 | Specify and deliver gateway orchestration — redact, evaluate, calibrate, return. | Local tag processing exposes success and dependency failures explicitly. |
| F-042 | 2 | Specify and deliver evaluator on redacted text only; self-reports as "rules-only". | Local tag processing exposes success and dependency failures explicitly. |
| F-098 | 2 | Specify and deliver presidio language assets baked into the image. | Local tag processing exposes success and dependency failures explicitly. |
| F-099 | 2 | Specify and deliver upstream response validation — status and shape checked before parsing. | Local tag processing exposes success and dependency failures explicitly. |
| F-100 | 2 | Specify and deliver constant-time bearer token comparison. | Local tag processing exposes success and dependency failures explicitly. |
| F-101 | 2 | Specify and deliver startup refusal of the example token change-me. | Local tag processing exposes success and dependency failures explicitly. |
| F-102 | 2 | Specify and deliver modality validated against the schema enum; unsupported returns UNK + unsupported_modality. | Local tag processing exposes success and dependency failures explicitly. |
| F-103 | 2 | Specify and deliver health checks reporting dependency readiness, not process liveness. | Local tag processing exposes success and dependency failures explicitly. |
| F-104 | 2 | Specify and deliver defined dependency-failure behaviour. | Local tag processing exposes success and dependency failures explicitly. |
| F-044 | 2 | Specify and deliver registry dashboard — hashes only, 30-day retention. | Local tag processing exposes success and dependency failures explicitly. |
| F-045 | 2 | Specify and deliver reporting intake, hash-only. | Local tag processing exposes success and dependency failures explicitly. |
| F-105 | 2 | Specify and deliver one documented command: clean clone → running stack. | Local tag processing exposes success and dependency failures explicitly. |
| F-050 | 2 | Specify and deliver gate thresholds in eval/gates.yaml — precision, recall, ECE, abstention band, latency, axe, α. | Versioned verification evidence determines whether the applicable acceptance criteria passed. |
| F-051 | 2 | Derive metrics from evaluator outputs on versioned fixtures | Reports expose confusion counts, denominators, category failures, and applicable uncertainty. |
| F-106 | 2 | Specify and deliver wilson confidence intervals, lower-bound gating, n published beside every figure. | Versioned verification evidence determines whether the applicable acceptance criteria passed. |
| F-107 | 2 | Specify and deliver per-category failure breakdown on every metric. | Versioned verification evidence determines whether the applicable acceptance criteria passed. |
| F-052 | 2 | Specify and deliver pS fixture set. | Versioned verification evidence determines whether the applicable acceptance criteria passed. |
| F-108 | 2 | Specify and deliver frozen held-out split with a manifest hash, separate from the regression suite. | Versioned verification evidence determines whether the applicable acceptance criteria passed. |
| F-109 | 2 | Specify and deliver dataset versioning and provenance per example. | Versioned verification evidence determines whether the applicable acceptance criteria passed. |
| F-110 | 2 | Specify and deliver adversarial boundary examples for the use/mention discriminator. | Versioned verification evidence determines whether the applicable acceptance criteria passed. |
| F-053 | 2 | Specify and deliver hP / MT / FI fixtures. | Versioned verification evidence determines whether the applicable acceptance criteria passed. |
| F-056 | 2 | Specify and deliver krippendorff's α published for MT, ≥ 0.55. | Versioned verification evidence determines whether the applicable acceptance criteria passed. |
| F-054 | 2 | Specify and deliver cI that can actually fail. | Versioned verification evidence determines whether the applicable acceptance criteria passed. |
| F-111 | 2 | Specify and deliver evaluator unit tests — the first tests in the repository. | Versioned verification evidence determines whether the applicable acceptance criteria passed. |
| F-112 | 2 | Specify and deliver schema validation against real service responses, not just schema syntax. | Versioned verification evidence determines whether the applicable acceptance criteria passed. |
| F-055 | 2 | Specify and deliver axe-core accessibility gate, serious and critical at zero. | Versioned verification evidence determines whether the applicable acceptance criteria passed. |
| F-113 | 2 | Specify and deliver latency budget enforcement — p95 ≤ 100ms. | Versioned verification evidence determines whether the applicable acceptance criteria passed. |
| F-114 | 2 | Specify and deliver abstention-rate band enforcement, 0.02–0.35. | Versioned verification evidence determines whether the applicable acceptance criteria passed. |
| F-115 | 2 | Specify and deliver network-isolation verification — exec into each container and prove it cannot reach out. | Versioned verification evidence determines whether the applicable acceptance criteria passed. |
| F-057 | 2 | Specify and deliver sBOM plus Sigstore release signing. | Versioned verification evidence determines whether the applicable acceptance criteria passed. |
| F-116 | 2 | Specify and deliver dependency lockfiles and hashes, not just version pins. | Versioned verification evidence determines whether the applicable acceptance criteria passed. |
| F-117 | 2 | Specify and deliver model hash verification at load. | Versioned verification evidence determines whether the applicable acceptance criteria passed. |
| F-118 | 2 | Specify and deliver calibration ledger — every published number reproducible by a third party. | Versioned verification evidence determines whether the applicable acceptance criteria passed. |
| F-119 | 2 | Specify and deliver conformance test suite an outside implementer can run against their own build. | Versioned verification evidence determines whether the applicable acceptance criteria passed. |
| F-120 | 2 | Specify and deliver evidence packets — committed transcripts per exit gate. | Versioned verification evidence determines whether the applicable acceptance criteria passed. |
| F-121 | 1 | Specify and deliver receipt format binding an artifact hash to observed composition activity. | An author or verifier can inspect the defined composition evidence and its limits. |
| F-122 | 1 | Specify and deliver receipt issuance — always a free path, by policy. | An author or verifier can inspect the defined composition evidence and its limits. |
| F-123 | 1 | Specify and deliver receipt verification requiring no contact with us. | An author or verifier can inspect the defined composition evidence and its limits. |
| F-124 | 1 | Specify and deliver independent RFC 3161 timestamping — we never operate the authority. | An author or verifier can inspect the defined composition evidence and its limits. |
| F-125 | 1 | Specify and deliver per-device revocable keys plus a revocation transparency log. | An author or verifier can inspect the defined composition evidence and its limits. |
| F-126 | 1 | Specify and deliver freshness model for offline verification against revocation. | An author or verifier can inspect the defined composition evidence and its limits. |
| F-127 | 1 | Specify and deliver forgery-cost class as a first-class field on every receipt. | An author or verifier can inspect the defined composition evidence and its limits. |
| F-128 | 1 | Specify and deliver anti-coercion rule — a conformant implementation may not make receipt issuance non-optional for the author. | An author or verifier can inspect the defined composition evidence and its limits. |
| F-129 | 1 | Specify and deliver key custody and recovery for a non-technical author. | An author or verifier can inspect the defined composition evidence and its limits. |
| F-130 | 1 | Specify and deliver group authorship — four signers or four receipts. | An author or verifier can inspect the defined composition evidence and its limits. |
| F-131 | 1 | Specify and deliver receipt expiry and algorithm agility — ed25519 will not be safe forever. | An author or verifier can inspect the defined composition evidence and its limits. |
| F-132 | 3 | Specify and deliver aitrustid.com — landing and reference content, no-JS core. | A person can access the public tag workflow and its support process. |
| F-133 | 3 | Specify and deliver public status table distinguishing supported / experimental / reserved. | A person can access the public tag workflow and its support process. |
| F-134 | 3 | Specify and deliver limitations page, findable without being told where it is. | A person can access the public tag workflow and its support process. |
| F-135 | 3 | Specify and deliver report AI — public intake for AI content people want flagged. | A person can access the public tag workflow and its support process. |
| F-136 | 3 | Provide public live community discussions and official replies with safe publication controls. | Everyone can read public community messages and company replies; private reports and research remain outside the public stream. |
| F-137 | 3 | Apply a documented moderation and appeal process with public safe action records. | People see moderation reasons and appeal routes without removed secrets, private reports or reporter identities being republished. |
| F-073 | 3 | Specify and deliver security@ with a 72-hour response promise. | A person can access the public tag workflow and its support process. |
| F-074 | 3 | Specify and deliver conduct@ with an enforcement ladder. | A person can access the public tag workflow and its support process. |
| F-138 | 3 | Specify and deliver abuse@ and press@. | A person can access the public tag workflow and its support process. |
| F-139 | 3 | Specify and deliver site accessibility held to the same gate as the extension. | A person can access the public tag workflow and its support process. |
| F-140 | 3 | Specify and deliver sanitised public roadmap — no personal execution material. | A person can access the public tag workflow and its support process. |
| F-141 | 3 | Specify and deliver pilot programme — small consenting group, feedback without collecting prompts or outputs. | A person can access the public tag workflow and its support process. |
| F-142 | 3 | Specify and deliver install and removal instructions, reproducible. | A person can access the public tag workflow and its support process. |
| F-075 | 3 | Specify and deliver two-entity structure — independent foundation holds spec and mark; implementations compete on top. | Responsibilities and decisions are documented without implying an operating institution exists. |
| F-143 | 3 | Specify and deliver certification mark — filed, owned by the foundation. | Responsibilities and decisions are documented without implying an operating institution exists. |
| F-144 | 3 | Specify and deliver mark usage guidelines and a conformance statement template. | Responsibilities and decisions are documented without implying an operating institution exists. |
| F-145 | 3 | Specify and deliver certification programme — what a certifier must test, and how one is accredited. | Responsibilities and decisions are documented without implying an operating institution exists. |
| F-146 | 3 | Specify and deliver nonprofit formation and filings. | Responsibilities and decisions are documented without implying an operating institution exists. |
| F-147 | 3 | Specify and deliver conflict-of-interest recusal rule for maintainers with a commercial interest. | Responsibilities and decisions are documented without implying an operating institution exists. |
| F-148 | 3 | Specify and deliver qualified legal review of every biometric and privacy assurance. | Responsibilities and decisions are documented without implying an operating institution exists. |
| F-070 | 3 | Specify and deliver six invariants in CONTRIBUTING.md. | Responsibilities and decisions are documented without implying an operating institution exists. |
| F-071 | 3 | Specify and deliver threat model, 10 entries. | Responsibilities and decisions are documented without implying an operating institution exists. |
| F-072 | 3 | Specify and deliver aCCESSIBILITY.md as a release gate. | Responsibilities and decisions are documented without implying an operating institution exists. |
| F-149 | 3 | Specify and deliver mAINTAINERS.md with per-maintainer scope. | Responsibilities and decisions are documented without implying an operating institution exists. |
| F-150 | 3 | Specify and deliver cHANGELOG.md, state.json, docs/, runs/. | Responsibilities and decisions are documented without implying an operating institution exists. |
| F-151 | 3 | Specify and deliver dECISIONS.md — 15 seeded decisions with dates and reasons. | Responsibilities and decisions are documented without implying an operating institution exists. |
| F-152 | 3 | Specify and deliver branch protection, CODEOWNERS, required status checks, Dependabot. | Responsibilities and decisions are documented without implying an operating institution exists. |
| F-153 | 3 | Specify and deliver named ongoing ownership for security response and adapter maintenance. | Responsibilities and decisions are documented without implying an operating institution exists. |
| F-060 | 1 | Specify and deliver image. | Independent implementers have an explicit subject contract before support is claimed. |
| F-061 | 1 | Specify and deliver audio. | Independent implementers have an explicit subject contract before support is claimed. |
| F-062 | 1 | Specify and deliver video. | Independent implementers have an explicit subject contract before support is claimed. |
| F-063 | 1 | Specify and deliver document. | Independent implementers have an explicit subject contract before support is claimed. |
| F-154 | 1 | Specify and deliver text and code subject contracts. | Independent implementers have an explicit subject contract before support is claimed. |
| F-155 | 3 | Specify and deliver synthID and vendor watermarking. | The application extends supported tags without disabling the personal workflow. |
| F-156 | 3 | Specify and deliver additional browser and site adapters. | The application extends supported tags without disabling the personal workflow. |
| F-157 | 3 | Specify and deliver newsroom integration — labels in an editorial workflow. | The application extends supported tags without disabling the personal workflow. |
| F-158 | 3 | Specify and deliver agent identity — labelling output from autonomous agents. | The application extends supported tags without disabling the personal workflow. |
| F-159 | 3 | Specify and deliver fleet deployment and policy management. | The application extends supported tags without disabling the personal workflow. |
| F-160 | 3 | Specify and deliver host-level capture agents. | The application extends supported tags without disabling the personal workflow. |
| F-161 | 3 | Specify and deliver long-horizon retention and audit trails. | The application extends supported tags without disabling the personal workflow. |
| F-162 | 3 | Specify and deliver sSO and directory integration. | The application extends supported tags without disabling the personal workflow. |
| F-163 | 3 | Specify and deliver support with an SLA. | The application extends supported tags without disabling the personal workflow. |
| X-01 | 2 | Prevent introduction of: A paid API or any metered inference | The product excludes a paid api or any metered inference, and changes are reviewed against this boundary. |
| X-02 | 2 | Prevent introduction of: Any closed-source or paid dependency in the pipeline | The product excludes any closed-source or paid dependency in the pipeline, and changes are reviewed against this boundary. |
| X-03 | 2 | Prevent unapproved central collection; review consented in-house research storage under N-011. | No central collection is active; provider, consent and retention must be resolved before connection. |
| X-04 | 2 | Prevent introduction of: Per-person keystroke templates or any biometric identity profile | The product excludes per-person keystroke templates or any biometric identity profile, and changes are reviewed against this boundary. |
| X-05 | 2 | Prevent introduction of: Any human-negative verdict from an absent signal | The product excludes any human-negative verdict from an absent signal, and changes are reviewed against this boundary. |
| X-06 | 2 | Keep automatic telemetry disabled; treat approved research contribution as a separate consented workflow. | Using a tag does not automatically upload usage or content; collection remains unconnected. |
| X-07 | 2 | Prevent introduction of: Competing with C2PA on image provenance | The product excludes competing with c2pa on image provenance, and changes are reviewed against this boundary. |
| X-08 | 2 | Defer from the initial release: Building image, audio or video detection in 1.0 | The capability remains tracked for a later release and is not advertised as supported. |
| X-09 | 2 | Prevent introduction of: Colour-coded labels | The product excludes colour-coded labels, and changes are reviewed against this boundary. |
| X-10 | 2 | Prevent introduction of: aria-live="assertive" announcements | The product excludes aria-live="assertive" announcements, and changes are reviewed against this boundary. |
| X-11 | 2 | Prevent introduction of: Machine-assigned IV | The product excludes machine-assigned iv, and changes are reviewed against this boundary. |
| X-12 | 2 | Prevent introduction of: Mandatory receipts | The product excludes mandatory receipts, and changes are reviewed against this boundary. |
| X-13 | 2 | Defer from the initial release: Signing in 0.1 | The capability remains tracked for a later release and is not advertised as supported. |
| X-14 | 2 | Defer from the initial release: The registry container in 0.1 | The capability remains tracked for a later release and is not advertised as supported. |
| X-15 | 2 | Prevent introduction of: Collecting prompts or outputs from pilot users | The product excludes collecting prompts or outputs from pilot users, and changes are reviewed against this boundary. |
| X-16 | 2 | Prevent introduction of: "Outside knowledge proves human authorship" as an implementation requirement | The product excludes "outside knowledge proves human authorship" as an implementation requirement, and changes are reviewed against this boundary. |
| F-019 | 1 | Specify and deliver legacy grouping for F-019a, F-019b, F-019c. | The named capability has observable behavior and is tracked independently of implementation status. |
| F-020 | 1 | Specify and deliver legacy grouping for F-020a, F-020b. | The named capability has observable behavior and is tracked independently of implementation status. |
| F-021 | 1 | Specify and deliver legacy grouping for T-FA, T-PA. | The named capability has observable behavior and is tracked independently of implementation status. |
| F-022 | 1 | Specify and deliver legacy grouping for T-IV. | The named capability has observable behavior and is tracked independently of implementation status. |
| F-029 | 1 | Specify and deliver legacy grouping for F-029a, F-029b, F-029c. | The named capability has observable behavior and is tracked independently of implementation status. |
| N-001 | 2 | Specify and deliver protocol compatibility and schema migration. | The named capability has observable behavior and is tracked independently of implementation status. |
| N-002 | 2 | Specify and deliver separate pending, uncertain, unsupported, unavailable, and no-finding states. | The named capability has observable behavior and is tracked independently of implementation status. |
| N-003 | 2 | Specify and deliver detector resource limits, cancellation, concurrency, and failure containment. | The named capability has observable behavior and is tracked independently of implementation status. |
| N-004 | 2 | Specify and deliver consent, per-site pause, capture boundaries, reset and deletion. | The named capability has observable behavior and is tracked independently of implementation status. |
| N-005 | 2 | Specify and deliver label dispute, correction, and supersession workflow. | The named capability has observable behavior and is tracked independently of implementation status. |
| N-006 | 2 | Specify and deliver versioned regression checks and revalidation triggers. | The named capability has observable behavior and is tracked independently of implementation status. |
| N-007 | 3 | Specify and deliver no automated promotional AI content network. | The named capability has observable behavior and is tracked independently of implementation status. |
| N-008 | 3 | Specify and deliver no child-safety report hosting. | The named capability has observable behavior and is tracked independently of implementation status. |
| N-009 | 1 | Specify and deliver no rogue-AI verdict inferred from output. | The named capability has observable behavior and is tracked independently of implementation status. |
| N-010 | 3 | Specify and deliver personal/team/enterprise/proprietary tag offering boundaries. | The named capability has observable behavior and is tracked independently of implementation status. |
| T-UC | 1 | Identify supported hazardous command instructions with context | The person sees the command pattern and its bounded risk explanation. |
| T-SC | 1 | Evaluate validated co-occurring fraud indicators | The person sees possible fraud indicators, uncertainty, and relevant context. |
| T-BT | 1 | Research positive evidence of automation without inferring it from absent human evidence | The person sees only validated observations; templates or repetition alone are not a bot verdict. |
| N-011 | 3 | Organize approved tag outputs in a remotely hosted, controlled open-source data stack for independently reviewed training and pattern analysis. | Versioned records, independent labels and approved examples support reproducible improvement without making collection a dependency of local tags. |
| N-012 | 3 | Run a version-bound tag method on a phone without an account, extension or local containers. | A person copies an answer from any app and receives a bounded PS preview without uploading the answer. |
| N-013 | 3 | Receive selected text through an iPhone Share extension with explicit user action. | A person checks shared text without manual copy-and-paste while retaining control of disclosure. |
| N-014 | 3 | Receive selected text through an Android OS share interface with explicit user action. | A person checks shared text without manual copy-and-paste while retaining control of disclosure. |
| N-015 | 3 | Read a frozen reviewer JSON file, collect independent labels and export exact item fields for comparison. | Reviewers can label without developer setup or detector predictions; incomplete and changed files fail coordinator comparison. |
