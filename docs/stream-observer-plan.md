# Bounded optional stream observer — architecture before refactor

F-030 remains open. The installed extension uses the explicit ChatGPT DOM adapter,
not MAIN-world fetch capture. Replace the unused unsafe prototype with a complete,
inert developer module: no automatic fetch patch, permissions, capture, network or
MAIN-world registration. It takes a caller-supplied Response in an explicit test
or integration and a caller-supplied event callback. This is an engineering
component for future supported-adapter integration, not a vendor adapter or label.

Preserve the original Response object/status/headers/URL and return it immediately;
observe a clone only for an allowed event-stream response. Bound observer bytes,
chunks, decoded event line/buffer size, JSON/event count and deadline. Never parse
or read a request body. Decode strict UTF-8 and a narrow explicit assistant-text
SSE profile; never forward raw stream bodies, URLs or error messages. Unknown
schemas, invalid role/status/IDs, oversize input, timeout and cancellation produce
constant unavailable results and discard partial text. A page can forge its own
responses, so this cannot establish authentic model origin.

Clone/tee backpressure is not zero effect on the host; the browser controls chunk
allocation before observer bounds apply. Do not claim hard browser memory limits,
physical stream cancellation, a working vendor contract or transparent interception.
On completion/refusal, request clone cancellation without waiting for the page's
branch; remove timers and release locks when legal. Stale generations remain an
integration responsibility. A caller cancel function must stop results and clear
buffers, even if the body reader cannot be physically terminated. No assertion,
account, token, telemetry or deployment route is added.

Run real Response/ReadableStream controls for response identity and original-body
consumption, supported assistant fields only, user-message refusal, malformed
JSON/UTF-8 and resource limits, reader failure, timeout/cancel and no callback after
cancel. Prove the manifest is still DOM-only and cannot import/run this module.
Actual current vendor capture and human workflow acceptance remain separate.

## Implemented boundary

The module exports `observeAssistantStream(response, limits)`. The returned object
contains the unchanged original response, a completion promise and a cancel
function. Only a complete `aitrust.assistant-text.v1` synthetic stream can return
text. Every event has exactly `profile`, `message_id`, `role`, `delta` and `done`;
duplicate keys, changing identity and any non-assistant role are refused. There
is one data line per event; comments and CRLF are supported. This is our explicit
test profile, not a claimed current vendor format. Failure returns only a fixed
status/reason, never partial text, URLs or exception messages.

Default ceilings: 65,536 bytes, 512 chunks, 8,192 characters per line, 128 events,
8,000 UTF-16 code units of output and two seconds. Callers can lower these bounds,
not increase them. The deadline can settle even when the upstream body is stalled.
Successful completion requires the final `done` event and clean end of stream.
Cancelling a clone is requested without waiting for the page branch; no physical
erasure or browser memory ceiling is claimed. The caller owns any successful text.

The former `tap.js` automatically replaced fetch, accumulated a complete stream
and broadcast its raw body. It was never registered by the installed manifest;
its historical source remains in Git history. It is removed from the current
checkout. The new component imports nothing and does not install itself, observe
requests, select vendor URLs, write storage or issue assertions. No F-030
completion percentage or release claim is increased by this component.

Run `node --test tests/stream-observer.cjs`. CI executes these controls on Node 24;
the Python regression wrapper executes the same real web-stream controls with an
explicit TAP reporter. Full current-route and source-bound revalidation remain
required before publication. Physical devices and live vendor behavior stay open.
