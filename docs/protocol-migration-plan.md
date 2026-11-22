# Offline assertion compatibility: accepted plan before code

Technical acceptance: 2026-11-22T02:21:57.847306+00:00 by Codex PM under delegated engineering scope. This is not a Michael vote, taxonomy adoption or a production0.2 switch.

The current schema permits absent preprocessing identity; missing historical inputs cannot be reconstructed. Add a separate complete-identity0.2 offline schema and a bounded local converter. Keep existing0.1 production consumers unchanged. The exact two schema hashes, transform, refusal/loss table and full acceptance are in `protocol-migration-contract.json`, recorded before feature code.

Implement `protocol/migration.py`, a migration-owned private capture helper adapted from the audited no-follow primitive (no sibling tag import), an explicit CLI, published canonical vectors and an independent Node reference transformation for those vectors. No global refactor, new service or model.

Preserve every record field except the requested version. Require every identity default to have been explicitly serialized and verify self-consistency without normalization. Refuse any signature member and incomplete or unknown history. Default output is a brief non-content summary; explicit private export retains correlation metadata and requires careful sharing.

Risks: a migrated record might look newly verified; summaries must deny signature/accuracy/authenticity/re-evaluation. Changing a signed version invalidates its bytes, so refuse signed migration. JS numeric parsing loses precision/type, so the independent vector transformer edits only the top-level version string in trusted valid canonical vectors. Preserve old source files; output uncertainty must be explicit after publication faults. Foundation source/schema tampering and missing dependencies fail closed; never consult an external schema URI.

Full original closure requires actual end-to-end conversion/refusal, numeric-preserving roundtrip, independent implementation agreement, current consumer refusal/parity, private I/O faults, isolation and a distinct review. Until executed, N-001 remains open.
