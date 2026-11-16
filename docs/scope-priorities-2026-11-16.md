# Scope priorities and operating roles — November 16, 2026

Audited by Codex PM at 2026-11-16T19:09:40.101080+00:00. All **202 original IDs** remain: **132 complete / 70 open**. Six explicit delivery enhancements are added separately; they do not reduce that count.

## What was missing

The broad jobs were mostly preserved, but their delivery breakdown was incomplete. Native Light/Dark/Auto, payment-to-entitlement enforcement, distinct web/mobile community clients, quiet on-device presentation and image-first multimodal detection now have named linked jobs and acceptance. Planning earns only the written-contract milestone. No new taxonomic code, collection, checkout, credential, purchase or permission is activated.

F-006 reserves six modalities; it does not implement six detectors. F-136 already requires live public discussion; GitHub links and an empty imported snapshot do not complete an in-house web/mobile community. Accepted self-hosted Fleet/Host/Audit/SSO software is not an operating paid Business service. Current work must never retroactively remove the existing open-source license or gate personal checking/evidence.

## Pareto of open acceptance gates

Manual primary-gate classification of each original open requirement exactly once; not failure frequency, effort, revenue or predicted closures. Tags and supporting signals overlap, so counts do not imply equal business impact.

| Primary gate | Open records | Share | Cumulative | Accountable delivery lane |
|---|---:|---:|---:|---|
| Tag methods, evidence mapping and format support | 22 | 31.4% | 31.4% | CTO + independent tag agents |
| Device/vendor delivery and real-person acceptance | 13 | 18.6% | 50.0% | Delivery engineers + Debugger + actual device users |
| Independent ground truth and claim calibration | 12 | 17.1% | 67.1% | Tag agents + actual independent reviewers; Michael coordinates |
| Institutional, legal, license and service commitments | 9 | 12.9% | 80.0% | Michael/qualified counsel for decisions; CTO for technical evidence |
| Live community, reporting and moderation operations | 6 | 8.6% | 88.6% | Community engineer; Michael assigns real moderators |
| Adoption, compatibility and final acceptance decisions | 5 | 7.1% | 95.7% | PM prepares reviewable decisions; Michael adopts |
| Controlled production services and public trust operations | 3 | 4.3% | 100.0% | CTO + service engineer; Michael operating policy |

The largest four groups contain 56 of 70 open records (80%). This is a scope-count observation, not proof that four fixes remove 80% of defects. Each tag retains its own method and validation. Frequency does not outrank a security or release-blocking failure.

## Execution order and ownership

1. **Debugger + native delivery:** current appearance control, reproducible Share evidence, current package/Apple validation and a concrete TestFlight handoff. Keep failed runs and exact-five acceptance; do not alter the tested action just to get green.
2. **PM + tag engineers:** at most two active tag increments, each with an exact job, independent inputs/method/version, useful brief result, measured limits and its own acceptance packet. PS and PII improvements remain separate. Supporting components do not count as full released tags.
3. **CTO + image-method engineer:** publish and implement the first bounded image profile, keeping provenance, watermarks and statistical-generation signals distinct. Then audio/video/document and additional format profiles expand the same architecture.
4. **Community lane:** version the shared service contract and build web/native reading, posting, moderation, correction and replay behavior; name actual moderators before public posting. No silent training permission from participation.
5. **Business lane:** sell one defined operating service only after payment/tenant/entitlement/cancel/recovery controls and actual provider/pricing/terms are ready. Checking remains account-free; posting and paid organization membership have separate identities.

The PM owns priorities, original-ID preservation, task/acceptance allocation, evidence, changelog and release status. The CTO owns architecture, trust boundaries, resource budgets, migrations and cross-tag/platform isolation. The Debugging Lead owns reproduction, error signatures, cause assessment and regression review. Tag engineers own their independent methods. Michael remains product owner and actual legal/operator decision maker; agents are not legal officers or independent human reviewers.

Heavy local native UI and browser/build workloads are serialized; source research and work on separate remote hosts may proceed in parallel. No role is represented as permanently running outside active execution.

## Product-owner feedback

Strong direction: the code-only tag product, independence, broad formats, free personal use, transparency and usability have remained consistent. Useful corrections have caught real omissions. The execution gap was ours: broad promises were not consistently translated into separate service/client/payment acceptance, and visible activity/test counts replaced shipped outcomes too often.

