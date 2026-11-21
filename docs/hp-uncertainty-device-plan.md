# HP uncertainty-word preview: bounded software plan

Source base: `f5c03183b2e6176cb64a798664a5c7ee7d4a5e5a`.
Owner: `/root/web_camo`. Original scope: T-HP and F-018, whose full acceptance,
percentages and contextual/human validation requirements are unchanged.

The missing usable job is an optional on-device view of the existing English
hedge observation for a whole passage the caller explicitly selects as an
expected-uncertainty context. It reports lexical words and a narrow calendar
exclusion, not whether uncertainty is necessary, a statement is true, a person is
confident, or an HP tag. This is not independent accuracy validation.

## Architecture before implementation

- A new `tools/hp_uncertainty_device.py` adapter calls the byte-unchanged
  `tools.language_observations.observe('hedge', ...)` method with a closed,
  subject-hash-bound whole-NFC-passage annotation. The caller must explicitly
  confirm selection; a missing/forged/partial annotation refuses.
- A standalone no-follow, regular-file, bounded source builder captures the
  adapter, canonical method, frozen normalization/corpus foundations and their
  applicable LICENSE/NOTICE/Unicode license before publication. It produces a
  hash-addressed HP-uncertainty-only payload and manifest. It imports/executes no
  captured source while building. It does not depend on NF, MT or numeric HP.
- A new lazy local error boundary and component expose a textarea, explicit
  whole-passage checkbox, Run/Cancel/Clear, brief result and opt-in private details.
  Existing styles/native controls are reused. Input is retained intact and
  rejected when oversized; no HTML maxlength silently truncates it.
- Every explicit Run starts a fresh bounded browser worker using the existing
  self-hosted Pyodide runtime. Source/runtime bytes are fetched, never input.
  A raw UTF8 and frozen-NFC identity, annotation, exact method/source identity and
  complete canonical record bind the result. Closed main-thread validation
  independently reconstructs the bounded literal hedge/calendar rows; changed,
  omitted, forged or unknown fields refuse before rendering.
- Input/selection edits, Clear, cancellation and unmount invalidate pending work
  and terminate its worker. Missing optional imports/payloads/errors are confined
  to this preview. The existing numeric HP, PS and MT checks retain operation.
  No account, endpoint, upload, persistence, telemetry or default export is added.

## Unicode risk and explicit device boundary

Python's Unicode-aware IGNORECASE/word-boundary behavior is not a stable JavaScript
Unicode-equivalence guarantee. This versioned device profile therefore refuses
potential hedge or calendar candidates touching non-ASCII letter/boundary cases
that its exact replay cannot interpret safely. Known Unicode whitespace and a
small declared set of nonword punctuation (including curly quotes) remain usable;
Unicode elsewhere is preserved and affects codepoint positions normally. The
Python canonical method is unchanged and its unrestricted CLI remains separate.
Unsupported boundary cases are Unavailable, never a completed zero finding.

No negation meaning is inferred: `not likely` retains a lexical word. `May 12`
receives only the canonical calendar exclusion, which is not calendar validation.
Quotes, writer intent, semantic uncertainty, unsupported vocabulary and context
adequacy remain unresolved.

## Resource/privacy gates and executed evidence

Inputs: at most 8,000 original and normalized codepoints and 32,000 UTF8 bytes;
no clipping. Output: at most 262,144 bytes, closed arrays/counts/spans. Load deadline
45 seconds; check deadline 6 seconds; one result per worker; cleanup failure
refuses rather than returning a claimed result. Details contain only canonical
positions and linkable identities, not original text; no automatic storage/export.
Application clearing is not forensic memory erasure.

Focused Python and Node controls must prove canonical full-record agreement,
explicit annotation/raw-NFC/source binding, supported/no-word/calendar/negation
cases, ambiguous Unicode refusal, unknown private fields, forged/omitted spans,
input/record/resource bounds, stale/cancel/fault isolation and safe source capture.
Then a source-frozen standalone fixture must run Chromium and WebKit sequentially
with native complete-record parity, real UI/privacy/lifecycle/keyboard/reflow and
optional fault recovery followed by actual numeric HP/PS/MT checks. Keep first
failures immutable. A different reviewer and PM mounting/protected/publication
remain separate steps. No physical-phone or human screen-reader claim follows.

Only NEW hedge-specific files, fixtures/tests/docs and execution records are owned
by this lane. Shared main/HP slot/catalogue/build hooks/package/revalidation/scope,
state and changelog remain PM-owned until an explicit handoff.
