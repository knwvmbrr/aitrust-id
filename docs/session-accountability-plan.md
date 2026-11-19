# Session delivery accounting

Owner direction, November 19, 2026: dedicated tag bots, a task-list lead and at
least one finished task per session, while moving 70 original open requirements
toward 60. Original requirements close only after their full acceptance works.

## Architecture before implementation

The task-list lead owns a dated assignment board. Tag workers own isolated tag
implementations; the integration lead owns scope, state and publication. All 14
tags retain a logical bot and queue. An assigned process is distinct from a
queued role; a saved board is not a running background agent or heartbeat.

Add a standard-library accounting tool that reads the immutable Git baseline,
the current scope ledger and the board. It must preserve the original 202 IDs,
independently calculate old/new completion, and report two separate results:
finished scoped deliverables and full original requirement closures. It does
not write the scope ledger, accept human/legal evidence or promote a tag.

The ordinary inspection command succeeds only when the accounting is internally
consistent. A separate session-goal check fails when the declared minimum
original closure has not happened. A structurally sound board with zero closures
must say **NOT MET**, even if useful component work finished. New task IDs,
passing test totals and an old 100% record cannot lower the original count.

Each closed task needs its declared outcome, distinct reviewer, timestamp and
hashed execution evidence. Original closures also need a reviewed recommendation
bound to the original job, outcome and acceptance; no erased or weakened
criterion earns credit. Evidence identity and counting are machine checked;
whether the work actually satisfies acceptance remains an explicit review job.

Inputs use bounded, duplicate-rejecting JSON and repository-local regular files;
Git baselines are full immutable commit IDs. No arbitrary command in the board is
executed. Reports contain project delivery information only. The existing public
report writer keeps committed run destinations immutable. No endpoint, data
collection, paid service, tag verdict or external communication is added.

## Risks and acceptance

- A stale board can invent activity: label all assignments as dated snapshots;
  require a worker only for active tag work, and update it at handoff/end.
- A task can masquerade as a requirement: derive original counts from the Git
  baseline and current ledger, preserving IDs, jobs and acceptance identities.
- A checkbox can masquerade as a working result: require current evidence hashes
  and an accountable distinct reviewer; disclose that accounting is not proof of
  functional, human, legal or independent-accuracy acceptance.
- A goal can encourage dishonest closure: expose an unmet original-closure goal
  as failure rather than weakening criteria or blocking unrelated tag work.
- An edited board can run commands or escape paths: treat it as data, bound
  inputs, reject unsafe paths/links and never execute its strings.

Verify unchanged 132/70 inspection, genuine witnessed transition accounting,
stale/duplicate/invented closure refusals, missing/tampered evidence, altered
acceptance, unsafe inputs and an actual CLI session-goal refusal. Continue work
on unblocked tag tasks when original acceptance requires another person.
