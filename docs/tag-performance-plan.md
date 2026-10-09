# Tag performance and lean validation

Written 2026-10-09 by Codex before implementation.

## Architecture

Each tag modal and its static reference receive the same versioned performance
record. A build step derives PS development counts from a hashed regression run,
computes Wilson 95% intervals, and includes the measured mobile engine parity
checks. It verifies the run's method and dataset hashes against this checkout.
No test count, confidence interval or stage is inferred from prose. Missing data
renders “Not measured”, never a zero or a perfect score. Enterprise capabilities
and future tags have separate empty states and next tests.

The charts show development evidence, denominators and uncertainty. They do not
convert development examples into an independent holdout or runtime heuristic
scores into probabilities. Precision and recall have different denominators.
Browser emulation, runtime latency, label accuracy and release acceptance remain
separate dimensions. Method changes invalidate previous method-bound reports.

The existing on-device blind-review workflow is the data collection route for a
coordinated pilot: frozen shareable examples, two shuffled reviewer files, no
predictions shown, explicit labels and reasons, private file return, comparison
and adjudication. No raw answer upload, telemetry, new endpoint or database
permission is introduced by this UI change. Automatic research intake still
needs its own implemented consent, identity, retention, deletion and isolation
contract. A public bug report is not training consent.

## Risks and controls

- A 100% development point estimate can look like accuracy: show the 95% range,
  actual counts and “Development examples” immediately beside it.
- Stale metrics can survive a detector update: verify method and fixture hashes
  at build; fail when they differ.
- Phone emulation can be misread as hardware testing: identify Android Chromium
  and iPhone WebKit as emulated, retain physical-device status separately.
- Timing can blend cold load and warm execution: collect and label these
  separately; do not claim production hardware latency from desktop emulation.
- AI-created samples can repeat one template: use them for stress/regression,
  reserve independently sourced, frozen, representative samples for evaluation.
- Proprietary assistance could become a self-certifying oracle: preserve separate
  suggestion and tag-evidence roles, method/version provenance and public tag gates.

## Small-team validation route

1. Freeze the PS job and sampling protocol. Supported command risk is the target,
   not scam identity or universal safety. Choose strata before predictions.
2. Build a new authorized corpus with source and template-family provenance.
   Independently sourced instructions, benign downloads, warnings, quoted text,
   mixed contexts, multiline forms and unsupported forms are separate strata.
   Group near duplicates by source/template family; do not multiply n by repeats.
3. Two blind human reviewers label and give reasons, using the existing phone
   form. The product owner can coordinate but cannot replace two independent
   judgments with Codex/Claude agreement. Adjudicate and retain ambiguous cases.
4. Freeze hashes and accepted policies, then run predictions once. Publish
   precision TP/(TP+FP), recall TP/(TP+FN), counts, intervals and category failures.
   A stratified or enriched corpus supports that declared test population, not
   an unqualified population-wide precision claim.
5. Run automated Android Chromium and iPhone WebKit parity, accessibility,
   network-canary, invalid-bundle, stale-input and offline checks. Record a small
   physical-phone and human assistive-technology acceptance check separately.
6. PS release depends on its complete gate. PII has a separate procedure/order
   and recognition-coverage gate; its thresholds are not inherited from PS.

At two-sided Wilson 95%, 52/52 predicted positives has a lower bound above
0.93. At 12/12 ground-truth positives the recall lower bound exceeds 0.75.
These are mathematical denominator minima with no errors, not a sufficient
sampling design or a promise that 52 handpicked examples validate the tag.
With a false positive the denominator must be larger; the executable sizing
report records the exact calculation. We need examples and reviewers, not
thousands of recruited users or an advertising budget.

## Proprietary assistance

An organization-specific assistant can help explain findings, suggest examples,
triage consented feedback or apply private policies. It stays distinct from
public reproducible tag issuance. Every suggestion needs bounded wording;
training data needs actual permission and lineage; a model cannot independently
validate its own labels. Public personal detection/evidence stays free and
inspectable under the current scope. Any closed model must be identified as a
closed component, not marketed as an entirely open-source stack. No model is
trained or introduced in this increment.

## Acceptance

Every one of 20 modals and static references has a compact performance panel.
PS shows counts, denominators, intervals and declared candidate thresholds.
PII shows the procedural/recognition distinction. Unimplemented tags show
unmeasured states with their own next validation task. Charts work with keyboard,
screen-reader text, 320px layout, 200% text, light/dark and no JavaScript reference.
The two mobile engine suites execute all 86 development examples. Reports are
published with timestamp and source hashes. No collection is silently activated.
