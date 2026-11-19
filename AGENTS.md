# AI Trust ID delivery instructions

Read `state.json`, `docs/session-delivery-plan.md`, its JSON board and the current
`docs/scope-progress.json` before choosing work. Preserve the owner's full scope,
tag independence, privacy decisions and all historical acceptance criteria.

## PM, task-list lead and tag workers

The PM owns shared integration, scope/state/changelog and publication. Assign a
task-list lead to review the open queue and finished evidence. Staff independent
tag workers in bounded waves, each with a concrete outcome, existing scope IDs,
owned files, isolated worktree and verification. Use the available agent capacity;
a logical tag queue is not a permanently running process. Share exact commits and
source-bound evidence at handoff. Follow `docs/agent-handoffs.md`.

At session start select at least one deliverable that can fully work without the
owner. Keep a full original requirement as the closure target. If it requires an
owner, independent human, outside operator, counsel or platform action, preserve
that gate and advance another authorized implementation. Do not repeatedly stop
after partial work or ask again for authorization already given.

The task-list lead must account for every finished item: outcome, actual worker,
different reviewer, completion timestamp, executed checks, exact evidence digest
and unresolved limits. Update the dated board at handoff and closeout; completed
agents are no longer active. The PM maintains the scope ledger and attributed
changelog. Run `python3 scripts/session-delivery.py`; use `--check-session` to
expose an unmet strict session goal rather than imply that it passed.

## Truthful completion

Only full functioning acceptance earns 100%. A passing test count, draft,
component preview or scoped task cannot close a broader tag requirement. Keep
finished deliverables and original requirement closures as separate counters.
Do not remove, weaken or silently reassign criteria to hit a numerical target.
Evidence hashes prove identity, not accuracy or professional approval.

Tags must not depend on another tag's result or availability. Use foundational
protocol/normalization helpers where appropriate; isolate optional checks, workers
and UI failures. A check that fails must say Unavailable, never zero findings or
safe. Never assert semantic truth or malicious intent from a literal observation.

## Verification and publication

Use focused controls while developing, then the required source-bound and
protected checks after sources freeze. Schedule heavy local browser/native jobs
sequentially. Preserve failed candidates; do not rerun unchanged failures without
diagnosis or claim a retry found a root cause. Check outstanding review findings
before final validation and merge.

Keep private examples, credentials, trust execution details and unrelated project
files outside public source and logs. Do not stage unrelated/untracked files.
Use normal branch pushes, never `--mirror`, and do not remove tooling refs or
perform destructive object cleanup during live agent work. Keep public run
records immutable and record fresh changes before build/deploy/commit.
