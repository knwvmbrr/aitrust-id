# Visual, video and spatial tags — execution baseline

Direction recorded November 22, 2026. This is implementation planning under
ENH-MULTIMODAL-COVERAGE, ENH-QUIET-LAYER and the existing FA/PA/MT/NF/IV,
F155 and format scope. It does not register new live codes, extend the six-value
modality enum, change existing numeric gates or count a planned capability as
complete. All 202 original requirements and the136/66 count remain preserved.

The product remains independent, explainable tags. A picture or clip can carry
several tags with different jobs. One tag failing must leave unrelated supported
tags and the host interaction usable. The first visual release must complete one
precise useful claim end to end while the broader scope stays in the backlog.

## What each result must mean

| Question | Supported evidence/outcome | What it cannot establish alone |
| --- | --- | --- |
| What is in this file? | Bounded container facts and metadata-section observations | AI origin, authorship, truth or a clean/safe file |
| What does a trusted origin declaration say? | Exact content binding, signature, signer policy, revocation state and declared generation/edit events | Whether the depicted event is true |
| Is a supported watermark present? | Provider-specific authenticated subject/payload evidence and its limitations | That an unmarked image is human-made |
| Does this look manipulated or synthetic? | A named, validated classifier's bounded inference; regions/times and error rates | Universal authenticity or malicious intent |
| Is it misleading in context? | Claim/source/time/location comparison with cited evidence | A verdict from visual style or a VLM's confidence alone |
| Does it use a persuasion technique? | A specific contextual technique with text/region/time evidence and uncertainty | Falsity, ideology, intent or an accusation about a person |

