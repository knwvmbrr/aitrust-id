# Bracketed email: development result

The source candidate now masks `pilot [at] example [dot] org` as one complete
email span. In the existing challenge, all 28 original characters are masked;
the surrounding text stays intact. This is a measured development improvement,
not a tag release or a claim that every private detail will be found.

The matcher requires both explicit ASCII bracket markers in one bounded address.
It asks the same offline upstream email recognizer to accept the complete
projected address, then masks the original span. It does not rewrite input for
other recognizers, disable a category, change a score threshold, use DNS or depend
on PS. Ordinary email and the existing invisible-separator behavior remain.

## What actually ran

The genuine source-current baseline reproduced the unmasked challenge before the
candidate was tested. Both used the same installed Linux image/model, with one
explicit read-only public source-file overlay. The installed base image itself
contains older code; it was never presented as the current service. Each run
verified all five source identities and the sealed model's 29 assets before NLP.

The changed candidate produced these measured results:

- Executed all 42 retained examples; the bracketed challenge is fixed and
  the other 41 observations match the fresh baseline.
- All six unchanged compact-address examples, including complete masking and
  zero extra characters. The comparison reference is explicitly historical
  November 12 same-model evidence, not a new compact baseline run.
- Fourteen actual in-process HTTP/ASGI controls: complete original-offset masking,
  multiple addresses, benign/invalid-suffix controls, exact identity/entity counts,
  private response headers and content-free malformed/oversized-request failures.
- Fifty-nine model-free adapter/mock contract checks, recorded separately.

Each owned test container, public source file and private nonce folder was
removed. Its source inode/hash stayed unchanged; the pre-existing staging
service metadata stayed unchanged. No service was rebuilt or replaced. No local
Docker, model/dependency installation, new endpoint or real user data was used.

## Limits and next delivery

The fixed cases are developer-authored synthetic regressions. Existing English
false masking remains six characters across two examples; the Spanish challenge
still has eight extra masked characters. Other obfuscations/languages, independent
representative recognition and human acceptance remain open. F-023 and T-PII stay
at their existing 80% scope-completion status; this is not an accuracy score.

This result is an isolated engine plus in-process ASGI result. It does not update
an installed redactor, the website's selected chart/method, the gateway/replay
chain or the phone PS preview. Integration must select the new source identity
and separately qualify the rebuilt service route before describing it as served.
The on-device PS checker does not gain PII redaction from this change.

The earlier no-start guard failure, stale-model refusal and old-image source
refusal remain preserved. The authored execution record was captured before
ROOT's different actual review; that completed review is recorded separately.

[Architecture](pii-bracket-address-plan.md) ·
[Actual source-bound execution](../runs/2026-11-25-pii-bracket-address-development.json) ·
[Different source and actual review](../runs/2026-11-25-pii-bracket-address-review.json)
