# Certification programme: complete nonoperating reference design

Version 1.0.0. This is the delivered F145 programme **design and preparation
workflow**, not an operating institution, actual accreditation, a certification
mark licence, a legal opinion or a tag release. AI Trust ID remains the project;
the individual operator identified in Terms and Michael's accountable maintainer
role remain unchanged. Codex and other AI tools are contributors, not certifiers.
There are no appointed programme officers, accredited applicants or certificate
holders. A future institution/mark holder is unselected. This design does not
transfer assets, adopt a taxonomy or change public licences.

The [working guide](certification-programme-guide.md) consumes this design in an
offline application, assessment, separate decision review, appeal and correction
workflow. Its successful records concern **reference checklist completeness**.
All actual accreditation, certification, mark permission, authenticated role and
independent accuracy flags stay false. A complete reference application is not a
successful accreditation application to an operating body.

## 1. Purpose, claims and admission

An operating programme would assess a specifically identified implementation and
scope against an adopted, versioned standard. It must identify the standard,
implementation/version/configuration/source, tested platform, test dates,
excluded capabilities, evidence owners and precise claim. No generic “AI Trust
ID certified” or “safe/true” claim is permitted by this design. Do not infer
certification from a source signature, paid service, self-declaration or test pass.

The complete requirements matrix is
[`eval/certification-programme.json`](../eval/certification-programme.json).
The tool pins its exact bytes in independently selected source. An application
cannot choose a different policy or import an authority flag. Each of its ten
requirements needs attached named documentation: scope, competence, test plan,
evidence, impartiality, decision, appeals, surveillance, privacy and authority.
Empty/missing documentation is visible as incomplete. Text being present does
not establish that its assertions are truthful; an assessor must inspect it.

Participation must not depend on one vendor's detector or purchasing the
project's organization services. Alternative implementations can use the public
vectors and documented adapter contract. The current executable practice uses
the published reference implementation evidence; it cannot authenticate another
implementation or certify its completeness. A prospective independent
implementation needs its own exact executable/build/configuration evidence and
actual execution, assessed under the same adopted scope. Fees and an operating
licence, if any, need a future accepted decision; personal checking stays free.

## 2. Three separate test scopes

| Scope | What a certifier must examine | What the existing evidence does not establish |
| --- | --- | --- |
| Selected software interface | Identify the exact source/configuration and protocol version. Execute all14 public cases under both schema and extension profiles:28 outcomes, including expected invalid, unsupported and unavailable/failure states. Check case IDs, expected/observed state, process exits, output digests, source stability, privacy boundaries and missing tooling/refusals. Investigate deviations. | Full protocol correctness, implementation authenticity, independent accuracy, human accessibility, organization operation or accreditation. |
| Per-tag empirical validity | Before evaluation, record the adopted claim/subject/method mapping, independent label provenance, sampling and adjudication rules, untouched holdout, numeric/error budgets, calibration and uncertainty requirements. Execute that specific method on that accepted dataset, retain denominators, disagreements and failures, and compare appropriate baselines. | Author-authored fixtures, a raw research p-value, interface28/28, multiple keys, source signatures or one working example are not independent validation. Missing adoption or independent inputs blocks the accuracy claim. |
| Private organization policy/service | Identify actual custom scope/ownership/licensing, operator/tenant/job, authorization/export permissions and privacy/retention/removal/recovery constraints. Exercise supported and refused access, cross-tenant isolation, role removal, provider outages and independent personal operation. Inspect each claimed job separately. | A personal PS result, public reference source, protocol/vector pass or an invented organization does not certify a real service, employees, agreements, legal compliance or all organization jobs. |

The current checker admits only a **reference review** of complete selected
software-interface documentation/evidence. Tag-accuracy and organization-service
applications retain their additional unresolved requirements and cannot reach
completed reference review from interface evidence. This is an explicit boundary,
not a new numeric accuracy threshold or an assertion that those scopes were tested.
The full28-case reference evidence remains engineering evidence even when current.

## 3. Applicant and evidence responsibilities

