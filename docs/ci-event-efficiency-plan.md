# CI event efficiency — architecture and risk plan

Owner: Codex CI efficiency lane. Integration owner: Codex PM. 2026-11-16.
Base: `92364964334668ee0dad44c1b517a58d3a3ddcae`.

## Change boundary

A feature-branch update with an open pull request currently starts both `push`
and `pull_request` executions of the main CI workflow. The optional manifest
workflow also duplicates those executions when its existing path filters match.
Retain the complete checks on normal pull-request events and postmerge main
pushes, without launching the extra feature-branch push execution.

Change only the two workflows' event declarations:

- Main CI: unfiltered `pull_request`; `push` branches exactly `main`, plus all
  tags through the explicit `tags: ['**']` filter.
- Optional manifest inspection: the same branch/tag push policy, preserving
  both existing path lists exactly and preserving the PR path filter.

Every job, command, dependency, runner, permission, action pin and release gate
remains unchanged. Source provenance retains its existing push/main/repository
condition, so tag and PR events cannot gain signing authority. No new event,
endpoint, permission, cancellation policy or protection exception is introduced.

## Risks and intentional limits

A branch without a pull request no longer receives these two workflows' hosted
branch-push checks. Opening or updating its pull request remains the review path.
Tag-push execution is explicitly preserved; GitHub does not apply path filtering
to tag pushes. Existing optional-workflow path filtering remains in place. Main
CI receives no PR branch or path filter, avoiding newly skipped required checks.

Existing canceled or failed executions do not become successful through a source
change; normal hosted reruns and branch protection still apply. No merge-queue
support is claimed or introduced. The event change does not speed up a single
job or establish a measured reduction in total CI minutes. It removes one
redundant launch for the affected branch-update scenario. Accuracy, accessibility,
independent validation and all original scope completion counts remain unchanged.

## Verification before integration

Parse each old and new workflow with YAML's BaseLoader, compare every field other
than `on`, compare optional path lists exactly, verify the explicit main/tag push
policy and unfiltered main-CI PR policy, and record source hashes. Run only the
existing manifest input-coverage controls, source-signing authority control and
browser-runner trust control. Do not add tests that mirror the reversible YAML
change. No SDK, model, browser/native build or full test suite is needed here.
Hosted event acceptance remains pending until the integration PR and main push
execute normally. Integration owns the final current-source evidence runs.

## Official semantics reviewed

- [GitHub workflow syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax):
  branch and path filters combine; declaring branch filters alone would omit tag
  pushes, so tags must be preserved explicitly. Path filters do not apply to tags.
- [Required-check troubleshooting](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/troubleshooting-required-status-checks):
  required checks must satisfy the current commit; skipped workflows and stale
  successful checks do not establish current merge acceptance.

Rollback is the inverse event-only diff. Do not cancel or bypass required checks
as a rollback mechanism.

## Local result

The event-only change is implemented. Six existing workflow consumer controls
passed in 0.17 seconds. The retained execution record is
[`runs/2026-11-16-ci-event-efficiency.json`](../runs/2026-11-16-ci-event-efficiency.json).
It records both workflow hashes and parsed comparisons: all non-event fields are
identical, all 12 jobs remain, both optional path lists match their previous
values, and main/tag push execution is explicit. The first environment probe
found no pytest in the research environment; the already installed system Python
provided pytest and YAML, with no package installation. Hosted acceptance and
measured CI-minute savings remain unproven. No original requirement closes.
