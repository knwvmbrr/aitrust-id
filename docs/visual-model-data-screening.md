# Visual model and persuasion data — first screening

Primary pages read November22,2026. Engineering screening for the existing
visual execution plan; no model or dataset downloaded, installed, trained,
benchmarked, accepted or released. No change to the202 original requirements,
accepted tag meanings, independent validation or approved metadata-only pilot.

## One small VLM candidate, with a specific job

Hugging Face's **SmolVLM2-256M-Video-Instruct** card declares Apache2.0 for its
checkpoints and image, multi-image, video and text inputs producing text. It
reports1.38GB GPU memory for video inference. Those are publisher descriptions,
not our measured CPU, iPhone, latency, memory or authenticity results. The card's
examples use CUDA/FlashAttention; video examples add decord. It also describes
English use, possible factual errors and unsuitable high-stakes uses.
[Official model card](https://huggingface.co/HuggingFaceTB/SmolVLM2-256M-Video-Instruct).

**Candidate job:** propose visible text, objects and selected-frame descriptions
for a user to inspect, with region/frame identity. A description is an observation
proposal, not proof of AI generation, manipulation, propaganda, author identity
or truth. It receives no credentials, tools, filesystem, network or device action
authority. OCR/media instructions remain untrusted data. No automatic action on
a person follows a model output.

**Before implementation:**

1. Pin an actual revision and record model/config/processor/tokenizer/weight
   hashes, selected code and all applicable notices. Audit the chosen dependency
   and decoder chain, base components and data obligations separately. A card's
   license field is not the completed full-distribution review.
2. Choose a supported implementation for the actual available hardware. Confirm
   a CPU-compatible path rather than copying CUDA requirements onto the VPS or
   phone. Measure cold/warm load, RAM/VRAM, disk, input size, frames, runtime,
   energy and cancellation on each claimed route before promising portability.
3. Freeze local-only loading, bounded image/clip inputs, frame/time identities,
   no remote URL fetching or arbitrary code loading, finite output and a killable
   worker. Keep the model optional so PS and other tags survive its absence,
   crash, overload or timeout.
4. Compare against a simple OCR/description baseline on licensed material.
   Score text/region/frame errors and uncertainty separately from any future
   detector's actual generation/edit/technique task. Include instruction-bearing
   images, text-only images, benign editing and out-of-distribution content.
5. Publish exact limits and measured errors before a user-facing inference
   claim. Actual tag-specific independent acceptance remains mandatory.

This is a candidate for a bounded descriptive role, not the selected universal
AI detector or a claim that new proprietary training is required.

## Persuasion benchmark: access and rights block product adoption

The official SemEval2024Task4 page distinguishes20 text techniques from22
multimodal techniques, with hierarchical multilabel scoring and a separate
binary task. It describes registered-team data access and restricted test labels.
It explicitly limits dataset use to scientific research and prohibits third-party
redistribution. Publicly readable examples and a research paper do not supply
product-training or redistribution permission.
[Official task, data and participation terms](https://propaganda.math.unipd.it/semeval2024task4/).

**Decision for now:** use the published task design to inform evaluation planning;
do not copy its corpus, images or annotations into the repository, application,
commercial service or downloadable fixtures. No registration or terms acceptance
has been performed. A participant's public code license would not automatically
license the underlying memes.

**Executable next actions:**

1. Resolve explicit, purpose-compatible rights before selecting a dataset. Keep
   evaluation-only and training permissions distinct. Skip this corpus for product
   use unless the needed rights are actually obtained; continue with a compatible
   source rather than treating restricted access as an engineering permission.
2. Build an original or permission-compatible evaluation set with independently
   coordinated context labels. Include quotations, reporting, debunking, satire,
   ordinary advertising, legitimate urgency and culturally varied counterexamples.
   Public visibility alone does not establish image reuse rights.
3. Freeze splits by source/meme family and generation/edit pipeline; detect
   near-duplicates. Keep a clip/meme as the sampling unit and retain an unseen
   holdout. Multiple frames or model answers are not independent reviewers.
4. Evaluate each supported technique and its evidence/uncertainty. Keep OCR,
   contextual interpretation, origin and factual verification errors separate.
   Detecting a technique does not establish deceptive intent or falsity.
5. Retain existing consent boundaries. The approved optional feedback pilot
   collects metadata, not a new image/video training corpus. Any contributed
   example needs its own informed permission, preview and applicable retention.

Scope and ordering: [visual execution plan](visual-tag-execution-plan.md),
V05/V06/V07/V08/V11/V12. This screening selects no new live tag or numeric gate.
