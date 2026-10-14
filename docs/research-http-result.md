# Research transport — executed development result

Codex, 2026-10-14. The approved feedback path now has an independent ASGI
transport and a real HTTP → isolated worker → PostgreSQL development check.
The ordinary application remains disabled before reading request content.
No public listener, participant record, production database or browser upload
was enabled, and no tag method or allowlist changed.

The selected local regression suite passed 235 tests. On Linux, 58 transport and
bounded-worker tests passed in a network namespace with only loopback enabled;
both external IPv4 and IPv6 connection attempts refused. Seven actual
HTTP/database control groups passed: invalid capability, valid submission and
identical retry, conflicting retry, private/malformed/oversize payloads, quota,
withdrawal/replay, and recovery. The listener stopped, the disposable database
was stopped and removed, and the owned staging source was removed. Exact selected
source hashes stayed unchanged through execution.

The tests distinguish a simulated backend boundary from the actual Linux
HTTP/database path. Body timeout, fragmentation, framing, header/Host/auth
refusal, saturation and canceled-handler capacity are ASGI controls. Existing
bounded-worker tests exercise real subprocess timeout/output limits. These
controls are not a claim of production DoS resistance or proof of proxy behavior.

N-011 remains 60%, F-141 remains open, and the full queue remains 78 open of 202.
Production authentication/grants, proxy/provider handling, active and backup
expiry, replacement-host recovery, current notice, owner operation and a real
consenting pilot still need their own evidence. No synthetic rating is a human
label, independent tag validation or permission to train a model.

[Linux execution](../runs/2026-10-14-research-http-current-linux.json) ·
[Guide](research-http.md) · [Architecture and risks](research-http-plan.md)

The added isolation check also runs the real standalone PS checker while both
research slots are occupied. PS still completes its independent check. Its first
test expectation used the wrong capitalization for the existing PS message; the
subprocess had succeeded. That failed test is retained in
[the refusal record](../runs/2026-10-14-research-http-test-expectation-refusal.json);
the corrected assertion and five private worker refusal controls pass.

The first protected CI run refused a command-wiring defect: the inserted step
interrupted an existing multiline block, so YAML folded a feedback verifier
command into pytest arguments. It was not merged. The repair restores the two
separate steps. Three consumer controls execute both actual parsed workflow
commands and confirm that the known folded command refuses.
[CI refusal](../runs/2026-10-14-research-http-ci-command-refusal.json).
