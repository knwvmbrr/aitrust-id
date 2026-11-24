# Static web artifact engineering profile

This optional offline tool reconstructs the existing runtime and npm notices, checks a complete observed build, and produces a deterministic static ZIP. It does not start a web server, execute received JavaScript, admit the web distribution route, or issue project-wide license/accuracy clearance.

From the repository root, check the retained source and grant facts without installing or importing a builder:

```sh
python3 -I -S -B scripts/web-checker-artifact.py sources
```

The check reconstructs fourteen runtime companions and the thirty-five-package npm notice cohort. It retains the separately reviewed Vite, Tailwind and Rolldown source grants for any emitted helpers/styles. React scrollbar2.3.8's project-grant correspondence remains a documented inference: the exact registry Git commit was unavailable. The old notice output and that limitation stay unchanged; the additional source-grants record points to the recovered facts.

An intentional build must use the new observer configuration instead of the ordinary Vite invocation, with the existing locked packages already supplied by the approved build environment:

```sh
cd site
python3 ../scripts/web-distribution.py prepare
node scripts/prepare-device.mjs
node scripts/prepare-performance.mjs
node scripts/prepare.mjs
node node_modules/vite/bin/vite.js build --config ../scripts/web-checker-build-observer.mjs
node scripts/render-reference.mjs
node scripts/prepare-offline.mjs
cd ..
```

These are future integrated-build instructions. This component handoff did not execute that build, install dependencies, or qualify its whole module census. The observer is inert when imported as a factory; its default configuration loads the existing builder only for the intentional build command above. An existing dist without `web-build-observations.json` is unsupported. No historical build gains a fabricated observation.

After that genuine build, select the exact commit independently, create a private parent outside every Git checkout (`0700`), and package to a NEW directory:

```sh
python3 -I -S -B scripts/web-checker-artifact.py prepare \
  --directory /absolute/build/site/dist \
  --destination /absolute/private/new-web-package \
  --source-commit YOUR_EXACT_40_CHARACTER_COMMIT
python3 -I -S -B scripts/web-checker-artifact.py inspect \
  --artifact /absolute/private/new-web-package/checker.zip \
  --source-commit YOUR_EXACT_40_CHARACTER_COMMIT
```

The producer includes all final static files, the nineteen-file runtime projection, unchanged npm companions, source grants and observed module notices. Missing companion files are generated from pinned trusted project producers; an existing inconsistent companion refuses. Unknown source/module/provider/member names, changed copied-source identities, omitted companions, noncanonical archives, aliases and excessive resources refuse. Source/build inputs must match the selected Git tree. Installed npm source bytes are builder observations associated with the pinned lock; this does not claim compiler reproduction or a native build-tool distribution grant.

`inspect` verifies format/source data only and never materializes or executes received content. Its false release/signature claims are intentional. A protected signature is necessary for the separate managed operation:

```sh
python3 -I -S -B scripts/web-checker-artifact.py managed \
  --artifact /absolute/download/checker.zip \
  --packet /absolute/download/evidence.json \
  --spdx /absolute/download/sbom.spdx.json \
  --bundle /absolute/download/checker.sigstore.json \
  --trusted-roots /absolute/independently-selected/roots.jsonl \
  --destination /absolute/private/new-managed-web \
  --source-commit YOUR_EXACT_40_CHARACTER_COMMIT
```

The user independently selects repository/commit and obtains roots. Received files cannot choose a signer, runner, command, approval flag or trust root. The managed operation first makes bounded opaque quarantine copies. It uses the unchanged protected-main GitHub identity, current policy and real attestation verifier before reading member metadata or writing the `site` subtree. It additionally requires the exact build object in the authenticated Graph node `web:build-observation`. Current shared web policy/Graph have not admitted this profile, so the genuine managed positive is deliberately unavailable until ROOT's distinct integration, signing and consumer qualification. Injected-authority tests are not a cryptographic result.

Successful materialization creates private `0600` files in `0700` directories. It starts no server, browser or script. The quarantine evidence remains alongside the static files. Outputs are never overwritten or recursively removed. If creation, cancellation, namespace instability or a close fails after a creation attempt, fixed JSON reports `output_may_exist:true`. Inspect retained private files before retrying with a new name. There is no claim of universal protection from a hostile concurrent same-user writer.

The API supports POSIX main-thread, single-thread operation without an existing real-time timer. It installs/restores one temporary deadline:115 seconds of managed work plus the existing supervisor's five-second cleanup allowance. Existing HOME is untouched. Artifact/file/count/path, JSON, source, read and descriptor limits are fixed in the pre-code plan; no caller override exists. The read ledger conservatively precharges the pinned legacy call composition. Trusted GH's opaque internal reads are separately supervised, not falsely counted as Python body reads. Actual whole-build peak memory and integrated current-policy permission remain later evidence requirements.

This profile is a bounded F-057/X-02 engineering component. Other distribution routes, complete embedded obligations, production publication and the original whole-project criteria remain separate.
