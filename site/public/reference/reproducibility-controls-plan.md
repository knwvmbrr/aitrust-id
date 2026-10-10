# Next execution: reproducibility and release controls

Preserve all 202 requirements, current unsigned 0.1 route, and separate tag
acceptance. Four independent contracts are being tightened:

1. Signal catalogue: retain every specified and historical ID, distinguish
   proposed, retired and current development/procedural methods, bind current
   methods to source, and provide an offline lookup and reproducibility check.
   A catalogue entry is not an independently measured conformance registration.
2. Revalidation: source/dependency/fixture/version fingerprints identify which
   current capability must be checked again after change. A stale report cannot
   become fresh by changing its date. This is not independent ground truth.
3. Accessibility release gate: preserve automated tests and require actual,
   current-source manual review before release. The current missing reviews must
   block the gate; test fixtures must never be accepted as real review evidence.
4. Decision ledger: seed and timestamp the 15 existing open decisions with reasons
   and owners, preserving accepted history and unresolved adoption. Recording a
   date is not inventing an acceptance or historical decision date. Correct
   categorical recommendations unsupported by evidence; no new legal opinion.

Risks: metadata can overstate a proposed detector; a fingerprint can identify bad
code without proving accuracy; self-declared review data can be forged; seeded
decisions can be mistaken for owner approvals. Mitigations are explicit states,
fail-closed identity/format checks, negative mutation tests, separate real-review
and engineering-fixture inputs, and public limits. A functioning gate can refuse
release. No operating institution, signed assertion, renamed tag or human tester
is created by this batch. Close only a full named mechanism after execution;
independent accuracy, outside-user acceptance, legal filings and actual manual
reviews remain assigned to their own open requirements.