The improvement on your side is to distinguish a new requirement from a change to the active release, and define the user outcome rather than prescribing simultaneous implementation. Keep the full ambition in the roadmap while limiting each release to a small set of complete jobs. You should not have to repeat scope to keep it alive; the PM owns that record and must flag gaps proactively.

## Item-by-item primary classification

### Tag methods, evidence mapping and format support

Choose one bounded method increment per active tag; preserve provenance, abstention and own validation; do not issue unsupported tags.

- **T-NF** (20%): NF Non-Fiction. Next: Deliver NF Non-Fiction. Next package action: Define claim units, reference freshness and corpus identity. Required outcome: The reader sees which claim is supported by which source and passage, and the limits of that support. Owner: Codex.
- **T-FI** (20%): FI Fiction / Fabricated. Next: Deliver FI Fiction / Fabricated. Next package action: Separate contradiction and unresolved-citation evidence types. Required outcome: The reader can inspect the contradiction or resolution failure without being told an entire author or work is fabricated. Owner: Codex.
- **T-HP** (20%): HP Hallucination Possible. Next: Deliver HP Hallucination Possible. Next package action: Evaluate specificity, contradiction, repetition and hedging independently. Required outcome: The reader knows which inconsistency or unsupported detail warrants checking and why. Owner: Codex.
- **T-MT** (20%): MT Manipulative Tactic. Next: Deliver MT Manipulative Tactic. Next package action: Write an annotation guide separating persuasion, urgent safety advice and coercive framing. Required outcome: The reader sees the framing and relevant context, with a measured disagreement/uncertainty boundary. Owner: Codex.
- **T-IV** (20%): IV Independently Verified. Next: Deliver IV Independently Verified. Next package action: Specify reviewer consent, review scope and attestation identity. Required outcome: The reader knows who reviewed what, against which evidence and when, including withdrawal or correction. Owner: Codex.
- **T-FA** (20%): FA Full AI Augmentation. Next: Deliver FA Full AI Augmentation. Next package action: Define acceptable generation events and manifest claims with signer trust. Required outcome: The reader sees the origin assertion, source of evidence and supported observation window. Owner: Codex.
- **T-PA** (20%): PA Partially Augmented. Next: Deliver PA Partially Augmented. Next package action: Separate explicit generation/edit evidence from behavioral research hypotheses. Required outcome: The reader can distinguish documented contribution/edit events from unobserved authorship. Owner: Codex.
- **T-OUT** (20%): PII_OUTBOUND. Next: Deliver PII_OUTBOUND. Next package action: Define supported compose/send surfaces and capture permissions. Required outcome: The user controls disclosure before sending, without an invisible copy of their prompt. Owner: Codex.
- **T-SC** (20%): Scam Pattern. Next: Deliver Scam Pattern. Next package action: Define pressure, value transfer, identity assertion and channel-switch labeling with benign controls. Required outcome: The reader can inspect each validated indicator and dismiss a warning without an accusation of intent. Owner: Codex.
- **T-BT** (20%): Automation Pattern. Next: Deliver Automation Pattern. Next package action: Define positive, verifiable automation evidence and its capture boundaries. Required outcome: A finding reports supported automation evidence within a defined workflow, without labeling an ordinary person a bot. Owner: Codex.
- **F-012** (80%): sig.credential_exfil.v1 — reads a secret path, writes to a network sink. Next: Complete the proposed Semgrep/use-mention integration contract and independent credential-flow validation before any PS mapping. The separate bounded Python static-flow observation now runs on Mac and isolated Linux; unknown syntax is explicitly unavailable. Owner: Codex.
- **F-013** (80%): sig.typosquat.v1 — package name within edit distance 1–2 of a top-N name. Next: Obtain an independently supported ranked package snapshot, validate the recommendation/use-mention and benign-similarity boundaries, and complete held-out enhancement acceptance before any PS mapping. The offline ranking/import/edit-distance component is functioning. Owner: Codex.
- **F-015** (80%): sig.unsourced_specificity.v1 — figures or dates with no provenance marker. Next: Validate contextual specificity, citation scope and useful indicator errors before HP integration. The separate literal numeric/date-shaped component now executes on Mac and isolated non-root Linux; it does not establish truth or source support. Owner: Codex with independent reviewers.
- **F-016** (60%): sig.selfcontradiction.v1 — NLI entailment between sentence pairs. Next: Validate representative self-contradiction selection, category errors and model calibration; agree signal/tag mapping and finish the full HP integration and human acceptance. The working caller-selected research model has a retained neutral-pair error and issues no tag. Owner: Codex.
- **F-018** (80%): sig.hedge_collapse.v1 — hedging absent where uncertainty is expected. Next: Validate contextual hedge/word-sense interpretation and complete the full HP integration acceptance. The English reference observation works for explicitly caller-selected, hash-bound expected-uncertainty spans; expectation is not inferred. Owner: Codex.
- **F-019a** (80%): sig.urgency_frame.v1 — time-pressure lexicon plus imperative density. Next: Complete contextual/grammatical imperative and use-mention validation before MT integration. The separate English literal time-pressure and directive-density measurement works; emergency advice is never asserted as manipulation. Owner: Codex.
- **F-019b** (60%): sig.false_dilemma.v1 — binary framing where alternatives exist. Next: Complete additional exclusive/negated grammar, automatic selection, contextual/quotation interpretation, feasible and fresh additional references, independent category errors and accepted MT/human integration. Four caller-selected paired-marker forms now work; the new between/and form never nominates a signal. This increment is published through protected PR101; remaining validation and integration work stays open. Owner: Codex.
- **F-019c** (80%): sig.authority_appeal.v1 — unattributed appeals to expertise or consensus. Next: Complete contextual attribution and use-mention validation before MT integration. The English phrase/local-marker component works but does not resolve citations, attribution elsewhere or intent. Owner: Codex.
- **F-020b** (60%): sig.corpus_contradiction.v1 — NLI contradiction against a retrieved passage. Next: Validate representative reference selection, contextual and temporal errors, source freshness and model calibration; accept the proposed signal/tag mapping and complete full FI integration and human acceptance. The working offline research command preserves a default lexical miss and is not an FI or falsehood verdict. Owner: Codex.
- **F-029a** (20%): sig.outside_knowledge.v1 — a revision introduces something not derivable from the captured session. Next: Deliver sig.outside_knowledge.v1 — a revision introduces something not derivable from the captured session. Next package action: Separate explicit generation/edit evidence from behavioral research hypotheses. Required outcome: Observed interaction is documented without unsupported authorship or identity claims. Owner: Codex.
- **F-024** (80%): PII_OUTBOUND pre-send warning — you are about to paste personal data into a model. Next: Complete accepted browser compose/send capture, explicit edit/cancel/proceed and supported send-path enforcement, then independent recognition and human acceptance. The manual draft privacy route works but does not intercept sending or issue PII_OUTBOUND. Owner: Codex.
- **F-155** (20%): SynthID and vendor watermarking. Next: Deliver SynthID and vendor watermarking. Next package action: Treat vendor origin/watermark evidence as inputs, not blanket truth. Required outcome: The application extends supported tags without disabling the personal workflow. Owner: Codex.

