# Bounded configuration verifier navigation

The first default-APK candidate passed the seven original controls but failed the
supplemental rotation wait. Its hierarchy had the owned editor and no visible
status. It did not record actual rotation or exact edited text, so status below
the landscape viewport is a source-supported hypothesis, not that run's proven
cause. Keep the [failed producer](../runs/2026-11-21-android-default-configuration-failed.json)
failed. Do not change the product handoff while investigating this verifier gap.

The corrected rotation check uses one existing 40-second wait and a finite state
machine. It first requires observed rotation1 and an editor exactly matching the
validated synthetic edited draft. It may scroll only when the status node is
absent, using the unique owned ScrollView's outer margin. At most two upward
gestures find the required received/no-result status; at most two downward
gestures bring the editor back for an exact post-receipt comparison. No new
per-substep wait or deadline reset is introduced. Wrong editor values, result
tags, Ready/Cleared states or missing required receipt fail rather than waiting
for a later correction. Foreign or malformed scroll bounds receive no gesture.

Evidence retains only finite rotation/state enums, visibility booleans, a gesture
count and exact-editor-match booleans. When no editor is visible the match is
unknown/null. The first scroll's positive precondition snapshot is retained.
No editor values, input hashes, coordinates, IDs or hierarchy dumps are retained.

The separate immediate rotation-to-HOME exercise keeps its original adjacency
and fast task refocus. An observed marker during final-rotation verification fails
immediately; it cannot be hidden by waiting for later clearing. All seven original
checks and product source bytes remain unchanged.

Normal PR/push default-APK jobs now request both supplemental configuration checks
automatically. Manual default jobs honor the explicit input; manual diagnostic
jobs omit the checks unless an invalid combined request is explicitly made, which
the helper refuses before SDK activity. A finite event/input matrix executes the
actual argument-selection shell block and compares automatic and manual-true
arguments. There is no extra emulator job or changed license/permission/deadline.

Before one reviewed changed-source candidate, preserve the old/new offscreen
fixture outcome, run affected fault/source controls and obtain separate review.
The old failed runtime is not recovered or promoted. Actual default7+2 acceptance
remains pending until this new producer executes it; no physical/human/full
original requirement closure is implied.
