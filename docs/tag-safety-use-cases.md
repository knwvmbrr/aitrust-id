# Independent tag jobs: safety first

Each tag answers one stated question. Its result must identify the evidence,
method, supported format and limitation. A tag may use multiple tools or sources;
that does not automatically make their evidence independent. No tag requires
another tag’s success, availability or conclusion. Shared capture or transport
must preserve separate results and explicit per-tag failures.

The following is a scope contract, not an announcement that all tags operate.
Only PS and the optional local PII_REDACTED route are callable in the first AI-tool
adapter, and both retain their development-validation status. Existing code
adoption and migration decisions are preserved. The three device/agent profiles
below are proposed jobs rather than additions to the issued code enum.

## PS

**Question:** Does selected text contain a supported download-and-run or decoded-execution pattern?

**Required evidence:** The current identified text, frozen normalization, matched pattern and bounded use/mention handling.

**Useful outcome:** Show the observed command pattern and a short explanation.

**Cannot establish:** Safety, scam, malicious intent, AI origin, or completeness across all command syntax.

## PII_REDACTED

**Question:** Did the selected local privacy check detect and mask supported personal details?

**Required evidence:** The current local redactor/model identity and its actual redaction metadata.

**Useful outcome:** Report the performed masking and its limits; do not change the original input.

**Cannot establish:** Complete removal of private information, legal compliance or permission to share.

## PII_OUTBOUND

**Question:** Is a supported send action about to disclose detected personal information?

**Required evidence:** Authorized compose/send integration, the current draft revision and local detection evidence.

**Useful outcome:** Offer an explicit edit, cancel or proceed choice before the supported send.

**Cannot establish:** Visibility into unsupported apps, encrypted destinations, all private information or coercion outside the interface.

## NF

**Question:** Which specific claim is supported by an identified reference passage?

**Required evidence:** Claim unit, exact source/passage, source authority policy, freshness and evaluation method.

**Useful outcome:** Show bounded support for that claim and the reference used.

**Cannot establish:** Universal truth, source neutrality or support for claims not actually checked.

## FI

**Question:** Is an identified claim contradicted by a selected reference under the declared policy?

**Required evidence:** The exact claim, reference passage, supported contradiction method and contextual/temporal scope.

**Useful outcome:** Show the specific contradiction separately from a missing citation.

**Cannot establish:** An entire work or person is fabricated, deliberate deception, or absence of evidence as disproof.

## HP

**Question:** Which supported inconsistency or unsupported detail warrants another check?

**Required evidence:** Independently validated component observations tied to exact claim units and their uncertainty.

**Useful outcome:** Explain each supported indicator without substituting for the original evidence.

**Cannot establish:** A model is hallucinating merely because it is uncertain, no citation exists, or one component failed.

## MT

**Question:** Does the supported wording/context match a validated pressure or framing pattern?

**Required evidence:** Quoted context, use/mention discrimination, the separate tactic method and blinded contextual labels.

**Useful outcome:** Show the observed framing and limitations in plain language.

**Cannot establish:** Personal intent, ideology, dishonesty, or manipulation from urgency alone.

## IV

**Question:** Who independently reviewed this exact claim or artifact, against what evidence, and when?

**Required evidence:** Consenting identified reviewers, separate trust/independence policy, artifact binding, review scope and correction/withdrawal status.

**Useful outcome:** Expose the review and its evidence with current scope/status.

**Cannot establish:** Truth from signatures alone, independence from multiple keys alone, or accreditation without a real program.

## FA

**Question:** Is there positive, trusted generation evidence covering the entire defined artifact?

**Required evidence:** Authenticated generation events or supported manifest claims, complete covered ranges, signer policy and current status.

**Useful outcome:** Describe the declared/verified generation observation and coverage.

**Cannot establish:** Human absence, human identity, intent or truth from textual style or missing provenance.

## PA

**Question:** Which defined portions have positive evidence of AI contribution or editing?

**Required evidence:** Artifact-bound generation/edit events, covered ranges, source trust and explicit observation window.

**Useful outcome:** Show the documented contribution boundaries and unobserved portions.

**Cannot establish:** Complete authorship history, proportion from style alone, or AI origin outside observed ranges.

