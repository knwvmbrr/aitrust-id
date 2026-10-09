# Provenance-to-tag boundary increment

Plan recorded 2026-10-09; Codex implementation/review, Claude initial bridge draft.
Scope: F-025, F-083, T-PA, T-FA, F-116, F-150. No taxonomy adoption or production
allowlist change. This is research input plumbing, not a media validator.

## Architecture and risks before refactoring

A valid credential establishes neither AI participation nor human editing.
The draft maps every fully valid credential to PA, including credentials for
ordinary human-created content. It also rolls up the first positive contribution,
which can conceal contradictions, accept malformed contribution objects and
combine subjects. Replace that implicit authorship inference with explicitly
scoped claim evidence, supplied by a future trusted adapter, and a matching
subject hash. Missing, invalid, revoked or unchecked evidence is neutral.

PA requires the explicit claim of AI generation followed by human rework; FA
requires the explicit claim of generation without human intervention. These
proposed adapter values must never be inferred from timing, credential validity,
absence of a watermark or missing human evidence. The bridge checks typed input,
subject binding, exact claim values, conservative conflict handling and source
identity. It does not verify a signature or prove the truth of a signed claim.
Research candidates always carry production_assertion=false and
independent_release_validated=false. No route to the gateway/extension is added.
Keep all evidence behind a contradiction, reject mixed subjects, deduplicate
repeated source evidence and never turn repetition into independent validation.

A clean checkout exposed a separate build-verifier defect: its expected manifest
was generated/ignored, so configured CI could not run without a prior build.
Use a committed engineering reference, verify actual builder output against it,
and regression-test a checkout with no runtime manifest. A deliberately altered
reference must fail, rather than be silently regenerated.

## Execution and exit checks

Preserve the original drafts outside the repository; repair in an isolated
worktree. Run adversarial typed/claim/hash/conflict tests, the full reviewed
Python suite and clean-checkout build matrix. Add a runnable synthetic demo with
no network or command execution. Scope evidence and timestamps are updated with
no acceptance inflation. Write changelog events before commit and push only the
reviewed files. Independent crypto/claim capture, provenance-policy acceptance,
real media, human review and tag release remain future acceptance gates.
