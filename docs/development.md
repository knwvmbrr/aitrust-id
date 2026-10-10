# Local development and verification

This is a development preview, not a validated public release. PS is the current tag code; UC/SC/BT remain proposed. Text on ChatGPT is the initial adapter target. One live Homebrew response is verified; broader vendor compatibility and human
screen-reader use remain unverified. Follow docs/open-validation-path.md to run
the manual checker without a browser adapter.

## Setup

Use Python 3.12, Node.js 22, and Docker. Create a virtual environment and install:

```sh
python3 -m venv .venv
.venv/bin/pip install --require-hashes -r services/gateway/requirements.lock
.venv/bin/pip install -r eval/requirements.txt
npm ci
npx playwright install chromium
```

Keep the gateway environment file outside the repository. It must contain AITRUST_TOKEN with a generated secret of at least 16 characters. Do not print the token into a public transcript. Docker build downloads dependencies and the English model; inference does not require those downloads.

```sh
make build ENV_FILE=/absolute/path/to/private/runtime.env
make up ENV_FILE=/absolute/path/to/private/runtime.env
make verify PYTHON=.venv/bin/python
make verify-runtime PYTHON=.venv/bin/python ENV_FILE=/absolute/path/to/private/runtime.env
make gates PYTHON=.venv/bin/python
```

The gate command currently returns failure: the 24-example regression set is not a frozen independently labeled holdout, its intervals do not clear the candidate gates, and scores are uncalibrated. Passing regression tests does not override this.

Load extension/ unpacked in a dedicated Chrome profile. Set the gateway token in its options. Remove the token there and unload the extension to remove access. Shut down this project's containers with make down and the same ENV_FILE. Do not run Docker cleanup against unrelated projects.

## Verification boundaries

Python tests exercise evaluator patterns and gateway HTTP behavior with controlled dependency responses. Browser checks exercise real DOM, closed-shadow behavior, out-of-order and stale results, and HTML-injection resistance on a synthetic page. Axe checks instrument that fixture with an open shadow root because automated discovery cannot traverse its normal closed root. Real-extension smoke checks load the production manifest and talk to real local services on a routed synthetic ChatGPT-origin page:

```sh
AITRUST_ENV_FILE=/absolute/path/to/private/runtime.env node scripts/verify-extension.cjs
```

That test does not prove live ChatGPT selectors remain compatible. It also does not replace manual screen-reader assessment or independent labels.

Gateway is on an edge network to support Docker Desktop loopback publishing. Anonymizer and evaluator sit only on the internal inspection network. The verified egress probe is a bounded external TCP test, not proof against every possible exfiltration channel. Hashes are correlation identifiers. Detected PII redaction is incomplete by nature.

Only text is enabled by the gateway. Non-text requests return an explicit unsupported-modality HTTP error until subject byte/offset contracts are implemented; reserved enum values are not a support claim. No new endpoint was introduced.

## Changes requiring specification review

Context-aware behavior uses sig.piped_installer.v3 and sig.obfuscated_payload.v2; substitution methods are now v3/v3/v2 under context-v5. Their v1 IDs are not silently mutated. Methods and limitations are documented under development methods in spec/signals.md; accepted conformance registration still requires independent evidence. Scores are displayed as uncalibrated heuristic method data, never a probability.

## Reproducible runtime and audit limits

Each service image installs requirements.lock with pip --require-hashes. requirements.freeze
records the pinned resolution inputs; update the input requirements and regenerate the
lock with pip-compile on Python 3.12 before rebuilding. The English model wheel has an
explicit SHA-256 in the anonymizer lock. Runtime uses UID 10001, a read-only root filesystem,
no Linux capabilities, no new privileges, and a bounded temporary filesystem. HTTP request
bodies are capped at 1,250,000 bytes before parsing, separately from the 200,000-character
text bound.

The dated package audit records zero known findings in audited package versions. The
direct-URL language model was skipped by pip-audit and its hash does not establish security.
Application and OS-image review remain separate requirements. The automated live-site probe
hit ChatGPT browser verification; do not treat the synthetic-origin test as a live-site pass.


## First-tag validation pass

Run `python3 scripts/prepare-ps-review.py --help` for the independent review
preparation tool. It freezes method, policy and item hashes and exports two blind
CSV forms; it never runs predictions or certifies reviewer independence. See
`docs/independent-review.md`. Keep its files outside this public repository.

The latest development corpus has five active sets and 86 cases. Containers must
be rebuilt after the context-v5 method update; old container evidence is historical,
not proof that this version is running. Docker Desktop is not launched automatically
by the verification scripts. The local daemon was unavailable during this pass.

## Device build reference

`python3 scripts/verify-device-build-matrix.py` runs without a prior site build.
The expected artifact is committed in `docs/device-build-reference.json`; the
runtime manifest is generated and ignored. Method/projection changes must update
this reference through a reviewed, recorded change. The verifier never silently
refreshes it. Repeat `--python /path/to/python` to compare actual installed
builders. `tests/test_device_matrix_checkout.py` executes a minimal clean checkout
and a deliberately incorrect reference.

## Linux staging conformance (current source)

The selected context-v5 stack has also executed on Debian with Podman 5.4.2 and
podman-compose 1.3.0. Debian's daemonless engine needs `aardvark-dns` for container
name resolution. Use absolute compose/env paths with that compose version. Builds
need working network DNS; on a host with a loopback-only resolver, a build-only
host-network setting worked. Never transfer that setting to inference containers.
Explicit source COPY permissions make a restrictive checkout/extraction umask safe
for the non-root runtime. Existing host default-deny firewall policies can block
container DNS/internal traffic; review narrowly scoped private-bridge rules rather
than opening public ports or globally allowing forwarding.

On a dedicated **disposable staging** project, after the services are healthy:

```sh
python3 scripts/verify-service.py --engine podman \
  --project aitrust-staging --env-file /absolute/private/runtime.env \
  --disrupt-staging-dependencies --output /absolute/private/service-report.json
```

Use the engine's required administrative permissions on Linux. The verifier
refuses projects outside the staging naming boundary. The disruption option stops
and restarts each dependency, so never point it at production. Inspect the source
before executing. Only synthetic input is submitted. A safe failure record reports
its source location; it excludes exception bodies and credentials. Successful
reports are reproducible engineering evidence, not tag accuracy or a public API.
Current execution: `runs/2026-10-10-current-service-conformance.json`.
