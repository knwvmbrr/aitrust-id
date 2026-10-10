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
