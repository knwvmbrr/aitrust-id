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