## UNK

**Question:** Was the check valid but unable to support a stronger conclusion?

**Required evidence:** An actual supported evaluation with explicit uncertainty and method/version.

**Useful outcome:** State what remains unknown. Preserve adopted compatibility until a successor is accepted.

**Cannot establish:** That no check ran; failures are UNAVAILABLE and unsupported inputs are UNSUPPORTED.

## UC

**Question:** Does a supported command exhibit the proposed unsafe-command observation?

**Required evidence:** Accepted migration/compatibility contract and its own command-pattern evidence.

**Useful outcome:** Explain the specific command observation under an adopted contract.

**Cannot establish:** Automatic adoption of the proposal, a scam, intent or the safety of unflagged commands.

## SC

**Question:** Does the current context match an independently validated scam-pattern combination?

**Required evidence:** Validated pressure/value-transfer/identity/channel-switch indicators, use/mention context and published category error policy.

**Useful outcome:** Show each supported indicator, hedged wording and a one-action dismissal.

**Cannot establish:** Fraud or malicious intent from one weak indicator or several correlated indicators alone.

## BT

**Question:** Is there positive evidence of automation in the declared interaction window?

**Required evidence:** Supported authenticated automation events or independently validated capture evidence.

**Useful outcome:** Report the observed automation and its boundaries.

**Cannot establish:** A person is a bot from writing style, speed, repetition, disability, language or missing human evidence.

## ROBOT_ACTION_PROFILE

**Question:** Did an observed robot action cross an explicitly configured physical-action boundary?

**Required evidence:** Authorized device telemetry, exact action/state/time window, units, device trust and versioned safety policy.

**Useful outcome:** Report the action, violated rule and policy version; separate missing telemetry from compliance.

**Cannot establish:** Malicious intent, physical safety certification, unobserved motion, or permission to control the robot.

## IOT_POLICY_PROFILE

**Question:** Does an observed or proposed IoT action violate this device operator’s explicit policy?

**Required evidence:** An identified device/action, authenticated interaction source where available, current permission/state constraints and policy version.

**Useful outcome:** Report the exact allowlist/permission/parameter/timing violation for operator review.

**Cannot establish:** That the actor is AI, hostile or a criminal; signed identity and policy violations have separate meanings.

## AGENT_INTERACTION_PROFILE

**Question:** What positive evidence identifies an autonomous agent’s interaction with this system?

**Required evidence:** Trust-scoped agent identity, signed action/event binding, observation provenance, freshness/replay and revocation handling.

**Useful outcome:** Describe the verified agent statement or recorded action and what remains unverified.

**Cannot establish:** Malicious intent, real-world identity or actual execution from an agent self-description alone.

## Security, legal, communication and propaganda applications

These are application domains, not a single universal truth or intent tag.
Security can combine explicit command findings, identity evidence and device-policy
violations while preserving each result. A legal workflow must retain claim-level
sources, jurisdiction/date and reviewer scope; a tag does not make a legal ruling.
Communication tools must distinguish quoted/reporting context from endorsement.
Propaganda-pattern work needs a public definition, representative contextual data,
false-positive analysis and independent review; a political opinion alone is not
evidence of deception or manipulation. Emergency or accessibility-related behavior
must not become a proxy accusation.

For robot and IoT operation, begin with read-only, owner-authorized events and
simulation. Specify units, clocks, missing/out-of-order events, stale permissions,
replay, device impersonation, update/rollback and safe degradation. A proposed
request and an observed physical execution are different records. Sending a
physical command, automatically blocking equipment or granting new device access
requires a separately authorized control boundary and device-specific acceptance.
The AI-tool adapter introduced here does none of those things.

No passive household surveillance, covert device enrollment, biometric inference,
automatic legal accusation or training use follows from these use cases. Keep
processing and operator data local/self-operated where selected, request only the
minimum evidence, and define retention and deletion before collection. Community
posting, research sharing and machine control each retain their own consent.

Every implemented profile needs its own reproducible acceptance cases, measurement
where inference is involved, known failure modes and deployment-level safety checks.
Policy violation is an observed mismatch with a rule, not proof of malicious intent.
The [machine-readable contract](tag-safety-use-cases.json) retains these boundaries.
