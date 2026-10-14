# Independent tags and the target of 45 open requirements

Owner direction, 2026-10-14. Implementation owner: Codex. Preserve all 202
requirements; 100% means the whole named job functions and has its required
acceptance evidence. The starting ledger has 124 complete and 78 open records.
The target is 45 open, requiring 33 genuine full closures. A failed or blocked
requirement does not stop work on another independent job.

## Architecture before changes

Each tag owns its input contract, method, version, result, validation, resource
budget and failure state. No tag consumes another tag's verdict as a prerequisite.
A shared protocol does not make accuracy transferable between tags. Unbuilt tags
remain unavailable. Future implementations must pass their own fault and recovery
checks before the catalogue describes them as operational.

The two current routes expose a concrete coupling: four waiting full-pipeline
requests exhaust the gateway's shared admission semaphore, including privacy-only
requests. Reserve three slots for full-pipeline work and one for privacy-only
work. Keep the total at four. Acquire/release the selected slot on success,
upstream failure, caller cancellation and disconnect. Reject excess work before
sending input upstream; never borrow the other route's reserved capacity.

Keep the existing /healthz endpoint's default complete-pipeline readiness
contract. Add a privacy selection on that same endpoint and to the existing
owner-run doctor command. The container probe uses privacy-route readiness so a
PS outage does not make the gateway unusable while its privacy route works.
Required redaction remains mandatory on all service routes. A failed redactor
must never cause raw input to be forwarded to the evaluator.

Add a standalone, process-isolated PS command using the existing exact frozen
on-device projection. It requires only Python, reads selected input, runs no
inspected command and calls neither gateway nor redactor. It is the independent
PS route when the local stack is unavailable. It explicitly reports no redaction,
no independent release validation and no safety clearance. Bound input to the
existing 20,000-character device contract, bound execution time, verify the
returned method/normalization identity, and suppress private text and exceptions
from ordinary output. Do not adopt a new production tag or invent an API endpoint.

Do not change the existing combined assertion into a partial-success envelope:
its schema and consumers currently promise a complete pipeline. Until a separate
versioned partial-result contract is accepted and implemented, combined failure
remains Unavailable; the independent selected routes remain usable.

## Risks and checks

A queue reservation protects admission, not an entire machine from compromise or
resource exhaustion. The shared redactor is a security prerequisite for service
processing; it is not the PS tag. The standalone route processes locally without
redaction and must say so. It must not silently replace a combined check or claim
PII results. Never reinterpret a timeout/crash as No finding.

Exercise both saturation directions, timeouts, malformed upstream output,
authentication, redactor failure, disconnects and recovery. Execute the standalone
CLI from a minimal isolated interpreter, compare it with every existing PS
regression fixture, and simulate its child timeout, crash and invalid result.
Refresh actual clean Linux setup, runtime receipts and source-bound performance
when their inputs change. Record authored software checks separately from actual
ML-service, human, independent accuracy and physical-device acceptance.

Record this direction and the current count in state and the change log. Keep
unperformed acceptance open; a stronger completed requirement may need reopening
until its new acceptance passes. A passing isolation component does not complete
all 14 tag packages or manufacture the 33 remaining closures.
