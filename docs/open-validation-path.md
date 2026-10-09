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

Use Python 3.12+, Docker Engine with Compose (or existing Docker Desktop), and
Git. Linux Engine/Compose is the open-source route; Docker Desktop has separate
vendor licensing. Node 22+ is needed for browser/site tests, not this checker.
Initial image/package/model downloads require a network.

```sh
git clone https://github.com/knwvmbrr/aitrust-id.git
cd aitrust-id
python3 -m venv .venv
.venv/bin/python -m pip install -r eval/requirements.txt
python3 scripts/aitrust.py init
make deploy ENV_FILE="$HOME/.config/aitrust-id/runtime.env"
.venv/bin/python scripts/aitrust.py doctor
.venv/bin/python scripts/aitrust.py check response.txt
```

Alternatively paste into `.venv/bin/python scripts/aitrust.py check`, then Ctrl-D.
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
See docs/development.md for browser verification and removal instructions.

## Verify and challenge

```sh
.venv/bin/python -m pip install --require-hashes -r services/gateway/requirements.lock
.venv/bin/python -m pytest tests -q
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
make down ENV_FILE="$HOME/.config/aitrust-id/runtime.env"
```

Remove the extension token before unloading it. Retain or remove your own local
configuration separately. No unrelated Docker cleanup is part of uninstall.
Do not upload real content to the research hosts.


Public reference downloads also work with ordinary curl or an identified
`AITrust-ID-Validator/0.1` user agent. The observed default Python urllib agent
received Cloudflare error 1010; that transport response is not an evaluation
result. The full repository includes the evidence and datasets for offline use.
