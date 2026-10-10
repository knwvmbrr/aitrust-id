# Open queue target: 100

The owner requested reducing 187 open requirements to 100: 87 full acceptance
closures, preserving all 202 records. Completion is recorded only for the full
named requirement. Independent human labels, real devices and owner/legal
acceptance cannot be substituted by generated tests.

## Architecture and first execution batch

Keep the public on-device checker and existing production PostgreSQL/backup/alert
services unchanged. Run the current three-service development pipeline in a
separate disposable staging project on the dedicated primary Linux host. Use
Podman, a daemonless open-source container engine, and a distinct compose project,
private synthetic token, loopback-only gateway and internal evaluation network.
No real user text, new public endpoint, research intake or local Docker launch.
The existing compose contract remains the installable reference implementation.

Before installation: check host capacity, existing engines, ports and database
health. Install distro-packaged Podman/compose tooling; do not replace the host
firewall, restart production PostgreSQL or bind a public port. Record actual
package versions. Build locked dependencies with hashes. Compare running source
hashes, execute positive/negative authenticated HTTP cases, dependency readiness,
redaction ordering, schema, bounded isolation, temporary storage and log canaries.
Stop/remove the staging project after evidence collection. Keep existing host
roles, backup schedules and service permissions intact.

Risks: container packages consume storage; image builds use CPU/RAM; container
network tooling can add firewall rules; the edge-attached gateway has potential
outbound access. Audit actual networking and preserve the published bounded
claim. If installation/build/isolation fails, stop, record the failure and fix its
cause before acceptance. Never treat configuration as executed evidence.

## Remaining batches

1. Service/privacy/runtime contracts and outside-implementer conformance runner.
2. Versioned protocol vocabulary, hash vectors and migration/result boundaries.
3. Safe local corpus/reference primitives, independently bounded new observations.
4. Optional receipt integrity/offline verification primitives and constraints.
5. Community correction/contribution and operational recovery workflows.
6. Re-audit each full named acceptance against current source; update the ledger,
   attribution, timestamp, remaining fix and state; publish verified increments.

These batches are execution priorities, not promised completion counts. A target
number is not permission to weaken acceptance or expand a policy into a runtime
claim. Existing previews remain previews until their own independent gates pass.

## Acceptance alignment audit

The initial ledger attached a full replacement-host recovery gate to F-150's
changelog/state/documentation job and attached whole-route release acceptance to
F-154's subject-definition job. Those are unrelated acceptance conditions, not
independent safety gates for these two named requirements. This increment verifies
their original baseline jobs with working mechanisms and failure tests. Full
recovery stays open under WP-OPERATIONS; outside interoperability stays open under
F-078/F-119; every tag's independent accuracy and human route gates stay open.
F-149 requires an actual named roster, not an operating staffed institution;
MAINTAINERS and its validated machine-readable lanes supply that narrow contract.

## Current service acceptance — executed

The dedicated staging pipeline passed 30 HTTP checks on context-v5: missing/wrong
credentials, hostile page origin, all five reserved non-text modalities plus an
unknown value, empty/oversized/wrong-type/extra-field requests, supported command
shapes and negative download/display/warning shapes, Unicode, actual detected
redaction, and both dependency stop/failure/restart cycles. Schema, source hashes,
redacted subject hash/length, bounded spans, non-root UID, read-only roots and zero
Linux capabilities were checked. Both stdout and stderr application logs exclude
the private staging token and synthetic content markers. Offline email recognition
works with new connection creation blocked.

Two bounded IPv4/IPv6 external TCP probes failed in all three containers under the
host's existing default-deny forward policy. The portable compose file's gateway
still has an edge network; this host observation is not a universal gateway-egress
guarantee. The anonymizer/evaluator additionally use only the internal network.
`C /etc` is the engine-generated mounted-file directory delta; unexpected
application filesystem changes are rejected. No physical-memory erasure, complete
PII coverage, independent accuracy, hardware latency SLA or human acceptance is
claimed. Resource saturation/cancellation remains a separate N-003 requirement.

This evidence completes the current named orchestration, redacted-input-only,
network topology, English-asset provisioning, dependency readiness/failure and
real-response schema/isolation checks. It does not complete the whole service
package, any detector's accuracy gate or every privacy route. The initial ledger's
shared cancellation/human-recognition gates are retained on N-003/T-PII instead
of being treated as dependencies of every unrelated service requirement.
