# Native Share reliability investigation

## Observed boundaries

Keep missing host target-action, remote activity readiness and detector startup separate until evidence links them. The controlled unchanged-source failure shows only the host after a correctly centered 50 ms tap. A private generated-only touch diagnostic then passes both Share workflows and records target-action and presentation completion. A passing diagnostic does not explain an earlier missed action.

The latest hosted failure is different: its final screenshot shows the populated AI Trust ID activity. Its readiness predicate spends most of its 20-second budget in repeated remote existence/hittability queries, including a 10-second image lookup, before it can establish two stable samples. The existing private-image queries amplify accessibility work and fail before the single activity tap.

## Architecture before changes

Keep production sharing, typed-provider validation, explicit Check, pinned detector/runtime, deadlines and result/lifecycle assertions unchanged while identifying the missing-action boundary. Private generated diagnostics record only fixed event labels, known control identifiers and gesture states; they never record input text and cannot replace selected acceptance proof.

For activity readiness, request one public cell snapshot per evaluation. Inspect its frame, enabled state and descendant image geometry in memory. Require the same nonempty frame to remain stable for one second, then query the cell's public `isHittable` once before the one real activity tap. Keep the existing 20-second wait. Avoid repeated queries of the private `activityImageView` identifier. Continue to require actual extension entry, exact synthetic provider text, no automatic result, explicit local Check, details, clear/cancel and repeat behavior.

