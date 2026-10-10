"""Render reviewable execution planning from the versioned scope-delivery source."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
plan=json.loads((ROOT/'docs/scope-delivery.json').read_text())
scope=json.loads((ROOT/'docs/master-scope.json').read_text())
progress=json.loads((ROOT/'docs/scope-progress.json').read_text()) if (ROOT/'docs/scope-progress.json').exists() else None
progress_by={x['id']:x for k in ['records','packages','subtasks'] for x in progress[k]} if progress else {}
def cell(text): return ('; '.join(map(str,text)) if isinstance(text,list) else str(text)).replace('|',r'\|').replace('\n',' ')
def link(path, prefix=''):return f'[{path}]({prefix}{path})'
intro='''# AI TRUST ID — scope delivery plan

Revision 1 · 2026-10-08 · execution planning, not a release claim.

**The product is the complete tag system.** Different tags examine different
properties, use the appropriate sources/tools/engineering and produce distinct
findings. Several tags can describe one output. Shared capabilities support those
jobs; they do not collapse the product into one detector or one trust score.
Personal, team, enterprise and proprietary workflows remain in scope, together
with six subject families, authorship receipts, public participation and consented
research for improvement. PS is the first implementation, not a dependency of NF,
FI, MT, provenance or other tags.

This plan covers all **202 preserved records**, **39 work packages** and **117
package subtasks**. Every original ID also has a task in the [record index](scope-task-index.md).
The [machine plan](scope-delivery.json) and [master scope](master-scope.json) preserve
traceability. Planning coverage does not imply implementation coverage. Current
executed truth remains in `../state.json` and versioned `../runs/` evidence.

## Current timestamped completion

Read the [completion ledger](scope-progress.md) for each requirement, package and
subtask: percentage, timestamp, execution credit, evidence and next fix. 100%
means the full named item functions and meets its acceptance; independent tag
validation is not inferred from component tests. Completed records leave the open
queue but stay in scope. Milestone percentages are not effort or accuracy.

## Three layers and their value

1. **Tags and evidence:** reference support/contradiction, hallucination indicators,
   manipulation, scam/risk, independent review, contribution provenance, uncertainty,
   personal-information controls, optional receipts and six subject families.
2. **Shared capabilities:** stable protocol, evidence binding, privacy, capture,
   small accessible multi-tag presentation, evaluation, correction and release.
3. **Delivery and operation:** phone/native/offline/browser/local workflows, public
   reporting/contribution/teamwork, secure research and recovery, organization
   services, and a separately established governance/conformance program.

## Who owns what

| Role | Accountable outcome | Boundary |
|---|---|---|
| Michael | Product acceptance, scope changes, enabled service and release decisions | Decisions are recorded; no agent adopts proposals on his behalf. |
| Codex | Architecture, implementation, reproducible engineering checks and state updates | Holds the implementation pen; no verification from reading code alone. |
| Claude | Claim wording, evidence/labeling review and gaps | Review-only during this implementation pass; changes require a coordinated handoff. |
| Independent human reviewers | Blind labels, adjudication and real usability/accessibility judgment | Roles remain unfilled until someone accepts; agents do not count as independent labelers. |
| Qualified security/legal specialists | Reviews requiring their expertise and professional responsibility | No invented reviewer assignment, legal clearance or security certification. |

## Dependency and failure rules

A prerequisite names the **capability needed for the selected claim and route**,
not completion of every feature in that work package. NF/FI need the selected
corpus attachment/retrieval capability; they do not require image/audio/video
support or each other’s conclusions. The shared validation machinery need not
validate every tag before one tag releases. A route uses only its accepted schema,
privacy and evidence primitives. There is no hidden all-tags gate.

Optional services, website availability, enterprise enrollment, research collection
and other detectors must not block a personal tag. Some dependencies are real:
a local-service route must stop if its required redaction fails; a provenance
finding cannot survive invalid required evidence; an unavailable browser runtime
cannot truthfully produce a result. Expose affected failure, preserve independent
findings, and use another route only when that route meets its own requirements.
No bypass or impossible guarantee of zero shared infrastructure failures.

For each signal, record source identity, observation window, subject version,
method version and dependence on other evidence. Several detectors consuming the
same source are not several independent confirmations. Distinguish record
integrity, reproducibility, source diversity and independently judged correctness.
Their roles can complement each other without being counted interchangeably.

## Delivery order and sprint discipline

**Stream 1 — earn the first PS release.** Existing 86 development examples and
browser checks are regression evidence. Complete the accepted sampling/labeling
protocol, new frozen holdout, two blind human reviews, adjudication and declared
statistical run. Candidate 95% Wilson lower bounds remain precision 0.93 and
recall 0.75; they must be agreed before the holdout run. Zero denominator or absent
required evidence cannot pass. Do not retune on the holdout. If it fails, retain
the honest preview, record the failure and open a scoped correction iteration.
Human install/use/removal, screen-reader and actual-phone evidence completes the
selected delivery route. Broader risk enhancements earn additional gates.

**Stream 2 — finish the PII_REDACTED procedure and recognition evidence.** Its
existing ordering/category/count checks are distinct from recognizer coverage.
Plan its own supported entities/languages, misses, false-redaction and accessibility
checks; PS thresholds are not borrowed. It can progress while PS human review is
pending. The on-device PS checker does not claim PII redaction.

**Stream 3 — prepare reference and further tag work.** Specify the shared local
corpus primitive, NF and FI claim units and evidence first; then implement one
selected tag at a time. Prepare MT/HP/provenance/IV/receipt contracts and datasets
without silently issuing them. UC/SC/BT stay proposals until their decisions.

**Stream 4 — independent delivery and operations.** Complete physical phone
checks, optional native Share routes, recovery/security gaps and public workflow
improvements. Build community and research applications only after their own
auth/consent/moderation/retention/recovery gates. Organization offerings do not
block personal releases and do not lower public standards.

Work in short, reviewable increments: contract/evidence design → implementation
and development checks → independent validation → complete selected user route →
release evidence → maintenance/revalidation. WIP is one detector implementation
and one independent review stream; unrelated support work may proceed with clear
file ownership. A sprint closes with a demonstrated outcome, not a document count.
A tag can need several sprints; a week is not an accuracy guarantee.

## First sprint: concrete exit evidence

| Task | Owner | Exit evidence |
|---|---|---|
| Accept PS sampling/ground-truth protocol before assembling or evaluating holdout | Michael; Claude reviews; Codex checks executable compatibility | Dated protocol/method/gate identities and sampling coverage; open disagreements stated. |
| Recruit/brief two blind reviewers and arrange independent sample preparation | Michael; human coordinator/reviewers | Accepted roles, labeling guide, separate frozen packets; no predictions exposed. |
| Run a small labeling pilot, outside the final holdout | Human reviewers; Codex checks packet tooling | Time per item, unclear cases and guideline revision; pilot never counted as final holdout. |
| Finish PII coverage experiment design and regression gaps | Codex; Claude reviews claim | Entity/language/error taxonomy and executable cases; no coverage percentage invented. |
| Execute physical phone and screen-reader checks with willing users | Human testers; Codex prepares scripts | Named route/device/browser/version, task completion, failures and fixes; emulation kept separate. |
| Record results and choose the next bounded implementation | Codex; Michael accepts | Updated state/evidence, explicit remaining gate and next task. |

These tasks have no promised completion date before reviewer availability and
labeling time are known. The pilot determines workload; sample size follows the
accepted design/interval and observed denominator, not a magic fixed count.

## Release and regression definition

Done means the specific job and supported scope are accepted; dependencies are
explicit; code/route works; required independent evidence meets the pre-agreed
gate; explanation, download/use and accessibility are tested; privacy/security
and correction behavior are demonstrated; a versioned evidence packet identifies
source, method, corpus, route and limitations. Unperformed checks stay pending.
No universal numeric gate applies across deterministic, semantic, procedural,
provenance and human-attestation tags. Future evidence can narrow an affected
claim or trigger correction without silently changing old records or other tags.

## Costs and access

Complete personal methods, evidence, verification and corpus attachment remain
free/open under the actual licenses. Fleet, host management, audit retention,
SSO, staffed support and organization-specific policy services may be separately
paid. They must have distinct contracts, security/validation scope and an actual
provider before accepting orders. No price, subscription, new purchase, closed
mandatory personal dependency or paid inference gate is adopted by this plan.
Organization-specific policy never redefines a public tag code.

## Decisions that block only their own scope

- UC/SC/BT registration and any PS rename: owner/RFC decision.
- PS holdout protocol: acceptance before independent execution, with two human reviewers.
- Real research intake: specific collection/consent/retention/deletion rules and recovery evidence.
- Self-hosted public community: moderator assignment, posting/appeal policy and application security.
- Institution/mark/certification/paid offers: owner and qualified professional review of their own gates.

Other planning, regression fixes, accessibility and unaffected tag work can proceed.

## Work packages

Each package below includes its own job, outcome, scoped prerequisites, tasks,
acceptance, failure boundary, access and existing source/evidence references.
References are not claims that the entire package is done.

'''
text=intro+'| Package | Job / service |\n|---|---|\n'+''.join('| ['+pkg['id']+'](#'+pkg['id'].lower()+') | '+pkg['name']+' |\n' for pkg in plan['packages'])+'\n'
for pkg in plan['packages']:
 text+=f"### {pkg['id']}\n\n**{pkg['name']}**\n\n**Job:** {pkg['job']}\n\n**Outcome:** {pkg['outcome']}\n\n"
 if pkg['id'] in progress_by:
  audit=progress_by[pkg['id']];text+='**Completion:** '+str(audit['percent_complete'])+'% · audited '+audit['audited_at']+' · checked by '+audit['checked_by']+'. [Evidence and next fix](scope-progress.md).\n\n'
 if pkg['id'].startswith('TAG-'):
  text+='**Input:** '+cell(pkg['inputs'])+'\n\n**Output:** '+cell(pkg['outputs'])+'\n\n**Claim boundaries:** '+cell(pkg['claim_boundaries'])+'\n\n'
 text+='**Scope records:** '+', '.join(pkg['scope_ids'])+'.\n\n'
 text+='**Scoped prerequisites:** '+(', '.join(pkg['dependencies']) if pkg['dependencies'] else 'No detector prerequisite; define/test this capability independently')+'.\n\n'
 text+='**Owners:** Codex implements; Claude reviews claims; Michael accepts; independent human/professional judgment is obtained where required.\n\n'
 for task in pkg['subtasks']:text+=f"- **{task['id']}:** {task['job']}\n"
 text+='\n**Acceptance:**\n\n'+''.join('- '+gate+'\n' for gate in pkg['acceptance'])
 text+='\n**Failure containment:** '+pkg['failure_containment']+'\n\n**Access/cost:** '+pkg['pricing']+'\n\n'
 if pkg['decision']:text+='**Decision gate:** '+pkg['decision']+'\n\n'
 if pkg['references']:text+='**Existing references:** '+', '.join(link(path,'../') for path in pkg['references'])+'. '+pkg['evidence_note']+'\n\n'
 if pkg['id'].startswith('TAG-'):text+='**Tag contract:** '+link(pkg['contract'],'../')+'.\n\n'
(ROOT/'docs/scope-delivery.md').write_text(text)
index='# Scope task index\n\nAll 202 source IDs remain covered. This is a crosswalk into the [one execution plan](scope-delivery.md), not a second roadmap. Package subtasks and gates supply the delivery criteria. Legacy grouping rows are traceability records, not extra detector implementations.\n\n| Record/task | Preserved requirement | Work packages | Completion at latest audit |\n|---|---|---|---|\n'
for row in plan['records']:index+='| '+cell(row['task_id'])+' | '+cell(row.get('display_title',row['title']))+' | '+', '.join(f"[{id}](scope-delivery.md#{id.lower()})" for id in row['work_packages'])+' | '+str(progress_by.get(row['scope_id'],{}).get('percent_complete','unassessed'))+'% · [evidence/fix](scope-progress.md) |\n'
(ROOT/'docs/scope-task-index.md').write_text(index)
# Render master table after enriching dependency mappings.
master='# Three-layer master scope\n\nAll 202 records and their dispositions remain preserved. UC, SC and BT remain proposals; no rename or new release is implied. Jobs/outcomes define scope, not implementation. Read the [execution plan](scope-delivery.md) and [task index](scope-task-index.md) for accountable work packages. `state.json` and `runs/` hold executed truth.\n\n| ID | Layer | Baseline job | Outcome | Work package |\n|---|---|---|---|---|\n'
for row in scope['records']:master+='| '+' | '.join(map(cell,[row['id'],row['layer'],row['baseline_job'],row['outcome'],', '.join(row['delivery']['work_packages'])]))+' |\n'
(ROOT/'docs/master-scope.md').write_text(master)
for pkg in plan['packages']:
 if not pkg['id'].startswith('TAG-') or pkg['id'] in ['TAG-PS','TAG-PII_REDACTED']:continue
 doc=f"# {pkg['id'][4:]}-01 — {pkg['name']}\n\nPlanning contract · 2026-10-08. No new runtime support, registration or release is asserted.\n\n"
 if pkg['decision']:doc+='**Decision gate:** '+pkg['decision']+'\n\n'
 doc+='## Baseline job and outcome\n\n'+pkg['job']+'\n\n'+pkg['outcome']+'\n\n## Inputs, outputs and boundaries\n\n**Inputs:** '+cell(pkg['inputs'])+'\n\n**Outputs:** '+cell(pkg['outputs'])+'\n\n**Limits:** '+cell(pkg['claim_boundaries'])+'\n\n## Method and evidence development\n\n'+''.join('- '+step+'\n' for step in pkg['tasks'])
 doc+='\n## Acceptance and error boundaries\n\n'+''.join('- '+gate+'\n' for gate in pkg['acceptance'])
 doc+='\nNumeric thresholds, supported languages/subjects and hardware/latency requirements are defined and accepted for this claim before independent evaluation; no PS threshold is borrowed by default. Existing editorial floors are not measured accuracy.\n\n## Prerequisites and failure\n\n'+', '.join(pkg['dependencies'])+' supply only the necessary primitives for this selected claim/route, not completion of unrelated tags.\n\n'+pkg['failure_containment']
 doc+='\n\n## Delivery, owners and maintenance\n\nChoose the supported personal route explicitly. Small code-only tags coexist; in-use explanation stays brief. The site carries method, input/output, privacy, limitations, tests, use/download instructions and evidence. Supported route installation/removal and human accessibility checks are part of release.\n\nCodex implements and records execution; Claude reviews claim/evidence design; Michael accepts scope/release; independent reviewers provide required ground truth or attestation. Reviewer assignments are not presumed. Personal capabilities stay free; organization administration is separate. Revalidate affected methods when sources, capture, parser, model, corpus or claim versions change. Corrections preserve old record identity.\n\n'
 doc+=f"Full work package: [{pkg['id']}](../scope-delivery.md#{pkg['id'].lower()}). Records: "+', '.join(pkg['scope_ids'])+'.\n'
 (ROOT/pkg['contract']).write_text(doc)
print(f'Rendered one plan, 202-record crosswalk and 12 additional tag planning contracts from {len(plan["packages"])} packages.')
