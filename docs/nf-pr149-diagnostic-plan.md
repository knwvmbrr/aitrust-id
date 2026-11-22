# PR149 NF timing diagnosis before source changes

Codex / web_camo, 2026-11-22. Isolated branch from
7174a3f49a3365ceff241d2b3ff5bd74d1be5598. The actual hosted canonical command
expired at180266ms under the unchanged180000ms release wrapper. Its last
Chromium chunk_import_render/render mark precedes navigation, authored failure,
fallback wait, actual PS/MT recovery and context close. It does not prove a
React render defect. Preserve that failure and all prior receipts.

## Architecture and risks

The existing two NF verifier scripts, their focused diagnostics test, the
fixture builder diagnostic hook, this plan, one new diagnostic workflow and
attributed run/change records are owned. Root explicitly added the fixture
builder handoff before feature edits.
No application, worker, method, fixture-builder, release criteria, shared CI,
selector, scope or state changes. The release wrapper's180000ms browser and
50000ms result budgets, all33 canonical cases,8 corruptions and every existing
privacy/lifecycle/failure assertion stay intact.

Add fixed, closed progress substeps at fault-context creation, navigation,
authored trigger, fallback observation, peer checks and context cleanup. Root
approved an optional fixed-token tester callback in the fixture-only
__peerChecks closure, preserving client creation, exact PS/MT input bytes, the
PS-then-MT await order, returned whole records and finally-stop cleanup. The
callback receives no inputs/results. Callback failures refuse the diagnostic and
must still stop both clients; there is no application behavior change. This
simple hook replaces the originally considered Worker proxy before feature code.

Progress is logged only through a closed fixed-field projection of existing
stage diagnostics. The original finite512-event budget remains. Retain two safe
JSON reports on failed hosted diagnosis for7days; never upload screenshots,
console text, private logs, user inputs or source/workspace paths in diagnostic
fields. Report this as timing observation, not independent detector evidence.

The new read-only PR-filtered Ubuntu24.04 workflow uses existing pinned actions,
Node22/Python3.12 (matching the failed site job), hash-locked eval dependencies and locked npm installs. It runs
inert diagnostics, builds the same standalone fixture and verifies actual hosted
capacity/concurrency2 before a sole full canonical diagnostic invocation. A
separate300000ms supervisor bounds this measurement, with a fixed deadline
outcome and cleanup; it is explicitly not the180000ms release gate or acceptance.
No release-wrapper override, new endpoint, signing, secrets, model or install on
the owner machine. Public standard runners are ephemeral. Preserve all outcomes.

If the new evidence identifies a performance defect, propose its concrete fix
separately. A diagnostic pass beyond180seconds cannot clear PR149. No local
browser/build/SDK execution is authorized below the2GiB reserve; use only focused
inert tests/syntax now. Root reviews the frozen commit before push/launch.

The hosted diagnostic must verify actual GitHub-hosted Linux concurrency2 and
4 available CPU threads before launch, recording actual memory via the existing
capacity schema. It initializes two explicit unavailable JSON placeholders, keeps
the one300s measured child bounded with GNU timeout and a5s SIGTERM-to-KILL cleanup margin, and
uploads only the two fixed JSON paths. Existing canonical fixture90s and inert
controls30s setup bounds are retained. Setup and browser dependency installation
are separate bounded steps on the disposable public runner. No local runtime or
SDK installation occurs.

## Peer cleanup correction before hosted launch

The f638 candidate placed the browser-close begin marker inside the same try as
close. A marker's report/console failure could therefore skip close entirely.
Preserve the original source-control-flow finding; it was not a browser runtime
reproduction. Before correction, make cleanup independent of both begin/end
checkpoint success: catch checkpoint failures, always attempt the owned close
exactly once, emit completion only after successful close, and keep diagnostic
failure distinct from actual-close completion. Either failure invalidates the
cohort. Apply the same helper to fault-context close; browser-finally remains the
backstop for failures at any earlier marker. No assertion, application, worker,
180s wrapper or50s wait changes. Prove begin/end/both checkpoint faults, real
stub close refusal, context-to-browser backstop and ordinary cleanup with inert
objects only; no local browser/native/SDK run.

Treat even null/undefined/falsy JavaScript throws as failures; diagnostic failure
truth must not depend on a thrown value being truthy.
