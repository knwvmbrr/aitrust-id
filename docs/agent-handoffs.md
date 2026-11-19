# Agent delivery and review handoffs

Effective November 19, 2026. Michael owns product decisions and acceptance. Codex
is the integration lead for these implementation lanes; agents provide bounded
work and review evidence, not institutional or legal authority.

## Dispatch and ownership

Each assignment names its outcome, existing scope IDs, owned files, source base,
verification and exclusions. Work in an isolated branch/worktree. The integration
lead owns shared scope, state, catalogue, build hooks and production publication
unless a specific handoff transfers a named file. Never infer ownership from a
general instruction to keep working.

Check agent status when issuing follow-up work. In the current collaboration
tools, `send_message` delivers context but does not restart a completed agent.
Use `followup_task` to start its next task. A queued message is not evidence of
active work. Confirm the task is running or has returned its result before
reporting it as underway.

## Deliver a reviewable result

A lane returns its branch/worktree, full commit, exact owned files, executed
checks, immutable evidence paths and source hashes. Separate authored controls,
actual artifact execution, emulated browsers, physical devices and independent
human validation. Record failed candidates and fixes without rewriting prior
evidence. A passing test count is not a requirement closure.

Freeze sources before final review. Review findings name an actual failure or
reproduction, affected contract and next owner. Dispatch corrections explicitly
if the author has completed its turn. The reviewer does not edit the author's
files without a handoff. After correction, repeat the affected controls and
source-bound execution; review the corrected identity, not an earlier screenshot
or passing result.

Check outstanding repository review threads before freezing another integration
run and immediately before merging. Reproduce each applicable finding against
the current source. Green CI does not settle an unresolved counterexample.
Resolve a thread only after the corrected source is on the review branch and
the actual regression passes; an unpushed local fix is not that state.

## Integrate and publish

Preserve child commits and both changelog entries. Resolve only understood merge
conflicts, reject remaining markers and run the real staged-index guard. Historical
evidence remains tied to its original commit; current changes still need fresh
matching records. Do not alter an old event to make integration pass.

Finish public evidence writes and their fresh change records before starting the
website prebuild guard. Serialize a newly captured protocol receipt, its record,
then the website build; avoid producing uncovered run files during that guard.
Use checked sequential operations for dependencies so a failed preparation step
cannot launch a consumer against an incomplete snapshot. Reuse unchanged
capability evidence only when its exact source fingerprint still passes.

Only count an original requirement complete after its full recorded acceptance
works and is evidenced. Keep blocked owner/external gates open and advance
another authorized job. Distinguish a completed lane, an integrated candidate,
protected CI, a merged source and exact verified public delivery. Report only the
state actually observed; do not describe a dormant agent as working after the
integration turn ends.

## Task-list lead and session closeout

The PM dispatches implementation; the task-list lead owns the dated assignment
board in `docs/session-delivery.json` and its readable companion
`docs/session-delivery-plan.md`. Every tag has a named logical queue. A queue is
not a running agent: only active assignments name an actual worker. With three
specialist slots, staff bounded tag increments and review in waves rather than
claiming fourteen simultaneous processes.

Before implementation, choose an original requirement and write the full done
evidence for the next deliverable. Keep its historical job, outcome and acceptance
intact. If owner action or outside evidence blocks it, preserve that blocker and
dispatch the next authorized engineering task. A new component cannot be counted
as a full original tag release.

At closeout, require a different reviewer, a current passing execution record and
its exact digest. Run `python3 scripts/session-delivery.py` to inspect accounting.
Run it with `--check-session` for the strict session goal: at least one completed
named deliverable **and** one genuinely closed original requirement. Exit 1 means
the goal remains unmet; exit 2 means accounting itself is invalid or unavailable.
A successful inspection alone does not mean the session goal passed.

The task-list lead updates assignments and blockers after review. The PM updates
the scope ledger, state and attributed changelog before protected integration.
The board counts finished scoped tasks and original requirement closures
separately. Never lower acceptance, reuse an old passing report as new execution,
or describe completed agents as still running to satisfy the session goal.
