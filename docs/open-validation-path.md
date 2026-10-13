# Runnable PS review package

## Architecture and claim

The downloadable repository and site are public entry points. The checker runs
on the person's machine, through the same authenticated gateway, redactor and
evaluator as the Chrome adapter. It adds no remote inference endpoint, upload
collection or paid API. Code supplied as input is never run.

PS reports supported command-risk patterns. It does not validate an AI answer's
truth, identify a scam, certify a publisher, or clear untagged content as safe.
Its schema-validated record binds a versioned method to the redacted subject.
Independent accuracy, accessibility and acceptance remain separate release gates.

## Install and use

Use Python 3.12+, Git, and an already installed Linux Podman engine. The
setup command does not install or grant access to a privileged engine. Engine
permissions must already work (`podman info`). Initial image/package downloads
require a network. The one-command acceptance was executed with Linux Podman and cached pinned
dependencies. The `--engine docker` branch has not been runtime-tested; the older
manual Docker Compose path remains available.
Docker Desktop has separate vendor licensing. Node is not needed for this checker.

```sh
git clone https://github.com/knwvmbrr/aitrust-id.git
cd aitrust-id
python3 scripts/setup-local.py --engine podman
```

That single setup command creates an owner-private token and checker environment,
builds three constrained services, verifies their effective limits and source
identity, and tests the authenticated redaction/evaluation pipeline. It uses
127.0.0.1:8787. A port conflict or existing setup directory fails without adopting
or replacing another installation. The default private directory is
`~/.config/aitrust-id/local-stack`; `--state-dir` selects another new private
location outside the repository. An optional `--wheelhouse` supports offline,
hash-locked checker installation with previously downloaded wheels. Image builds
still need their initial downloads or an existing verified build cache.

Check your own text after setup:

```sh
LOCAL_STATE="$HOME/.config/aitrust-id/local-stack"
"$LOCAL_STATE/checker/bin/python" scripts/aitrust.py check response.txt --env-file "$LOCAL_STATE/runtime.env"
```

The recorded complete-input Linux acceptance used `--build-network host` for
initial dependency downloads, an explicit option when an isolated builder cannot
reach DNS. This permits image-build processes to reach host networking; choose
it only for the reviewed, hash-locked build. Runtime service networks, ownership,
resource limits and loopback binding stay isolated. The default remains private.

```sh
python3 scripts/setup-local.py --engine podman --build-network host
```

The setup path is an unsigned CLI development preview. Extension signing/key
installation is separate; see [gateway authentication](gateway-authentication.md).
It does not release PS, complete human accessibility acceptance or collect data.

The existing manual Compose path remains available: create a private credential
with `scripts/aitrust.py init`, install the hashed evaluation requirements in your
own virtual environment, then use `make deploy` with that credential file.
Do not mix the two installations on port 8787.

Alternatively omit `response.txt` in the checker command, paste text, then Ctrl-D.
`--json` prints the schema-validated record, without response text.
`--fail-on-finding` returns 2 for a PS finding, 0 for a completed check otherwise,
and 1 when no valid evaluation could be obtained. Uncertain is not a safety pass.

The CLI refuses redirects and system proxies and only contacts 127.0.0.1:8787.
Empty, non-UTF-8 or oversized input, invalid records and unsupported tags fail.
The evaluator source hash must match this checkout; stale services require rebuilding.
Credentials live in an owner-only file outside the repository; initialization
never overwrites an installation. Another application's use of port 8787 blocks
startup; UNAVAILABLE is not a successful check.

The extension is optional. Load `extension/` using Chrome's unpacked-extension
workflow, open its options, and supply your existing local token from the private
file. It is saved in extension-local storage, not sync. Never publish/share it.
The extension starts paused. In options, explicitly enable ChatGPT checks after
saving the token; token saving does not enable capture. Pause stops new capture,
cancels in-flight checks and removes tags. Reset removes token and consent locally;
server credentials, ChatGPT conversations and your downloads remain yours.
See docs/development.md for browser verification and removal instructions.

## Verify and challenge

Check a record from your own implementation entirely offline:

```sh
.venv/bin/python scripts/check-assertion.py your-record.json
.venv/bin/python scripts/check-assertion.py --profile extension your-record.json
```

The first command checks the full schema and required date/UUID formats. The
second also uses the actual current extension profile (Node is required for that
profile). Exit 0 means the selected structural checks accepted the record; 1 means
invalid, 2 unsupported, and 3 unavailable tooling/input. Neither verifies a
signature, measured accuracy or certification. The CLI never prints submitted
fields and reads at most 2 MiB. It accepts standard input if no filename is given.
Only wire version 0.1.0 is supported; future versions are refused unchanged, not
guessed or relabeled. Signed records are structurally checkable by the schema
profile but refused by the unsigned extension profile. Reserved modalities are
schema values, not detector support. See [conformance boundaries](assertion-conformance-plan.md).

```sh
.venv/bin/python -m pip install --require-hashes -r services/gateway/requirements.lock
.venv/bin/python -m pytest tests -q
.venv/bin/python scripts/verify-dependencies.py
.venv/bin/python scripts/verify-regressions.py
.venv/bin/python scripts/verify-runtime.py --env-file "$HOME/.config/aitrust-id/runtime.env"
```

Public GitHub issues accept synthetic reproducible bugs and tag disagreements.
Include method/record metadata and expected behavior, not private AI text.
Public discussions are the development townhall. Site drafts are never sent
automatically; check visibility before manually posting. Vulnerabilities go
through GitHub's private report control. Posting is not training consent.

Independent reviewers must freeze and label new data before viewing predictions.
Development regressions cannot become a holdout. Follow docs/independent-review.md
and the PS acceptance packet. The statistical gate fails until its evidence
exists. Successful setup does not override it.

Stop only this project's services:

```sh
python3 scripts/setup-local.py --stop
# For the older manual Compose installation only:
# make down ENV_FILE="$HOME/.config/aitrust-id/runtime.env"
```

Remove the extension token before unloading it. Retain or remove your own local
configuration separately. The stop command checks recorded resource IDs and matching ownership labels. It
retains private files, removes only its own containers/networks/images, and
refuses resources whose ownership changed. No unrelated engine cleanup occurs.
A failed setup keeps its private record; inspect it before removing private files
and retrying. Failure is not readiness.
Do not upload real content to the research hosts.


Public reference downloads also work with ordinary curl or an identified
`AITrust-ID-Validator/0.1` user agent. The observed default Python urllib agent
received Cloudflare error 1010; that transport response is not an evaluation
result. The full repository includes the evidence and datasets for offline use.