C2PA distinguishes provenance validation from factual or moral judgments;
consume its standard rather than inventing a replacement or treating a signature
as truth. [C2PA 2.5](https://spec.c2pa.org/specifications/specifications/2.5/specs/C2PA_Specification.html).
NIST separately evaluates manipulation, deepfake and localization tasks; these
are useful evaluation patterns, not an accuracy certificate for this product.
[OpenMFC](https://mfc.nist.gov/).

## Ordered work, with parallel lanes

These are work-item IDs, not adopted tag codes or extra original completions.
Each finished item requires a different reviewer, exact source and evidence,
actual supported/refusal/fault/recovery cases and an attributed changelog entry.
No new paid service, model download or production capture is authorized by a
planning row; use existing resources and rights/resource gates.

| Priority / item | Engineering outcome and completion evidence | Owner/external handoff |
| --- | --- | --- |
| P0 V01 — deliver current image helper | Finish NF release-blocker diagnosis, current protocol/site checks, protected merge and actual public image/provenance-download checks. Keep FA Planned; do not market metadata as AI detection. | Existing physical-user acceptance remains separate. |
| P0 V02 — independent visual contracts | Write per-tag input/claim/output/failure contracts, supported formats, version binding and risk-specific gate proposal. Map every result to an existing adopted code only when that mapping is valid. | Formal standard/code/modality adoption where required. |
| P1 V03 — authenticated origin | Wire the existing manifest inspection/adjudication into a supported FA/PA evidence path: exact subject binding, configured trust, signature, timestamps and revocation. Test absent, altered, revoked, expired, wrong subject and unknown trust. Unknown revocation cannot become Valid. | Independent full-tag acceptance; no operating certification claimed. |
| P1 V04 — watermark resolver | Finish F155's real trusted subject/provider resolver and existing-tag consumer. Resolve decoded payloads and manifests where required; treat a bare research statistic as unbound. Show conflicting independent evidence rather than silently choosing one. | Supported authentic provider-positive evidence and tag-specific validation, not an invented account/key requirement. |
| P1 V05 — independent data | Inventory lawful image/video benchmarks and source rights; freeze source-family/generator-disjoint training/development/holdout sets. Include camera images, edited real images, generated media, screenshots, recompression, crops and benign counterexamples. Record leaks/near-duplicates and exclusions. | Independent sample coordination and labels; do not substitute author/AI labels for retained human gates. |
| P1 V06 — image inference baseline | Select a separately licensed code/weights pair that fits measured RAM/CPU/storage. Compare simple baselines with the VLM-assisted method on the same declared task. Return region evidence and uncertainty; do not issue FA from style, unusual pixels or missing credentials. Run model failure/OOD/resource-exhaustion controls. Treat OCR, image and model text as untrusted data: media instructions never grant tool, file, network or device actions; render explanations as escaped text and test instruction-bearing images. | Claim-specific independent release gate. Model choice is engineering; unresolved rights remain blocked. |
| P1 V07 — video baseline | Add bounded selected-clip decoding and reproducible frame/time identities. Detect supported editing/generation patterns over time, report localized intervals and uncertainty, and refuse unsupported codecs. Test frame insertion/deletion, transcoding, speed changes, missing frames and limited audio/video alignment. A clip is the sampling unit; thousands of correlated frames are not independent examples. | Actual rights, contextual labels and real-device validation. |
| P1 V08 — persuasion/propaganda research | Extend MT's contextual, multilabel technique research across OCR text and visible evidence. Separate quotations, satire, reporting, debunking, ordinary ads and legitimate urgency. Show each supported cue and alternative explanation; never label a person or infer intent from a technique. | Annotation policy, contextual independent raters and appeals. No single all-purpose Propaganda verdict is adopted here. |
| P1 V09 — nonblocking adapters | Version browser/native/agent adapters independently. Place compact multiple tags beside the subject; keep brief explanations in use and complete details in site modals. Do not replace text, intercept primary actions, move focus unexpectedly or obscure content. Test scrolling, editing, navigation, keyboard/touch/zoom, stale results, teardown and one failed/saturated worker while siblings continue. | OS permissions and physical screen-reader/device operation. |
| P2 V10 — spatial/3D proof | Propose a 3D modality/subject RFC before changing live schemas. Start with one bounded single-file scene/model format; bind source asset, resources and rendering/view/time identity. Refuse scripts, unapproved external resources, traversal and expansion bombs. Treat rendered pixels and underlying geometry as distinct subjects. | Standard adoption and appropriate spatial ground truth. No current3D detector is claimed. |
| P1 V11 — privacy and optional improvement | Default local/selected-content checking. No silent image/video uploads, gallery harvesting, telemetry or training consent. Keep metadata-only feedback separate from explicit previewed/redacted example sharing. Visual redaction may change forensic signals: bind original and transformed subjects separately. Run withdrawal, retention, encrypted-backup expiry and recovery before real collection. | Existing approved pilot terms remain; any raw-media/training purpose requires separate informed permission. |
| P1 V12 — per-tag release and reach | Publish readable per-tag instructions, downloadable method/evidence and small performance charts: actual sample counts, confusion matrix, precision/recall/FPR, intervals, coverage, OOD/unavailable rate and per-route hardware/timing. Make standalone API/MCP and browser/native use practical. Draft honest use-case announcements only after actual release. | Independent acceptance and exact social-post approval/connected accounts. |

SemEval's multimodal meme task supplies a useful reference taxonomy and evaluation
example for specific persuasion techniques; it is not a product truth or intent
oracle. Its hierarchy includes 22 techniques. Rights, representation and label
transfer still require review before using its data.
[Primary task paper](https://aclanthology.org/2024.semeval-1.275/).

The first concrete model/data screening and its blocked rights are recorded in
[visual model and data screening](visual-model-data-screening.md). No model or
corpus is selected merely because it is mentioned in a paper or model card.

## Release standard, applied separately to each tag

1. **Lock the job first.** Publish the exact question, positive evidence, rejected
   interpretations, supported modality and risk of a false accusation. Define
   numeric gates and sampling units before inspecting the holdout; do not copy
   PS's thresholds onto unrelated visual tasks or invent measured probabilities.
2. **Freeze the mechanism.** Pin code, model weights, preprocessing, sources,
   rights and configuration. Bind every region/time/result to the exact input
   version. An unexplained VLM answer is not an evidence packet.
3. **Measure the actual claim.** Publish per-category errors and uncertainty;
   test unseen generators/domains/languages and benign editing. Keep calibration,
   repeatability and independent accuracy as distinct evidence. Sparse data means
   an unqualified claim stays unavailable; no invented perfect score.
4. **Prove independence.** Run the tag alone; disable, timeout, corrupt and
   saturate it; recover without changing another tag's assertion. Shared parsing
   and protocol helpers are foundations, not permission for a verdict dependency.
5. **Complete use and correction.** A person can invoke, understand, dismiss,
   reproduce an eligible record and challenge a result. A mobile/keyboard/screen-
   reader task must actually work. Retain honest Unavailable for incomplete
   historical records, rather than fabricate original inputs.
6. **Ship protected source and real delivery.** Verify the actual artifact,
   provenance/SBOM and managed release where applicable. Match published bytes,
   exercise the live path and update scope/changelog. No model or original tag
   reaches100% from a draft, benchmark citation or test count.

## Presentation layer means isolation, not immunity

We can build independent tag presentation and supported acquisition adapters.
No layer is unaffected by every OS, permission, host change or protected surface.
Android documents both overlay permission and the ability of applications to hide
overlay windows; Apple documents constrained extension/host communication.
Start with the existing browser anchors, photo/file picker and Share flows.
Add an OS-approved overlay/capture adapter only after its permissions and secure-
content refusal are demonstrated. Permission denied or lost context means
Unavailable, not a weaker safety clearance. No secret screen capture or attempts
to bypass protected content.
[Android permission reference](https://developer.android.com/reference/android/Manifest.permission#SYSTEM_ALERT_WINDOW) ·
[Apple extension architecture](https://developer.apple.com/library/archive/documentation/General/Conceptual/ExtensibilityPG/ExtensionOverview.html).

## AI already works in 3D

AI is not confined to flat images. NeRF represents a scene through a neural
function of 3D position and viewing direction and renders new views. That makes
spatial provenance and scene/model tagging a legitimate expansion. It does not
make photorealism proof of reality, or certify the authenticity of every mesh,
scan, avatar or rendered scene. A model's viewpoint inputs are not evidence of
extra physical dimensions. [Original NeRF paper](https://arxiv.org/abs/2003.08934).

## Delivery management that enables this

Use one durable task register, a PM accountable for integration, and bounded tag
workers with separate reviewers. Separate human gates from available engineering.
Track completed original outcomes, available engineering handoffs, deployment
state and failures; do not reward a larger test count. Keep WIP within real worker
capacity. Use disposable Linux/macOS CI for qualification rather than depending
on an unlocked personal Mac or bypassing its disk reserve. Reduce unrelated
release coupling only through an explicit, reviewed architecture change; never
turn off the current failed check to speed a release.

The latest owner/engineering split is [execution-ownership.json](execution-ownership.json).
The owner checklist is [owner-actions.md](owner-actions.md).

## Owner clarification — personal history and temporal scenes

Direction recorded 2026-11-24T04:35:56.090177+00:00. The accepted business model supports the larger
open identification-standard mission. Track optional personal history as its own
independent enhancement: what was actually displayed, where, when and why, with
minimal consented data and no automatic research submission.

Keep image and video priorities, then explicit object/resource/view binding for3D.
For planning,4D means3D scene evolution over time, requiring timebase, coordinate
and object-continuity contracts; it is not a live modality or detector. No original
requirement or numeric gate is removed.

[History and standard execution contract](personal-tag-history-plan.md).
