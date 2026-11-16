---
status: verifying
trigger: "Native iOS Practice sharing / Share explicit Check intermittently do not act on the first UI-test tap"
created: 2026-11-16
updated: 2026-11-16
---

## Current focus

Next verification: hosted iOS 27.2 standard exact-five run with the retained snapshot readiness and failure-count guard, original single taps, original assertions and bounds. Local uninstrumented candidate failed 0/2 with repeated upstream Recap HID corruption. The 200 ms duration hypothesis is falsified and reverted. No further unchanged local retry; no runtime Swift change; no selected proof replacement.

## Symptoms

Expected: first Practice sharing tap opens UIKit activity sheet; choose AI Trust ID; fixed synthetic text arrives; explicit Check returns PS; cancel/clear during check, repeat and details preserve lifecycle rules.
Actual: latest full run 3/5 (host workflows pass, two Share failures); unchanged-source focused diagnostic 1/2 (first tap leaves host app only; clear/repeat passes). Earlier all-five pass is historical, not acceptance of repaired behavior.
Timeline: repeated local and hosted source-identical runs differ. No root cause established by prior readiness / keyboard workarounds.

## Evidence

- Source baseline `0038d7a`; no native modifications on entry.
- Private `2026-11-15-share-without-signing/workflow.xcresult`: first synthetic Practice-share test fails waiting for AI Trust ID activity after one tap. Final hierarchy shows host only, fully visible practice-share frame x20 y603 w388 h44. Thus the observed button is not offscreen.
- Focused second Share workflow passes, including actual selected text and detector result. Do not infer universal detector startup failure.
- No concurrent signing/build in controlled diagnostic. System touch dispatch alone does not prove action entry.
- All previous results retained privately under coordination/scope-60/ios-distribution. No test deadlines/assertions weakened.

## Eliminated / unproven

- Offscreen practice button: excluded for the captured host-only failure.
- Signing prompt cause: unproven; failure also observed without active signing.
- Share remote placeholder instability: observed earlier, not explanation for host-only first-tap failure.
- Detector bytes/semantics: pinned; no changes permitted in this investigation.

## Architecture and risks before changes

First add diagnostics only to a private generated build, with source/payload hashes and explicit modified-file receipt. Capture touch/action/presentation events via fixed event labels only. Keep one native UI process, owned disposable simulator, unchanged acceptance tests and time bounds. Diagnostics cannot become selected five-workflow proof. Production fix follows confirmed evidence; scope remains UI event/lifecycle path and native tests/verifier if needed. Risks: instrumentation can perturb timing; a passing instrumented run alone is inconclusive; no runtime/input logging, credentials, signing settings or detector changes permitted.

## Experiments

Pending touch/action diagnostic.

- 2026-11-16: decoded the failed XCTest synthesized-event attachment. Single stationary tap at (214, 625), duration 0.05 seconds, correct app PID. Together with full visible button frame this excludes wrong target coordinates in that recorded failure; it does not establish touch delivery.
- Diagnostic `2026-11-16-share-touch-diagnostic` builds successfully; generated `Source/CheckerController.swift` alone is instrumented. Repository production Swift/tests remain unchanged. Simulator boot completed in 46 seconds; test phase underway within original two-test limits.

- 2026-11-16: private generated touch/action diagnostic passes both Share workflows; all three practice taps reach target-action and presentation completion; both actual Check actions arrive. Owned simulator removed, repository source hashes unchanged. This does not reproduce the failure and cannot establish a production fix.
- 2026-11-16: fresh hosted `0038d7a` run fails only activity-readiness in clear/repeat test. Exported screenshot/hierarchy shows the visible populated AI Trust ID cell and `activityImageView`. Readiness predicate starts 13.83s, image existence/hittable query stalls 14.75–26.73s; second evaluation at30.85s exhausts bound through image-query retries. Query amplification is observed for this distinct predicate timeout; no missing host tap is implied.

## Next discriminating experiment