### Device/vendor delivery and real-person acceptance

Finish current iOS software/packaging, then owner TestFlight use; keep vendor, Android and human accessibility jobs distinct.

- **F-030** (40%): MV3 MAIN-world capture — fetch patch plus ReadableStream.tee(). Next: Prove MAIN-world stream capture on a live supported vendor or explicitly replace that route with the demonstrated DOM adapter; do not count DOM success as fetch-patch validation. Owner: Codex.
- **F-037** (60%): Per-vendor site adapters. Next: Exercise the declared supported ChatGPT adapter and deliberate recheck lifecycle against current vendor markup; publish unsupported-page behavior and complete outside-user checks. Owner: Codex.
- **F-035** (60%): Full screen-reader semantics, aria-live="polite" never assertive. Next: Rerun the current selected route on live regenerated/edited/multiple responses and vendor navigation; complete required human keyboard/screen-reader/comprehension checks without substituting synthetic fixtures. Owner: Codex.
- **F-097** (60%): User-invoked labelling — select a response, ask for a check. Next: Exercise the declared supported ChatGPT adapter and deliberate recheck lifecycle against current vendor markup; publish unsupported-page behavior and complete outside-user checks. Owner: Codex.
- **F-113** (80%): Measured latency budget on declared hardware. Next: Measure physical-phone and other declared whole-route startup/update behavior; accept route-specific budgets and prove their enforcement. The complete local staging pipeline is now measured at four input sizes; the historical 100 ms target remains unaccepted. Owner: Codex; human device testers.
- **F-142** (80%): Install and removal instructions, reproducible. Next: Perform the existing physical-device, screen-reader and outside-user setup tasks, and obtain an actual outside implementer run against their own build with recorded acceptance. F-119 software checks do not satisfy these human tasks. Owner: Human device/accessibility testers; Codex fixes.
- **F-156** (80%): Additional browser and site adapters. Next: Complete current live vendor use and the stable outside-user Firefox installation/removal acceptance. Only Linux Firefox 153.4.0 temporary installation and the declared synthetic DOM profile with actual source-verified services are demonstrated; other browsers/sites are not claimed. Owner: Codex and outside users.
- **N-012** (80%): Phone and offline on-device tag checker. Next: Execute the owner guide on the identified physical iPhone 14 Plus with actual iOS version and VoiceOver; then Android/TalkBack, outside-user setup and human desktop screen-reader checks. Browser engines do not substitute. Owner: Michael first iPhone test; other human testers; Codex fixes.
- **N-013** (60%): Native iPhone sharing into a tag check. Next: Run the source-current producer with strict one-attempt cleanup before result inspection and immediate post-UI/final source snapshots. The prior hosted run passes all five original UI cases but fails its30-second result collection; recovered summary cannot replace missing complete proof. Current unsigned archive passes34 resource comparisons. Keep signing/platform/contact, reviewed TestFlight upload and physical/VoiceOver/outside-user acceptance open. Owner: Michael / physical-device testers / Codex.
- **N-014** (20%): Native Android sharing into a tag check. Next: Deliver Native Android sharing into a tag check. Next package action: Complete real iPhone/Android and screen-reader/offline update/removal checks. Required outcome: A person checks shared text without manual copy-and-paste while retaining control of disclosure. Owner: Codex.
- **F-141** (60%): Pilot programme — small consenting group, feedback without collecting prompts or outputs. Next: Recruit and record a small consenting pilot, run the real workflow, review user feedback and close defects. Metadata preview/download is tested; it is not a running recruited pilot. Owner: Michael recruits and accepts; Codex tooling.
- **F-129** (80%): Key custody and recovery for a non-technical author. Next: Complete actual nontechnical-author backup, lost-key restoration, separately saved public-key checking and compromise/replacement understanding on an owner-controlled second computer. Offline Mac/Linux engineering and hidden terminal controls are exercised; human custody acceptance is not. Owner: Michael and outside author; Codex fixes.
- **F-130** (80%): Group authorship — four signers or four receipts. Next: Complete outside-user multi-device group operation and the full authorship-receipt interpretation/acceptance. Current cryptographic agreement proves selected keys signed the same artifact-bound record; it does not prove authorship or distinct people, issue PA/FA/IV, implement revocation or adopt RFC-0002. Owner: Michael and group participants; Codex interpretation and fixes.

