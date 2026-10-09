# Change records and changelog policy

Effective 2026-10-09. Implementation: Codex; changed/evidence/limits entry shape
adapted from Claude's reviewed draft. Applies to Michael, Claude, Codex and future
contributors. Scope: F-150, WP-RELEASE and WP-SITE. The previous human changelog remains
intact; structured enforcement starts here.

Every committed behavior, copy, policy, dependency, scope, verification or
operational-evidence change needs a **new** entry and event. The event records UTC
time, actual contributor, existing scope IDs, exact file hashes, executed checks
and/or hashed public evidence, and explicit limits. Events are append-only. A
correction is another event. A change recorded after it shipped is retrospective:
its timestamp is recording time and its historical source commit is explicit.

## Record a change

First implement and run its checks. Then:

```sh
npm run changelog -- --author Codex --slug describe-the-change \
  --records WP-SITE F-139 \
  --files site/src/main.jsx docs/your-change.md \
  --changed "Describe the resulting behavior." \
  --proves "Name the exact checks and their limits." \
  --limits "Human usability and independent accuracy remain unverified." \
  --gate "python3 -m unittest discover -s tests -p test_changelog_pipeline.py"
npm run verify:changelog
```

Use `--evidence runs/your-public-check.json` to hash an existing evidence file.
Use `--historical-source <full-source-commit>` only to record earlier work, without
pretending to know its original completion time. `--files` is explicit to avoid
crediting another contributor's in-flight work; omitting it captures all current
changes. Author is required and has no agent default. Check commands use argv,
not shell expansion; use separate commands for separate checks. Failed checks
write neither entry nor event. Output is not saved, avoiding accidental secret
capture. Do not put secrets or private answer text into arguments or evidence.
An exclusive lock and unique filenames prevent writers overwriting each other;
normal failures roll back the event. A process crash between writes is caught as
an inconsistent record by the verifier and needs repair before continuing.

## Enforcement

`npm run verify:changelog` compares working files, including staged changes and
untracked files, with HEAD. It requires a fresh event matching each changed file.
A pre-existing entry or an edit after recording fails. To check a committed range:

```sh
npm run verify:changelog -- --base <previous-commit> --head HEAD
```

CI checks the push/PR range with full Git history. It refuses a CI invocation
without a base rather than silently accepting a clean checkout. Current evidence
must match its recorded hash. Old structured events cannot be edited or deleted,
and their human entries must still agree. Generated build output, node_modules,
private ignored files and the changelog/event pair itself are excluded from file
coverage; all tracked source and operational evidence remain covered.

The supported npm site build/deploy commands (including direct `--prefix site`)
and Make build/verify/deploy entry points require this gate. Low-level individual
checks remain runnable to gather evidence **before** recording. Install the
versioned pre-commit hook with `make hooks-install` for a Git guard too. The hook
checks an isolated copy of the actual staged index: an unstaged entry cannot
justify a commit, and another contributor's unrelated drafts cannot block it. Direct
low-level provider commands can bypass local wrappers; CI and review still apply.
This is change-accountability enforcement, not a tamper-proof security boundary.

## Acceptance is separate

A passing engineering check never grants independent tag accuracy, certification,
or 100% scope completion. These event records are `engineering_only`; an
independent-release claim is rejected even if an unrelated UI test passed. A
future release acceptance record must implement its own held-out ground-truth,
sampling, calibration and per-tag gate contract. Until then record actual
engineering behavior and limits, and keep acceptance status in scope-progress.json.

CHANGELOG.md is the readable index; runs/changes/ is its structured audit trail;
docs/scope-progress.json holds acceptance, next fixes and attribution; state.json
holds current runtime/publication truth. Public readers can download the
changelog from the site's existing reference area and inspect the records in Git.