The applicant supplies the exact scope, implementation source identity, platform
and limitations; document references for all requirements; and permission to
inspect the chosen evidence. An operating application must establish the right
to represent that implementation. Never infer organization ownership from an
email address, an opaque ID, a signature or possession of source code.

Test evidence must identify test profiles, exact current source/input/configuration
and outcome bytes, supported cases and failures. A fresh result is needed after
an applicable source/configuration change. Unknown, failed, incomplete or stale
required checks stay visible. Do not select only passing examples or silently
remove disagreements/unsupported categories from denominators. Protect private
references, customer data and credentials; prefer synthetic fixtures and minimal
metadata. Do not put private evidence into public issues or a default console log.

The offline tool reads no user-selected executable or URL. It validates the
existing source-bound conformance receipt with its existing canonical verifier,
including all28 expected case/profile outcomes. Hash equality binds bytes; it
**does not independently authenticate execution, authorship or factual claims**.
Documents and local role declarations remain operator-supplied observations.

## 4. How a certifier would qualify and be accredited

A future accreditation authority must first have documented lawful authority,
accepted governance/standards, accountable decision owners, scope and an actual
impartiality process. Qualified review and actual adoption remain prerequisites
for institutional conflict rules, asset transfers and certification-mark
ownership. [GOVERNANCE](../GOVERNANCE.md), [mark usage](mark-usage.md) and the
separate legal/formation decisions remain controlling. Nothing here adopts them.

For each proposed certifier and scope, require a documented competence dossier:
knowledge of the exact standard/test method, demonstrable technical skills,
relevant privacy/security capability, evidence handling, limitations and conflict
disclosures. The authority would verify identities/qualifications, assess a
witnessed exercise on supported and deliberately failed cases, review the
certifier's reports, and record deficiencies and corrections. Passing software
is not the same as demonstrating a person's competence.

An assessor recommends with scope-specific reasons. A separate authorized
impartial decision maker examines the evidence, corrections, conflicts and
limitations; accepts, narrows, defers or rejects the requested scope with written
reasons and an appeal route. An operating accreditation record would identify
authority, certifier, scope/version, conditions, issue/expiry dates, surveillance
schedule, decision and current status. No such record is issued by this software.
Accreditation never implies every detector/tag or every organization job is approved.

## 5. Impartiality and roles

The applicant, assessor, decision reviewer and appeal reviewer are separate roles.
Actual assignments must be accepted through the project's lawful process, not
invented by an AI tool or by filling a JSON field. In the local preparation
workflow they are distinct opaque **declared** IDs; one operator can invent all
four, so distinction of IDs is not evidence of real-person independence.

Declare financial, employment, ownership, relationship and other relevant
interests. Unknown/unfilled disclosure is unresolved. The existing project rule
requires maintainers with a commercial interest in an affected implementation
to recuse; see the [recusal workflow](conformance-recusal.md). An abstention does
not replace recusal. No new institutional rule is adopted here. Replace a
conflicted/unavailable assessor through a documented correction and restart
review. No one can change a role or scope and retain an earlier recommendation.
The software cannot detect undisclosed conflicts or appoint a replacement.

## 6. Consumed reference review process

1. **Application:** identify scope/implementation, documents, declared roles,
   conflicts, exact source-bound interface evidence and proposed reference-validity
   date. `start` saves a new private record. It reports missing requirements.
2. **Assessment:** an assessor acknowledges all ten requirements and records a
   recommendation, requested changes or recusal. Missing required evidence,
   unknown/conflicted roles, missing28th case or a different source prevents a
   recommendation. Reasons are retained privately, not printed.
3. **Separate decision review:** a different declared decision reviewer can mark
   the **reference review** complete only after recommendation and no unresolved
   requirements. Alternatively request changes or refuse. No certificate or
   actual accreditation is emitted. A final authorized operating decision would
   require separately established institution, actual accepted roles and authority.
4. **Correction:** the applicant supplies a replacement application and reason,
   retaining its ID. Every correction, source/scope/role change or renewal clears
   the prior recommendation/completion and requires assessment/decision again.
   A current unknown source cannot be silently substituted into old evidence.