### Independent ground truth and claim calibration

Finish sampling/labeling policy and one frozen independent test per tag; software may prepare packets, not replace human independence.

- **T-PS** (80%): PS Potential Scam / Risk. Next: Complete the agreed independent current-method sampling/labeling/holdout protocol, report category errors and confidence lower bounds, then obtain required human route acceptance. Development success is not independent accuracy. Owner: Michael coordinates independent reviewers; Codex tooling.
- **T-PII** (80%): PII_REDACTED. Next: Improve remaining false masking and obfuscated addresses; complete independent representative recognition and required human route acceptance. Corrected source and measured development panels are published, and local service installations must rebuild to adopt the change. Owner: Codex.
- **F-005** (60%): Per-tag confidence floors. Next: Agree and independently validate evidence-supported per-tag calibration/confidence policy, then complete integration and final acceptance. Current 0.70 PS rule-score enforcement works but is not a measured probability or the 0.93 precision gate. Owner: Codex.
- **F-010** (80%): sig.piped_installer.v1 — curl/wget piped to a shell. Next: Complete the agreed independent current-method sampling/labeling/holdout protocol, report category errors and confidence lower bounds, then obtain required human route acceptance. Development success is not independent accuracy. Owner: Michael coordinates independent reviewers; Codex tooling.
- **F-011** (80%): sig.obfuscated_payload.v1 — base64/hex into eval/exec. Next: Complete the agreed independent current-method sampling/labeling/holdout protocol, report category errors and confidence lower bounds, then obtain required human route acceptance. Development success is not independent accuracy. Owner: Michael coordinates independent reviewers; Codex tooling.
- **F-014** (80%): Use/mention discriminator — is the command being recommended or discussed?. Next: Complete the agreed independent current-method sampling/labeling/holdout protocol, report category errors and confidence lower bounds, then obtain required human route acceptance. Development success is not independent accuracy. Owner: Michael coordinates independent reviewers; Codex tooling.
- **F-023** (80%): Detected PII redaction. Next: Improve remaining false masking and obfuscated addresses; complete independent representative recognition and required human route acceptance. Corrected source and measured development panels are published, and local service installations must rebuild to adopt the change. Owner: Codex.
- **F-050** (60%): Gate thresholds in eval/gates.yaml — precision, recall, ECE, abstention band, latency, axe, α. Next: Accept the claim-specific sampling, calibration/abstention and category reporting protocol; collect independent evidence and publish reproducible counts rather than reuse development labels. Owner: Codex.
- **F-108** (60%): Frozen held-out split with a manifest hash, separate from the regression suite. Next: Recruit two independent humans and an independent sample coordinator; freeze a new representative holdout, return blind labels and adjudicate disagreement before detector evaluation. Phone packet tooling is complete but actual review is not. Owner: Michael and independent reviewers.
- **F-056** (60%): Krippendorff's α published for MT, ≥ 0.55. Next: Accept the MT annotation and sampling protocol; collect real blinded independent human ratings, adjudicate disagreement, adopt the threshold and interval method, and publish the measured agreement. The nominal computation now executes on Mac and isolated Linux; synthetic examples are not an MT validation study. Owner: Codex.
- **F-114** (60%): Method-appropriate abstention measurement and policy. Next: Accept the claim-specific sampling, calibration/abstention and category reporting protocol; collect independent evidence and publish reproducible counts rather than reuse development labels. Owner: Codex.
- **N-015** (80%): Blind PS review from a phone. Next: Complete the identified physical iPhone 14 Plus owner-run review task and the independently coordinated representative holdout with two real blind reviewers and human adjudication. Current actual frozen-file browser downloads and private CLI comparisons are demonstrated using invented ratings only. Owner: Michael and independent reviewers.

