# Ownership and dependency automation — actual acceptance

F-152 is complete. PR 3 merged through normal branch protection after all eleven
required engineering checks passed on both the push and pull request. GitHub
accepts the default-branch CODEOWNERS file with zero errors. All ten actual
Dependabot update jobs completed successfully on the merged source: two npm roots,
four Python roots, three Dockerfiles and GitHub Actions.

The first real update proposal is held by required checks, including its missing
change record. Auto-merge remains disabled. A proposal does not update deployed
software. Each installed dependency update still needs synchronized hashed locks,
current source-bound evidence, applicable runtime checks and a recorded review.

The review caught an implemented defect: changing requirements.txt could leave
requirements.lock unchanged. Shared controls now compare direct manifests and
service frozen inputs with installed hashed locks, including normalized package
names and the supported extra. All four real version-only changes are rejected.
96 targeted dependency and route checks pass; the complete Python suite previously
passed 1,037 checks on the repaired source. No lock or production image changed.

[Actual source checks, ownership acceptance, ten jobs and held proposal](../runs/2026-10-10-dependency-automation-hosted-acceptance.json).
[Earlier defect and local correction](../runs/2026-10-10-dependency-manifest-sync-review.json).
[Protected failing-PR control](../runs/2026-10-10-required-ci-failure-blocking.json).

**105 complete requirements, 97 open; all 202 scope IDs preserved.** This closes
repository engineering controls, not independent human review or tag accuracy.
The separate release gate remains unmet. Research intake is disabled; the first
pilot remains an optional metadata preview/download with no examples authorized.
Website publication of the updated ledger is verified separately after deployment.

## Publication verified

Reviewed source `a8919741319877e9bb619424222ece251f17e81d` is live. All 187
artifacts match at its Pages deployment, aitrustid.com and www (561 exact decoded
HTTP byte checks). All 20 live panels pass, with zero automated axe violations
and all 202 scope records preserved. Both source workflows passed all eleven
required engineering checks after the chronology correction; normal PR 11 merge
used no protection bypass. See `runs/2026-10-10-dependency-accepted-publication.json`
and `runs/2026-10-10-dependency-accepted-protected-source.json`. Later evidence
bookkeeping is not a new runtime deployment.
