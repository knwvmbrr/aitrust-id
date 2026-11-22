# SynthID reference vendor-input delivery plan

Recorded before implementation, November 21, 2026. Target: F-155 and the unchanged
WP-INTEGRATIONS input/isolation/install-use-removal contract. No original
completion, tag adoption or independent accuracy is granted by this plan.

## Existing contract and selected outcome

F-155 requires delivering SynthID/vendor watermarking as an input and extending
supported workflows without disabling personal checks. The original supported
and failure demonstration, versioned evidence and platform install/use/removal
requirements remain. The separate tag-specific numeric gate is not applicable to
this input-only profile: no classification threshold or tag is introduced.

The existing `scripts/check-tags.py` CLI will accept an explicitly selected
SynthID reference packet alongside its independently selected PS/privacy checks.
Default invocation and its v1 result remain unchanged. Opt-in uses a new envelope
with the original personal-check result plus an independent vendor-input result.
Token IDs are a separate subject; this route does not assert that they encode the
CLI's unrelated text, that the caller's generation declaration is authenticated,
or that an observed statistic resolves to a credential or manifest.

The supported method is the official Google DeepMind SynthID Text 0.3.0
FrequentistDetector at immutable commit
`6452fbb837d0ad4281ccddb94b0af75d219b1a14`. Its matching single-key generation
configuration and generated token IDs with the prompt removed are caller-declared.
The selected bounded profile fixes ngram length5, depth30, history1024 and
single-key/two-leaf tournament processing; accepts at most512 IDs and a bounded
vocabulary/EOS and explicitly public research key. It does not guess production
keys, inspect Gemini output, tokenize arbitrary text, load model weights or claim
production suitability. Upstream explicitly calls this a research reference.

## Architecture and privacy

Copy the exact three required upstream modules and Apache license into an isolated
optional integration directory with immutable hashes/URLs. Install their pinned
runtime dependency cohort only into an explicitly owned private CPython3.12
macOS-arm64 virtual environment using existing hash-locked wheel cache; no global
packages, model download, network runtime or production service is needed. The
standalone worker imports only this fixed profile and returns raw p-value,
scored positions and binomial trial/one counts. A zero-position result is
Insufficient, never negative evidence or human origin. No threshold is applied.

An untrusted packet cannot select code, import paths, models or executable.
Runtime location is a separately trusted operator option. The worker has bounded
input/output, one CPU thread, a parent wall deadline and owned process cleanup.
The optional module is lazily imported only for explicit vendor selection.
Missing dependencies, malformed records, timeout or worker failure affect only
vendor evidence; existing selected personal checks still return their own result.
No new enum, protocol assertion, API route, UI promotion or strong WATERMARK input
is created. In the current adjudicator, verified WATERMARK requires decoded soft
binding resolved to a validated manifest; these statistics cannot satisfy it.

Default console output omits token IDs, key, paths, subject hashes and raw
metadata. Explicit JSON adds bounded public configuration and token-subject hash,
which can link examples and must be handled privately. No telemetry, upload,
storage, source text or automatic collection is introduced.

## Evidence and failure gates

Before code: verify exact upstream bytes and pin the accepted input-only profile.
After implementation: actual official generation on fixed synthetic logits and
canonical full statistical parity, unmarked control, wrong/malformed config,
zero positions, repeated/EOS masking, limits, missing SDK, malformed result,
timeout/owned reaping and independent PS outcome. Demonstrate actual supported
platform install, CLI use, removal and PS use after removal; claim only the
platform executed. Preserve failed candidates and obtain a different review.

Risk: public research keys are forgeable; no authentication follows. A p-value is
conditional on the declared matching generation setup and upstream statistical
assumptions, not probability of AI authorship, confidence, truth or a valid tag.
Unsupported vendor keys, dual-key schemes, other tokenizations/media and
transforms remain unsupported. No natural-text false-positive accuracy is
claimed. Distribution/source notice and platform obligations remain explicit.

## Pre-implementation acceptance

Codex PM accepted this exact input-only technical contract on November21,2026 under Michael’s standing implementation request, before feature code. This is not a Michael acceptance vote, production key grant or taxonomy adoption. The private offline dependency install is authorized up to0.8GiB while retaining at least2GiB free; no weights, network runtime or service activation. Only actual executed platform support may be claimed.