### Institutional, legal, license and service commitments

Complete software evidence and drafts autonomously; actual filings, qualified review, accreditation and staffed commitments remain real external gates.

- **F-076** (40%): RFC process — template, 14-day comment, evidence requirement. Next: Execute the RFC/maintainer/recusal process with accepted roles and recorded decisions; a policy file is not an operating foundation or populated independent board. Owner: Michael and reviewers.
- **F-057** (20%): SBOM plus Sigstore release signing. Next: Complete remaining transitive/native/platform obligations, source offers and model permission review; bind the full conflict policy before claiming redistribution clearance. Selected asset identity and exact notice packaging now execute. Owner: Codex.
- **F-075** (20%): Two-entity structure — independent foundation holds spec and mark; implementations compete on top. Next: Deliver Two-entity structure — independent foundation holds spec and mark; implementations compete on top. Next package action: Separate current individual publisher from any future legal entity. Required outcome: Responsibilities and decisions are documented without implying an operating institution exists. Owner: Codex.
- **F-143** (20%): Certification-mark ownership and filing work. Next: Deliver Certification-mark ownership and filing work. Next package action: Separate current individual publisher from any future legal entity. Required outcome: The public can distinguish a future institutional target from a mark or foundation that already exists. Owner: Codex.
- **F-145** (20%): Certification programme — what a certifier must test, and how one is accredited. Next: Deliver Certification programme — what a certifier must test, and how one is accredited. Next package action: Separate current individual publisher from any future legal entity. Required outcome: Responsibilities and decisions are documented without implying an operating institution exists. Owner: Codex.
- **F-146** (20%): Nonprofit formation and filings. Next: Reconcile full safe public formation drafts, approve entity/tax choices with a realistic budget and qualified counsel, and perform actual filings. Inventory and proposed corrections are not formation. Owner: Michael and qualified nonprofit/tax counsel.
- **F-148** (20%): Qualified legal review of every biometric and privacy assurance. Next: Qualified counsel must review actual privacy/biometric assurances and applicability. Codex targeted draft repairs and authoritative-source research do not constitute this qualified review. Owner: Michael engages qualified counsel.
- **X-02** (20%): Any closed-source or paid dependency in the pipeline. Next: Complete remaining transitive/native/platform obligations, source offers and model permission review; bind the full conflict policy before claiming redistribution clearance. Selected asset identity and exact notice packaging now execute. Owner: Codex.
- **F-163** (20%): Support with an SLA. Next: Deliver Support with an SLA. Next package action: Define supported versions/hours, escalation, exclusions and service outcomes. Required outcome: The application extends supported tags without disabling the personal workflow. Owner: Codex.

