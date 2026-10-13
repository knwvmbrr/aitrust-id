# Check the commercial-interest recusal rule

Before counting a conformance ballot, check whether the voter is eligible under
GOVERNANCE.md. A maintainer with a declared commercial interest in an affected
implementation must choose **recuse**. An unrelated declared interest does not
block a vote. Abstaining does not replace a required recusal.

This offline tool enforces that project rule. It does not grant certification,
adopt an RFC, create a board or verify that disclosures describe reality. The
operator must separately accept the actual role assignments, disclosure register
and affected-implementation scope. A signer cannot authorize themselves by
supplying a different register.

1. Obtain the approved register and decision scope through your trusted project
   process. Record their SHA-256 hashes independently of the ballots. Keep private
   disclosures and keys out of public issues; the checker needs only opaque member
   and implementation IDs, role status and public verification keys.
2. A ballot uses `conformance-ballot/v1`, a new UUID, the exact register/decision
   hashes, key ID, UTC issue time and approve/reject/abstain/recuse choice. Its
   Ed25519 signature covers `AITrust-ID/conformance-vote/v1\n` followed by ASCII
   JSON with sorted keys, compact separators and all fields except `signature`.
   Public keys and signatures use unpadded canonical base64url. This tool never
   accepts or stores the private signing key.
3. Use the existing hash-locked verification environment described in README.md:

   ```sh
   python scripts/check-conformance-votes.py ballots.json \
     --roster roles.json --roster-sha256 YOUR_TRUSTED_64_HEX_HASH \
     --decision decision.json --decision-sha256 YOUR_TRUSTED_64_HEX_HASH
   ```

Exit 0 means every supplied ballot follows the rule; inspect `eligible_votes` and
`recorded_recusals` separately. Exit 1 blocks eligibility because a declared
conflict, unfilled/observer role or withheld disclosure requires action. Exit 2
means malformed, tampered, expired, oversized, linked, nonregular or unavailable
input/dependencies; no ballot is counted. Output omits names, financial detail,
file paths and private keys. No remote call, publication or input rewrite occurs.

The register is valid only within its declared UTC window, has at most 128 unique
members and one selected public key per member. The scope lists 1–32 distinct
affected implementations. The verifier accepts 1–128 signed ballots, at most one
per member; IDs, register/decision hashes and issue times must agree. Duplicate
JSON fields and nonfinite values are refused. There is no majority/quorum decision
or hidden inference that different keys mean different people.

For a safe demonstration, run:

```sh
python scripts/verify-conformance-votes.py --output output/verification/recusal.json
```

It creates fresh **invented** keys and ballots in an owned temporary directory,
executes 19 real CLI controls, removes the directory and writes a sanitized
source-bound receipt. It never assigns actual roles or asks anyone to vote.
Codex executed it on Mac Python 3.12.14 and Linux Python 3.13.5, plus 49 focused
policy/file/signature tests. See the [local](../runs/2026-10-13-conformance-recusal-local.json)
and [Linux](../runs/2026-10-13-conformance-recusal-linux.json) receipts.

F-147 covers the functioning rule. Actual RFC decisions, a formed institution,
certification, counsel's independence review and real role operation remain in
their separate requirements. Dishonest disclosure, a dishonest register issuer,
compromised trusted hashes or inaccurate system time cannot be fixed by signing
ballots; retain those limits when interpreting a successful check.
