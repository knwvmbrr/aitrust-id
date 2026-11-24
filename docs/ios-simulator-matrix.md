# Representative native layout checks

This separate source-only tool is not yet native-qualified. It leaves the current
seven-flow iPhone14Plus proof and application code unchanged. It prepares the same
46-member developer project with exactly one test-source replacement: the new
layout fixture instead of the seven-flow test source. Other45 members stay exact.

After different source review and explicit native-slot scheduling, use an existing
accepted Xcode/SDK and installed iOS26.2 runtime23C54. No download or installation
is performed. Create an owner-private0700 output parent outside every Git checkout;
the selected output must not exist. Run small first; a failure stops the matrix.

```
python3 -B scripts/verify-ios-size-matrix.py --output /private/owned/new-layout --profiles small
```

The other finite profile names are regular, plus and max. These correspond to
SE3,14,14Plus and17ProMax. They are representative size classes, not a claim to
cover every iPhone model or OS. Each device is created with a unique owned UUID,
three targeted light/dark/enlarged-text configurations run serially, then that
UUID is deleted and inventory absence checked before the next profile. Existing
user Simulators are never selected, changed or removed.

Only fixed invented text enters the app. The fixture checks actual native typing,
PS result/evidence controls, clear/no stale result, bounded scrolling, visible
control/label geometry and bundled notices/page/source-row navigation. It does
not open the source ZIP or repeat the full seven-flow Share matrix. The layout
result is a distinct observation, never a seven-flow/physical/human VoiceOver pass.
Screenshot geometry is not proof that all glyphs are readable: inspect every
selected App/evidence/notices PNG at full size before presentation acceptance.

Exit0 means the declared automated observations and owned cleanup completed;
visual_review_completed stays false until a separate actual visual review. Exit2
means unavailable/failure with private artifacts retained. No output is overwritten
or recursively deleted. A publication/close failure may leave a complete output;
inspect before trying another path. Neither a JSON file alone nor a prior proof
establishes the outcome of a failed CLI invocation.

The build disables developer signing; SDK linker-generated ad-hoc metadata may still exist. No developer credential or signature-free claim follows.

The independent process supervisor streams bounded logs, owns/terminates/reaps its
process group and preserves partial failure evidence. Build600s/boot180s/case120s
and three-layout aggregate UI780s are maxima, clamped down to shared remaining
time. Cleanup90+15s uses the original whole-device deadline. SDK internal storage,
allocations and remote accessibility snapshots are not kernel-hard-bounded;
free-space reserve checks are observations. Parent/host crash or detached/uninterruptible
OS processes are not universally recoverable. No physical-device, human usability,
independent accuracy, signing/upload, release or original requirement is completed.