### Live community, reporting and moderation operations

Build a shared self-hosted service with web/mobile clients, authorized posting/retraction and bounded live updates; name operating owners before opening posting.

- **F-135** (40%): Report AI — public intake for AI content people want flagged. Next: Implement public report intake and official response/correction/appeal states with authorization, safe rendering and no private-example publication by default; verify a report through resolution. Link live discussion delivery to F-136 rather than treating a GitHub link as complete. Owner: Community engineer; Michael assigns response owners.
- **F-136** (40%): Townhall — a community space for AI users to talk, with moderation. Next: Build the self-hosted live community service and explicit web/iOS clients: public reading, authenticated posting/replies, bounded updates/reconnect/replay, moderation/retraction and privacy-marker tests. Name real moderators before opening public posting. Owner: Community engineer; Michael assigns moderators.
- **F-137** (40%): Moderation ladder and escalation path derived from the code of conduct. Next: Implement role-bound moderation, escalation, appeals, safe tombstones, and removal from public cache/replay/export; exercise two users plus an authorized moderator and retain accountability without republishing removed private material. Owner: Community/security engineers; named human moderators.
- **F-074** (40%): conduct@ with an enforcement ladder. Next: Verify conduct inbox delivery and access ownership, publish accountable response/escalation handling, and exercise a synthetic conduct report through the actual enforcement ladder. Do not infer staffed operations from an alias existing. Owner: Michael names conduct operators; Codex verifies tooling.
- **F-138** (40%): abuse@ and press@. Next: Verify abuse and press inbox delivery, responsible operators, private abuse triage versus authorized public press replies, and correction/escalation handling. Building the discussion UI alone does not operate these inboxes. Owner: Michael names operators; Codex verifies routing.
- **N-005** (40%): Label dispute, correction, and supersession workflow. Next: Implement a versioned dispute-to-review-to-correction/supersession workflow bound to the original tag/method/evidence; preserve correction history and safe public visibility, allow appeal, and verify authorized reviewers plus ordinary-user understanding. Owner: Community/tag engineers; Michael names review owners.

### Adoption, compatibility and final acceptance decisions

Preserve current schema and record meanings; prepare exact migration/acceptance proposals, never treat an unanswered proposal as adopted.

- **F-004** (80%): Abstention as a first-class state — UNK. Next: Complete owner adoption/compatibility decision for the proposed UNK replacement and required human understanding/accessibility checks. Current abstentions and six UI states work without emitting a new UNK verdict. Owner: Codex.
- **T-UNK** (20%): UNK Unknown. Next: Deliver UNK Unknown. Next package action: Reconcile existing protocol codes and six-state UI/proposal meanings without silent taxonomy changes. Required outcome: A reader can tell what was evaluated and why a tag could not provide its claim. Owner: Codex.
- **T-UC** (20%): Unsafe Command. Next: Deliver Unsafe Command. Next package action: Prepare an RFC decision and compatibility mapping. Required outcome: A proposed migration explains exactly which meaning changes and how old PS records remain interpretable. Owner: Codex.
- **N-001** (80%): Protocol compatibility and schema migration. Next: Accept any successor-version migration before implementing it; exercise the accepted transformation and evidence-loss/round-trip contract. Current version checks and unknown-version refusal work; no successor migration or proposal adoption is claimed. Owner: Codex.
- **F-120** (60%): Evidence packets — committed transcripts per exit gate. Next: F-120 software/human acceptance allocation remains unaccepted; the recorded November6 decision applies to F-119 only. Retain the original versioned-vector/exit-packet/outside-user criterion. Existing packet tooling works, and failed native collection is preserved; do not close F-120 by silently reallocating its acceptance. Owner: Michael — F-120 acceptance allocation; Codex — tooling; outside implementer — retained human acceptance.

