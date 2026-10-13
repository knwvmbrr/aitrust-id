# Conformance recusal rule — architecture and acceptance

F-147's original job is the conflict-of-interest **rule**, with responsibilities
recorded without implying an operating institution. GOVERNANCE.md says:
“Maintainers with a commercial interest in an implementation must recuse themselves
from votes on conformance decisions affecting it.” The completion ledger instead
copied the whole RFC/board process onto this row. That creates an artificial
completion dependency: F-075/F-076/F-143/F-145/F-146 track the broader institutional
and operating outcomes and stay open. A functioning rule must not pretend that a
foundation, board, real role assignment or conformance program exists.

Implement an offline decision-policy checker. The operator independently selects
and pins a role register and decision scope by SHA-256. Voters cannot choose their
own roles, omit an affected implementation, narrow an interest disclosure or move
a signed ballot to another scope. The register declares accepted/unfilled roles,
public Ed25519 keys, complete/withheld disclosure and implementation IDs. It is an
operator-selected trust input, not proof those real-world disclosures are true.

Each signed ballot binds the register hash, decision hash, key ID, choice, UUID
and claimed UTC time under a separate signature domain. Verify exact fields,
canonical identifiers, finite bounded JSON, signature, role/disclosure, active
register dates and one ballot per registered member. Require explicit recusal for
an affected declared interest; an abstention cannot hide that obligation. Unknown
or unassigned roles and withheld disclosure never count as eligible votes.

Output only bounded policy outcomes and counts. No private key, participant name,
financial details, source text, remote service, endpoint, public message or actual
certification decision is created. Eligible means eligible **under the supplied
project rule**, not certified, independent, conflict-free in reality or adopted.

Acceptance: actual Mac and isolated Linux CLI execution must accept an authenticated
unconflicted eligible ballot and explicit recusal, and reject a conflicted approval,
conflicted abstention, scope/roster tampering, forged identity, missing disclosure,
unfilled/observer roles, expired registers, duplicate members, malformed/bounded
input and linked/nonregular files. Archive exact source-bound execution evidence.
The policy checker is the F-147 job; executing a real RFC/board remains F-076 and
the institutional records. Do not mark those complete from synthetic ballots.

Risks: a dishonest operator can provision a false register; undisclosed interests
cannot be discovered from signatures. Different keys do not prove different people.
Signed timestamps are statements, not independently trusted timestamps. This is
project-rule engineering, not a legal/tax independence opinion or counsel review.
