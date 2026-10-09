# Security Policy

## Reporting

Use the repository's **Security → Report a vulnerability** control when enabled.
Do not post exploits, credentials, prompts, personal data or private AI outputs
in public issues. The owner created security@aitrustid.com; that particular inbox
has not been independently tested. No guaranteed response SLA is claimed.

## Scope, stated plainly

The on-device PS preview reads only pasted text in a browser worker, using a pinned
self-hosted runtime and source-bound method. It uploads no answer text, performs no
redaction and never executes or fetches the matched payload. Optional offline saving
caches public files only. Browser memory clearing is not physical memory erasure.

The separate Chrome adapter captures identified assistant responses on chatgpt.com. It
does not require reading the user's typed prompt. The local manual checker reads only
the text the person supplies. Both send text to an authenticated loopback gateway;
detected redaction precedes evaluation and can miss sensitive information.

* Evaluator/anonymizer use Docker's internal network, non-root execution and
  read-only roots. Bounded TCP probes failed; this is not universal proof against compromise.
* The gateway binds **127.0.0.1 only** and requires a per-install bearer token.
* Assertions contain a **content hash and character offsets, never text**.
* Build-time package/model downloads require network access and are hash-locked.
  The evaluator records its source hash: identity, not correctness or authenticity.
* Assertions are currently unsigned. No signed release, SBOM delivery or
  independent application security certification is claimed.

Hashes, offsets and redaction categories are metadata and deserve careful
disclosure. Default processing has no registry persistence or remote collection.
Do not expose the development gateway to the Internet or enable the optional
registry for research: it is an unconnected prototype, not a retention-enforced
service. See docs/development.md for the executed boundaries.

## Threat model

See THREAT_MODEL.md.