Use original UIButton/UIScrollView classes and add generated-only UIWindow sendEvent tracing plus fixed action/presentation/lifecycle markers. Run the complete original five workflows once to observe any failed first action across the same host/Share sequence. This differs from the first diagnostic by preserving exact UIKit control classes and sampling event delivery above scroll gesture handling. A pass remains inconclusive; a failure will identify hit-view and gesture/action boundary without test retries or larger timeouts.

- 2026-11-16: original-control UIWindow diagnostic passes all five original workflows; every Practice and Share Check event hits the intended control and reaches action. Source hashes unchanged and owned simulator removed. This confirms diagnostic coverage, not an explanation for historical dropped actions.

Current next action: fixed four-cold-launch first Practice tap diagnostic using the same private event probe, with all four launches required and stop on first failed assertion. No acceptance retry; no production change; 120-second workflow allowance unchanged.

- 2026-11-16: four-cold-launch first-tap diagnostic fails on launch four. Exact intended button receives began at 11:07:17.279 then cancelled at 11:07:17.417, no ended and no target-action; first three receive ended+action. Source hashes unchanged and owned simulator removed. Failure video shows no visible banner or overlay.
- System comparison from retained xcresult diagnostics: failed XCTest virtual Recap digitizer sender is initialized twice on different backboardd threads (`unknown digitizer` on the second path). The subsequent stream repeatedly reports missing previous touch down / skips events. Cancelling the virtual service coincides with app cancelled contact. Immediately preceding successful tap has one initialization, contact touching→none, app ended+action, and no unknown-digitizer/skipped-contact events. Thus the captured failure is upstream synthetic input loss, not an app presentation or detector failure. Do not implement action-on-cancel in production.
- Next test uses one public 200 ms press rather than 50 ms tap, preserving original test limits and assertions. This is a hypothesis test, not a proven fix yet.

- 2026-11-16: candidate 200 ms experiment delivers all four intended first actions and visible activity cells. Overall diagnostic still FAILED: the diagnostic terminated its last app, and the existing teardown checks `hasSucceeded` before test completion, so it attempted an app screenshot on a successful-but-not-yet-finished test. The screenshot refusal caused failure. Preserve this receipt; do not call it a passed diagnostic.
- Applied test-only correction: one public 200 ms press/release for each single interaction, one snapshot for activity frame/content plus public cell hit point, original stable-one-second/20-second gate and all assertions. Teardown now captures on actual `failureCount > 0` rather than an incomplete run's `hasSucceeded`. No production source changes or retry added.

- 2026-11-16: uninstrumented focused candidate FAILED 0/2. First Practice never exposes activity. Second activity snapshot readiness completes in about two seconds, but selection does not open the extension. Both exact synthesized-event system windows show unknown/double-initialized Recap digitizers and skipped events for missing prior touch down. This does not establish an extension launch failure or explain every historical missing Check result.
- The 200 ms hypothesis is falsified and all duration edits are reverted. Retain only snapshot readiness and failure-count capture. Runtime Swift unchanged. Same five workflow names, assertions, single-tap count, every wait timeout and 120-second workflow allowance pass a static preservation audit. Final source combination has not passed an uninstrumented five-test run; hosted newer-runtime verification remains required.

## Resolution (bounded; not resolved)

root_cause: Captured cold Practice first action is cancelled upstream in Simulator/XCTest synthetic HID; actual application action was never delivered. Hosted readiness separately suffers repeated remote-query amplification. Earlier Check-result failure remains untraced.
fix: Retain one public cell snapshot per readiness poll plus actual failure-count diagnostic capture. Reject and revert the unsupported gesture-duration candidate. No production workaround.
verification: Diagnostic original-source instrumented 2/2 and 5/5 are NOT acceptance; cold50ms reproduction failed; cold200ms overall failed on diagnostic teardown; uninstrumented200ms focused candidate failed 0/2. Current final five-source acceptance is pending hosted iOS27.2. All owned simulators removed.
files_changed: mobile/ios/Tests/UIFlows.swift; docs/share-reliability-plan.md; .planning/debug/share-reliability.md
