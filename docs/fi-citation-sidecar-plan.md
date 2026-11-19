# FI local citation sidecar architecture and risks

Codex implementation lane, 2026-11-19. Base `c088bc6e60c17dc14410b14d4849a8d6f99e4ecf`.
This component issues no FI or other tag and changes no corpus-v1 or existing route.

## Architecture before implementation

The standard-library library and CLI take an explicitly selected UTF-8 subject
file and an existing private corpus-v1 file. `prepare` captures both and accepts
caller-declared numbered-marker-to-document-ID mappings. It writes a separate
private sidecar binding raw and frozen Unicode-15 NFC subject hashes, the exact
corpus bytes and manifest, document raw/NFC hashes, parser profile and source
identities. `check` recomputes those bindings before producing any observation.
The console carries only counts and fixed states. Optional private details carry
marker spans and identities, never source or subject text.

The finite literal grammar supports `[1]` through `[9999]` without leading zeros.
Balanced nested brackets, escaped markers, Markdown links/definitions, malformed
or unmatched brackets are recorded as unsupported rather than clipped to a
supported inner marker. Text without brackets has no selected markers; this is
not a claim that other citation forms are absent. Quotes, code, array indexing,
prose intent, source meaning and claim-to-source entailment are not interpreted.
Unbracketed URLs, author/year, superscript and other citation systems are outside
this profile. They are never reported as unresolved numbered markers.

Each supported occurrence is resolved-in-attached-corpus only when its declared
document is present with the captured bytes; without a declaration it is
unresolved-in-attached-corpus. Unsupported syntax has its own state. A resolved
mapping is a caller's association, not source authenticity, freshness, citation
correctness, truth or support. No document download, model, service or request is
performed. A changed subject/corpus/method invalidates the sidecar; no automatic
rebind or grandfathered result is permitted.

## Privacy and failure controls

Inputs are finite regular single-link files opened through no-follow directory
and file descriptors, with pre-read bounds and post-read identity checks.
Subject/corpus/sidecar inputs must be owner-private. Outputs require an existing
owner-private directory outside this checkout and are exclusively created at
0600, never overwritten. Every captured input is rechecked before publication;
temporary cleanup is attempted once. Post-publication cleanup/durability/close
failures explicitly report that output may exist, without promising rollback.
CLI parsing and runtime refusals emit
fixed diagnostics without path/argument/content echo. No raw subject, URL,
corpus text, source ID or linking hash is printed in the brief result.

Risks include deliberately misleading declarations, incomplete corpora, lexical
bracket ambiguity and linkability of private hashes/spans. The user explicitly
chooses mappings and private export. Permission checks cannot protect a hostile
same-UID process or authenticate installed project code. Bounded descriptors
protect file handling, not factual correctness. Linux/macOS CPython 3.10+ are the
intended standard-library environments; actual executions identify their OS.

## Acceptance for this component

Verify exact and repeated markers, missing mappings, unsupported syntax, frozen
NFC spans and no input text in either output; reject rebound subject/corpus/
document/source identities, duplicate/unknown fields, excessive inputs, unsafe
files, drift and existing outputs. Exercise actual prepare/check/refusal CLI
paths and unchanged quantitative-checker operation when this optional module
fails. Record source-bound counts and failures honestly. Full T-FI still needs
independent evidence-type labels/error reporting, accepted tag mapping and human
release operation. No original completion percentage changes.

## Publication-boundary correction plan, before code

The first candidate incorrectly treated all output I/O errors as ordinary
refusals. Injected temporary-unlink, failed rollback after directory-fsync, and
descriptor-close failures reproduce a complete final file existing after an
ordinary error. Preserve that failed receipt and the earlier successful controls.

Replace rollback assumptions with an explicit publication boundary: before the
link attempt, refusal guarantees no newly committed final destination; after a
successful link, or an unexpected error whose link outcome is unknown, raise a
fixed typed `OutputCommitUncertain` instead of attempting to promise rollback.
CLI exit2 remains Unavailable but adds `reason: output_commit_uncertain` and
`output_may_exist: true`. Known destination-exists refusal never overwrites it.
Attempt all owned descriptor closes; post-publication close/cleanup failures
retain uncertainty. Import failures must still yield the ordinary fixed refusal
without referring to an uninitialized module variable. Document inspect-before-
retry handling, including possible private temporary-name remnants; do not
automatically retry or remove a complete final file. Regression controls inject
the exact boundaries in the library and actual CLI, preserve no-final-output on
source drift/pre-link failure, and verify no private path/value echo.

## Raw output descriptor ownership correction plan, before code

Peer review found that `fdopen` can fail before taking ownership of the raw
temporary descriptor. The frozen candidate then removed the temporary name but
left the descriptor open after capture exit. An injected failure reproduces that
leak without a final destination; retain its failed receipt separately.

Keep the raw descriptor in the capture's owned list immediately after `open`,
and use `fdopen(..., closefd=False)`: neither stream construction nor stream
close owns that raw descriptor. Capture exit attempts its close exactly once
with all other owned handles even if construction fails. Preserve a primary
pre-publication body refusal when a secondary close fails. Never retain that
descriptor in a retry list after attempting close: it may already be closed and
its number reused. A failed close cannot justify retrying the same number.
This remains an ordinary pre-publication refusal. Direct-library and actual CLI
controls must show the raw descriptor closed/attempted, final absent, temporary
cleanup attempted, other handles closed, fixed private diagnostics, and no
unsafe retry after a close reports failure. Existing post-publication uncertainty
and no-overwrite behavior must continue to pass.

## Unsupported-label adjacent-target correction plan, before code

Automated review found that nested/escaped label classification skipped the
existing adjacent-target consumption branch. Consequently numeric brackets
inside a URL/definition could become separate supported markers. Preserve a
minimized reproduction of the frozen source, then separate balanced-label
classification from adjacent parenthesized/bracketed target or definition-line
consumption. Consume that finite opaque suffix even when the label is already
unsupported, retaining its unsupported reason. Do not consume unrelated text or
expand the declared syntax into general Markdown support. Test nested/escaped
labels with each target shape, mapped/unmapped target numbers, unmatched targets,
and subsequent standalone markers after a closed target or definition newline.
Fresh exact-source CLI demonstrations must show no hidden target marker becomes
resolved or unresolved. Preserve prior evidence and full FI acceptance limits.
