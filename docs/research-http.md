# Check the optional feedback transport

This is a working developer test using invented feedback. It does not collect
people's data, enable uploads on the site, or require an account to check a tag.
Research runs separately from the tag gateway.

## Run it

On Linux, use an ordinary user with PostgreSQL 18 installed at
`/usr/lib/postgresql/18/bin`. Install the repository's existing pinned dependencies:

```sh
python -m pip install --require-hashes -r eval/requirements.lock -r services/gateway/requirements.lock
python -m pytest tests/test_research_http.py tests/test_worker_process.py -q
python scripts/metadata-store-sandbox.py --profile http --output output/verification/research-http.json
```

The last command creates a new private, socket-only database and an ephemeral
loopback HTTP listener, exercises the real request/worker/database path, then stops
both and removes the database. It publishes a receipt only after cleanup succeeds.
It does not connect to the production database or contact an outside service.
The server's fixed bearer values are public invented fixtures, not pilot credentials.

## What works in this development component

- Exact `POST /v1/feedback`; a canonical bearer header and exact loopback Host.
- Synthetic PS metadata only, with separate invitation and withdrawal capabilities.
- At most 4,096 input bytes, 64 body fragments, a two-second body deadline and two
  intake slots. Rejected framing, headers or authentication do not trigger a body read.
- A separate worker per admitted request, capped at 15 seconds and 2,048 output
  bytes. Content is passed through stdin, without a request file or command argument.
- Checked, fixed-shape output, no-store responses and no reflected error text.
- Idempotent retries, database quota enforcement and withdrawal without resurrection.
- Canceled handlers retain capacity until their already-started worker finishes.

The normal `services.research.app:app` entry point returns
`503 {"state":"Unavailable","collection_enabled":false}` before reading a body.
Environment variables cannot enable it. Only the verifier explicitly constructs
the separate synthetic instance. Do not expose the development verifier publicly.

## Before accepting real feedback

The [approved pilot contract](../deploy/research/metadata-pilot-policy.json) still
requires production authentication and grants, TLS/proxy/provider review, active
expiry, withdrawal and encrypted-backup expiry, replacement-host recovery, the
current privacy notice, and owner operation. This component does not satisfy those
gates or change the synthetic SQL permission into participant consent. It has no
browser CORS/upload integration, examples, model training or public aggregation.

The ASGI server and OS receive bytes before application rejection. The limits
demonstrate bounded application work; they do not prove complete network-level
DoS protection, OS erasure or protection from a compromised administrator.

[Architecture](research-http-plan.md) · [Execution result](research-http-result.md)
· [Existing admission component](research-admission.md)
