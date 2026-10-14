# Optional feedback transport — architecture before implementation

Codex, 2026-10-14. N-011 and F-141 remain open. Implement the already approved
`POST /v1/feedback` transport as a separate ASGI component; do not add a new
endpoint, attach it to a tag checker, deploy a public listener, or enable collection.
The default application returns Unavailable before reading a request body. No
environment variable can turn that default application into an intake service.

A separately constructed development instance admits invented requests only.
It requires a canonical 32-byte bearer capability, direct loopback transport,
exact Host, path and JSON framing, and the existing synthetic admission envelope.
No cookie, query token, CORS, redirect, forwarded-client trust, example, text,
identity, span, subject hash or client timestamp is accepted. Its fixed responses
contain no caller data. The response uses no-store, nosniff and connection-close;
access/error logging is disabled in the verifier's owned server.

Read at most 4,096 bytes within a whole-body deadline. Reject ambiguous framing,
unexpected headers and content encodings before reading. Reserve two independent
intake slots; an exhausted intake returns Busy without reading content. Move each
admitted request into a bounded, isolated process using the existing sandbox-only
admission command. The worker receives JSON on stdin, not an argument or file.
It uses the existing canonical token hashing, SQL allowlist, socket-only database
identity checks and synthetic NOLOGIN roles. Cap output while reading and kill
only the newly owned process group on timeout or excess output. Cancellation must
not refund a slot while database work is still running. A successful result must
match the operation and strict UUID/boolean output contract before returning it.

Verification must include actual loopback HTTP and PostgreSQL round trips,
withdrawal/retry/quota behavior, request refusal without body/backend access,
slow and oversize streams, saturation, worker failures and recovery, disconnects,
and fixed diagnostic/header behavior. Use only a newly owned private synthetic
database, shut it down and remove it after checking. Run positive controls on
Mac and Linux where applicable; source-bound receipts distinguish ASGI controls
from actual HTTP/database execution. Add protected CI coverage.

Risks and limits: the ASGI server and OS see incoming bytes before application
admission; no claim of network-level erasure or complete DoS protection. Loopback
is not authentication. Bearer values remain sensitive in process memory. A local
administrator can bypass the development isolation. This does not establish TLS,
proxy/provider handling, production database authentication/grants, participant
consent, backup expiry or replacement-host recovery. Do not reuse synthetic SQL
as a participant schema or silently change its `synthetic_test_only` permission.
The approved pilot stays disabled until its separate operational gates pass.