5. **Contest/appeal:** the applicant records an objection; the state becomes
   `APPEAL_PENDING`, so an old completion is not presented as current. A separate
   declared appeal reviewer can uphold the prior reference result or remand for
   correction, with reasons and the complete requirement acknowledgment. They
   cannot invent an approval or bypass missing evidence/conflicts. Correction
   follows remand; the record of the objection is retained.

The record retains the initial application, ordered actions, current derived
state, missing requirements, exact programme/source identities and predecessor
byte digest. `inspect` replays the complete current method, not a saved state
label. This is a local audit trail, not a signature or append-only trusted ledger;
a source holder can rewrite the files. External parties must obtain trusted
originals and actual authority separately.

## 7. Surveillance, renewal and revalidation

The reference-validity date is at most365 days after assessment and is not an
accreditation period. Expiry withholds a current completed-reference-review claim.
A renewal changes the requested period but does not renew approval: assessment
and separate decision are required again. An operating authority would set a
scope-appropriate surveillance schedule, inspect complaints/material changes,
require corrective actions and record renewal/narrowing/suspension with reasons.
No universal surveillance period or guarantee is inferred from this example cap.

A material implementation, method, standard, policy, operating scope or source
change requires new applicable test evidence. If the programme/method itself
changes, old records refuse current inspection. `revalidate` creates a fresh
application with no inherited actions/approval, linking old bytes as historical
provenance only. It does not validate an unknown older method or transform its
approval. A current-source predecessor must replay exactly; its stored state
cannot bypass withdrawal. An older-source predecessor cannot establish terminal
state, so it requires a different application ID. Changes of claimed scope
require an explicit new scope assessment.

## 8. Suspension, withdrawal, correction and complaints

A declared decision reviewer can suspend a recommended/completed reference review;
completion is withheld until corrections and fresh reviews. The applicant can
withdraw; that record is terminal. A later submission after withdrawal requires
a different application ID and starts without approval. Under an operating
programme, withdrawal, expiry, suspension and revocation must change public status
and stop any authorized mark claim according to its actual licence. This design
cannot revoke or authorize rights it never granted.

Complaints must have a private safe channel, minimal records, a responsible
reviewer, reasons, a correction/appeal path and scope-limited containment. Keep
contested facts and unresolved evidence visible. Correct published mistakes with
versioned provenance; do not silently rewrite the historical decision or hide a
failed case. No automatic public registry or notification service is introduced.

## 9. Private records, publication and removal

Records contain document text, IDs, reasons and linkable source hashes. Use the
explicit owner-private0700 parent and0600 outputs outside Git; inspect before
sharing. No input text/path/hash is emitted by default console summaries. The
software uploads nothing and stores only the selected new files. The operator
chooses disclosure, actual lawful retention and access. A real institution would
need separately accepted permissions, retention, deletion, appeal access and
incident responsibility; this programme design is not their legal clearance.

Logical deletion of selected files removes the local records, not backups or
forensic remnants. No daemon is installed. Unsupported/malformed/stale input is
Unavailable, not a negative certification decision. A publication/close failure
may leave complete/partial output; inspect the exact destination before retrying.
A failed optional reference tool cannot change another checker or grant access.

## 10. Legal/adoption packet and completion boundary

Before any operation: obtain qualified review of the proposed authority,
certification/ordinary mark distinction, owner-use/competition restrictions,
licence, scope wording, appeals, impartiality, privacy and applicable agreements;
record actual owner/RFC/role decisions. Determine real institutions, personnel,
resources, fees/access and accountable operator. No agent assurance substitutes
for those decisions, and no filing or asset assignment is performed here.

F145's original outcome is a complete documented programme without implying an
operating institution. It requires the full design, usable consumed workflow,
supported/refused/correction/appeal evidence and distinct review before a
completion recommendation. F143, formation, actual role operation, independent
accuracy, mark rights and any wider governance package remain separate and open.
The delivery must remain described as this reference design after publication.