Apple documents [snapshot()](https://developer.apple.com/documentation/xcuiautomation/xcuielementsnapshotproviding/snapshot()) as a capture of the element and descendant hierarchy, [snapshot children](https://developer.apple.com/documentation/xcuiautomation/xcuielementsnapshot/children) as in-memory descendant snapshots, and [isHittable](https://developer.apple.com/documentation/xcuiautomation/xcuielement/ishittable) as proof of a current onscreen hit point. These contracts support the test design; they do not establish application acceptance.

## Risks and verification

A snapshot can still be slow or fail; retain that failure and the original deadline. Descendant image geometry is a content-readiness precondition, not proof of detector readiness. Instrumentation can change scheduling; diagnostic passes cannot establish a root cause. Validate the readiness change with the affected two Share workflows, then all five uninstrumented workflows, preserving every prior failure and exact source identities. A failed native result must remain failed. Current hosted acceptance, physical-phone workflows, human accessibility, independent accuracy and reviewed TestFlight upload remain separate gates.

## Captured cancelled synthetic contact

A fixed four-cold-launch diagnostic reproduces the missing first action on its fourth launch, then fails and stops. The intended Practice button receives a began contact and then a cancelled contact, without an ended contact or target-action. The retained video shows the host with no visible banner. No production source was changed, source hashes remain stable, and the owned simulator is removed.

The retained system logs distinguish that failure from the immediately preceding successful tap. In the failed event, XCTest creates a virtual Recap digitizer; backboardd takes two initialization paths for the same sender and then skips events because it cannot find the prior touch down. The app receives cancellation when that virtual service is destroyed. The successful event has one initialization, a normal touching-to-none transition and an ended contact that enters the action. This establishes upstream synthetic input loss for the captured failure; it does not justify firing an application action on cancellation or claiming physical-device behavior.

Private comparison log hashes are `35332e2d4f41ddc3409075d1aa43f44d6a8cade2595924a407e854eab0f85a65` (failed event) and `23970e17841fff65657e9eb427730e028f60afb7d6f87e94fafd87402b8b4d06` (successful event). The failed diagnostic receipt hash is `6925af7f0e19d8f42760d47cb67b2e1918168088e0f5a09d38349dd986fb78b3`. Raw simulator diagnostics remain private.

Before changing repository tests, test a single public 200 ms press/release in the same fixed cold-launch experiment. Require all four first actions to complete, retain cancellation traces and the original deadlines, and stop on any failure. A passing result alone does not prove the underlying simulator defect fixed; full uninstrumented app/Share acceptance remains required.

The candidate 200 ms experiment delivered all four first actions and activity cells, but its overall receipt is **failed**: the diagnostic terminated its final app and the existing teardown requested a screenshot before the test was marked finished. `hasSucceeded` is false at that point even when the assertions succeeded. Use the actual failure count to decide whether to capture failure attachments. Preserve this result separately from the earlier cancelled-contact failure.

The public [press(forDuration:)](https://developer.apple.com/documentation/xcuiautomation/xcuielement/press(forduration:)) duration candidate was then tested uninstrumented with both Share workflows. Both cases fail (**0/2 passed**): first Practice does not expose the activity and the second activity selection does not open the extension. Both retained synthesized-event system windows show unknown/double-initialized virtual digitizers and skipped prior-contact events. Longer contact is therefore not an established remedy, and all duration edits are reverted. Preserve the exact failed source and receipt; do not reinterpret this as an extension launch failure.

The final repository change retains only one-snapshot readiness and failure-count diagnostic capture. In the failed focused run, the new activity-readiness condition did complete in about two seconds before the subsequent input loss. The original five workflow names, all assertions, single-tap count and every deadline remain; production runtime Swift is unchanged. The final source combination has no current full-five pass. Next verify it once on the newer hosted iOS 27.2 runtime. No unchanged local retry, source guard bypass, selected-proof replacement, physical-device claim or universal input-reliability guarantee is authorized by these diagnostics.

The focused failed receipt hash is `d8fdf76a0524b967f3972954664f8a5cca0aca38f60ef3e270cdac069122ac08`; exact attempted generated test-source hash is `7eaea952a54af61d667dd797c3b958f882100a24b139729267faa97485a303ec`. Raw logs and result bundles remain private. The original untraced Check-result failure remains separate from the captured cancelled Practice contact.


The first hosted final-source attempt (`43908324857`, attempt 1) is unavailable
before compilation/UI execution: `simctl bootstatus` exceeds its existing
180-second deadline on iOS 27.2. Owned simulator cleanup succeeds. No workflow
pass or application defect is inferred from this unavailable host. Retain its
receipt and perform exactly one fresh-host replicate at the same source, limits
and cost tier. A repeated failure stays failed; do not retry until green.


## Bounded boot observability

The one fresh-host replicate also stops at boot, with a shutdown deadline and
strict cleanup still false despite eventual deletion. No more unchanged retry
is used. A controlled child process proves that regular-file stdout loses an
unflushed phase on termination, while a terminal exposes that phase beforehand.

Only bootstatus now uses a nonblocking PTY and its documented migration-detail
option. Readiness-based draining preserves progress within the original
180-second bound. Default JSON commands retain regular-file output; command
events retain exact output byte counts/hashes and final return codes. Before
boot, record only free space and documented numeric memory/CPU values under a
five-second query bound. No hostname, environment or whole-system log is taken.

Risks are terminal CRLF formatting, EIO at terminal close, a noisy child delaying
a deadline, descriptor leaks, and accidentally treating a capture failure as
command success. Real-process controls exercise these boundaries. A first burst
control exposed fixed-sleep throttling; readiness-based waiting fixes it under
the unchanged five-second synthetic limit. The failed candidate is retained.
All 117 adjacent packaging/verifier controls pass on the final source. The two
old native-proof checks still fail their source guard, as intended. No simulator
startup, current full-five pass or TestFlight availability is inferred.


## Result-collection lifecycle ordering

### Evidence and limit

Hosted run 43914592758 completes boot, build and all five original UI workflows,
then reaches its unchanged 30-second xcresult summary deadline. Its owned
simulator is cleaned up successfully afterward. A later separate inspection
parses the retained result bundle and confirms five passed, none failed/skipped.
The original proof remains failed; that recovered summary cannot replace it.
The host reports 7 GiB memory, three logical CPUs and 37.5 GB free disk. Resource
pressure as the cause of the summary deadline is not established.

### Architecture before implementation

After UI execution finishes, capture the selected source hashes immediately,
even when the UI command itself failed. Retain these under explicit post-UI
fields. Reclaim only the verifier's owned disposable simulator before parsing
its result bundle. The xcodebuild command has already exited and the result
bundle is stored in the private output directory; simulator deletion must not
remove or rewrite that bundle, project, sources or logs.

Use one cleanup function and one attempt flag for shutdown/delete. Always try
delete after a failed shutdown, but require both commands to succeed. A failed
cleanup stops acceptance before result parsing and must not be retried by the
outer finally block. Failures before UI completion still reach the same cleanup
function from finally. Record a final source snapshot when a post-UI boundary
exists, including on later result failure; missing or changed source identity
keeps the proof failed.

Retain the existing 90-second bound for each cleanup command, 30-second result
summary, 600-second UI/build commands, 180-second boot, exact five-test predicate,
source identity gate and strict owned-simulator cleanup condition. No retries,
new runner, recovered-summary override or increased deadline. The change
releases an unnecessary live resource; it does not establish a memory diagnosis
or guarantee the next summary command will finish.

### Risks and verification

Risks are duplicate cleanup, accidentally parsing after failed cleanup, masking
an original failure, dropping post-UI source identity, or treating xcodebuild's
zero exit as sufficient acceptance. Exercise main's real report lifecycle with
fake external commands and real temporary report files: success order; summary
deadline; invalid summary; shutdown/delete failure; UI/build failure; source
change or unavailable capture; source change during result handling. Assert one
cleanup attempt, original command bounds and exact-five/source/cleanup gates.
Retain the existing real subprocess/PTY tests. No native/UI execution is part of
these focused tests. Actual acceptance requires a new complete source-bound
producer run after handoff.

Final adjacent controls pass 130/130, including an interruption that retains the
original interruption and a failed cleanup record instead of masking it with a
missing-key error. These are lifecycle controls only; the next full producer run
must still pass all five workflows, strict cleanup and the original summary
deadline before the selected native proof can change.
