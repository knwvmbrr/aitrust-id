# Scope completion audit architecture — 2026-10-09

Keep the original 202 requirements, 39 packages and 117 subtasks intact. Add a
separate versioned execution ledger keyed to their IDs; do not overwrite historical
scope status or delete finished work. Generate a reader report with completed and
open queues, and link it from the plan. Each assessment records UTC audit time,
evidence time, implementation attribution (reported vs verified), checker, passed
milestones, unmet acceptance and a concrete next action/owner.

Percentages count five equal acceptance milestones: bounded contract, implemented
mechanism, executable positive/negative checks, complete selected integration, and
all required final acceptance evidence. They are milestone coverage, not effort,
accuracy, business maturity or an overall project completion estimate. The last
milestone is never credited from author tests when independent/human/security
judgment is required. 100% requires all five, no open acceptance requirement, a
completion timestamp and named implementer. Policy/refusal records are assessed
as their scoped controls, not runtime products. Legacy group rows aggregate their
children and cannot create additional completed functionality.

Risks: counting documents as functioning software; stale source/test evidence;
crediting simulated status codes as file verification; hiding unfinished work with
arbitrary percentages; copying child completion into a broad package; assigning
Claude or a human credit without evidence. Mitigate with explicit per-record
review, source hashes, immutable evidence references, structural verification,
bounded completed jobs, and separate package/subtask assessments. Never average
these overlapping records into one project percentage.

Review Claude's new pure adjudication/statistics modules separately. They must
fail closed on absent validation, unknown status codes, contradictory revocation,
unverified manifests/watermarks and malformed measurements. Do not connect them
to a production tag, adopt a new precedence policy, start Docker, or issue a C2PA
conformance claim. Add regression probes before counting repaired code as tested.
Research findings become attributed review material; unsupported universal or
legal conclusions do not become product claims. ACR, revocation and survival
work are enhancements of existing UX/integrity/integration/validation packages.