### Controlled production services and public trust operations

Complete tenant/consent/revocation/retention/recovery controls before payment, research intake or public transparency service activation.

- **N-010** (60%): Personal/team/enterprise/proprietary tag offering boundaries. Next: Accept namespace ownership and actual custom scope/licensing; integrate and independently validate each organization job, permission, export and human operation before commercial rollout. The optional caller-bound literal prototype is functioning; it does not issue public tags or establish employee consent. Owner: Codex.
- **N-011** (60%): In-house research data, training and anomaly pipeline. Next: Deploy the approved invited metadata pilot only after production authentication and least-privilege grants, TLS/proxy/provider handling, active and encrypted backup expiry, withdrawal, replacement-host recovery, current privacy notice and owner operation pass. Then run a genuinely consenting pilot. The separate HTTP/worker/database development path is exercised; collection stays disabled. Owner: Michael data policy; Codex application.
- **F-125** (80%): Per-device revocable keys plus a revocation transparency log. Next: Deliver actual publicly distributed/witnessed revocation transparency, equivocation/completeness checks, rotation and outside-user per-device acceptance. Current signed cached history is not a public transparency service. Owner: Codex and Michael.

## Explicit enhancement contracts

Native appearance has since reached the implemented mechanism and executable-check milestones (60%); actual control rendering and final acceptance remain pending. The other five new contracts retain written-scope credit only. See the current ledger for timestamps and evidence.

### ENH-NATIVE-APPEARANCE — Native Light / Dark / Auto switch

Linked originals: N-013, N-012, F-139. Owner: Native UX engineer; Debugger regression review.

Accessible in-app switch and device-theme reset; preference only stored locally; no input/result/capture changes; verify persistence, separate host/Share containers and privacy manifest.

### ENH-BUSINESS-ENTITLEMENTS — Verified payment to Business entitlement

Linked originals: N-010, F-162, F-163. Owner: Business service engineer; CTO security; Michael commercial/provider decisions.

Define one real operating Business service, approved prices/provider/terms, authenticated tenant ownership, verified payment events, idempotent entitlement grants, server enforcement, cancellation/refund/revocation/recovery and outage isolation. Personal checks and existing open-source rights remain unaffected.

### ENH-COMMUNITY-CLIENTS — Shared live community on web and native app

Linked originals: F-135, F-136, F-137, N-005. Owner: Community engineer + native client engineer; Michael operating moderators.

One moderated service and versioned action contract used by web and iOS clients, with public read, separate posting identity, authorized official replies, safe retract/appeal/reconnect/replay, accessibility and data retention/deletion acceptance.

### ENH-QUIET-LAYER — Nonblocking tags beside device/app content

Linked originals: F-033, F-037, F-160, N-013, N-014. Owner: CTO architecture; platform integration agents; Debugger.

Per-platform authorized adapters bind observations and tags to exact content revisions; multiple compact tags must not intercept underlying actions, move focus, steal input or hide content. Verify per-tag fault containment, stale-result removal and supported OS/permission boundaries. No universal screen access is presumed.

### ENH-MULTIMODAL-COVERAGE — Image-first expansion across every supported AI format

Linked originals: F-006, F-154, F-155, T-FA, T-PA, T-HP. Owner: CTO + modality/tag engineers; independent evaluation per job.

Specify independent image provenance/signature/revocation, watermark and statistical AI-generation jobs; enumerate supported bytes/formats and attack/error cases, validate each before release. Extend the same contract to audio, video, documents, code/text and future formats; unknown profiles return Unsupported, never false clearance. No new live tag code is adopted by planning.

### ENH-DELIVERY-ROLES — PM, CTO, Debugging Lead and independent tag ownership

Linked originals: F-150, F-153, N-003, N-006. Owner: Michael product owner; Codex PM; assigned CTO/Debugger/tag agents.

Maintain distinct PM prioritization/scope/evidence, CTO architecture/security/resource boundaries, Debugger reproducible root causes, and tag-specific implementation/evaluation ownership. Bound WIP and serialize heavy local validation; audit handoffs, closure criteria, rollback and factual completion. Agent roles do not imply legal officers, human independence or continuous operation outside active work.

