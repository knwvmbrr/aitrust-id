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

## Integrate and publish

Preserve child commits and both changelog entries. Resolve only understood merge
conflicts, reject remaining markers and run the real staged-index guard. Historical
evidence remains tied to its original commit; current changes still need fresh
matching records. Do not alter an old event to make integration pass.

Only count an original requirement complete after its full recorded acceptance
works and is evidenced. Keep blocked owner/external gates open and advance
another authorized job. Distinguish a completed lane, an integrated candidate,
protected CI, a merged source and exact verified public delivery. Report only the
state actually observed; do not describe a dormant agent as working after the
integration turn ends.
