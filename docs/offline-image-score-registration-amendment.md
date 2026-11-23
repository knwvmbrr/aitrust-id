# Image-score source registration and manual acquisition gate

Recorded BEFORE registration code: 2026-11-23T17:59:34.379782+00:00

Base e5d2233db71dcab5c9c9c44acd305e881a1c9670 on isolated codex/nov23-image-source-integration. ROOT approved only finite verifier patterns, four protocol source commands (72 to76 preserving every existing command), one ordinary CI source-only step, a pure workflow guard and the qualification workflow. No ROOT worktree changes.

## Mandatory architecture amendment

The qualification workflow must be MANUAL ONLY: workflow_dispatch with required expected_commit input, no push/pull_request/schedule/workflow_run/workflow_call trigger. Its job must require the exact owned repository, event, trusted integration branch/ref and expected_commit equal to github.sha. Before acquisition, a fixed Python guard verifies a40-lowercase-hex exact commit against GITHUB_SHA and the checked-out HEAD. Pass input only through step env; never interpolate it into shell code or use it as a command/path/URL. Publishing the integration branch for ordinary CI cannot acquire2GB. No dispatch is authorized now.

No runtime/asset/model/crop/CPU/pipe/resource/time/cleanup semantics change. All8 shared source inputs and numerical production sources stay exact. The83-source map is a NEW observation with one changed workflow hash, not a replacement/rebinding of the original83-source proof. New registration/guard/amendment inputs are bound separately. Retain original96-file import, historical source/peer/failure receipts and old workflow in immutable Git history.

## Owned source-only delta

- scripts/verify-route-boundaries.py: append a finite image source cohort; preserve all existing patterns and gate behavior.
- eval/revalidation.json: append exactly three explicit stdlib test-file commands plus check-lock to protocol; preserve72 commands and every other capability.
- .github/workflows/ci.yml: add one read-only spec step with those same four source-only commands; no package/install/permission/runner/secret change.
- tests/test_visual_score_workflow.py: parse fixed workflow fields and exercise the actual pre-acquisition guard with inert subprocess substitution. Positive exact identity plus wrong event/repo/ref/commit/malformed/missing/checkout mismatch must refuse. Verify manual-only dispatch, fixed inputs/permissions/pinned actions and only declared safe report paths. No YAML library, SDK, model, network or acquisition executed.
- .github/workflows/visual-score-qualification.yml: implement the manual gate only and add the pure source guard test. Preserve all acquisition/install/reference/isolation/cleanup bodies, durations and assets.

EXCLUDED: tools/source_release_policy.py, closed source-copy assessment, grant tests and selected eval/route-boundaries.json evidence. Another author owns source-rights V2; ROOT coordinates grant mapping and finite inventory capture later. Do not rehash selected evidence to make it appear current. No global current/protected/publication claim.

## Verification and risks

Run only the three source-only stdlib files and check-lock, preserving any failure. Compare first72 protocol commands, all other capabilities, old CI source,83-source map and8 shared inputs. Review all inline Python and shell syntax without executing workflow phases. Obtain distinct source/workflow peer review before final guarded source commit. ROOT later schedules affected profiles: eval/revalidation.json is COMMON to allfive, so allfive old fingerprints become stale.

Manual gating prevents automatic acquisition, not all operator mistakes. Current model path remains UNQUALIFIED; eventual source publication is not native execution, grant admission, FA/PA/origin/accuracy or an original closure. Unreviewed workflow edits require a fresh exact source review and explicit future execution approval. Runtime known resource constraints and total35-minute hard job cap remain unchanged.

### Pre-code registration compatibility detail

The unchanged protocol.revalidation.load validator permits only the existing `-m pytest` module runner or fixed script paths; it does not accept `-I/-S/-m unittest` manifest commands. Therefore the three stdlib-authored test files are registered via the existing pytest runner (`{python} -m pytest <literal file> -q`) plus the fixed check-lock script. Ordinary CI uses those same four commands and its existing pinned dependencies. No loader/validator rule or new dependency is introduced. The test code itself remains stdlib-only and does not execute native inference. This detail is recorded before registration feature edits.

### Actual stale assertion repair amendment

After the registered source31 passed, the existing qualification file returned31passed/1failed: test_workflow_no_secret_signer_or_required_gate still expected the original exact branch. The approved workflow now deliberately requires a different branch and manual-only identity. Failure/source/log hashes are preserved in the first-failure record. Before touching that test, the repair is declared: replace only its branch literal with the approved integration ref and add explicit manual-event/expected_commit-equality checks. Preserve all other assertions and32 methods. This adds the existing test file to the approved-image correction delta; no runtime or resource change. The final83-source observation consequently has TWO changed hashes (workflow and this test),81 unchanged; the original handoff and all prior observations remain historical.
