# Selected dependency contract

The active preview has six install roots: the gateway, redactor, evaluator,
evaluation tools, and the two npm projects (root browser tools and site). Each
Python install uses a complete `--require-hashes` lock; npm installs use `npm ci`
and the lock's integrity fields. The three active images share an immutable
multi-platform Python 3.12 base index, including Linux amd64 and arm64. The
redactor additionally seals and verifies all model assets before use.

Architecture: publish an inspectable inventory containing lock hashes, package
versions, artifact hashes and the base digest, but no host addresses or private
credentials. Check active Compose targets against that inventory. Deliberately
remove a package hash, npm integrity or base digest and require failure. A clean
Python/npm install provides installation evidence; static inspection alone does
not. Fresh install reports list artifacts, not submitted application data.

Risks: pins freeze vulnerabilities as well as behavior. Refreshes must change the
inventory, rebuild services and run source-bound regressions before publication;
do not use mutable tags as an automatic update mechanism. A package hash checks
artifact identity, not the trustworthiness or license of its author. OS image
digests do not promise reproducible binary builds or a future security clearance.

The registry remains an inactive legacy proposal with an unlocked build. It is
not part of the selected preview, not an offered persistence service, and cannot
be included in a release inventory until independently locked and tested. Future
research, signing, receipt and organization routes require their own inventories.
The desktop application's runtime and commercial hosting are not dependencies
of the downloadable checker; vendor infrastructure is disclosed separately.

Current base: `docker.io/library/python:3.12-slim@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1`.
Its OCI index was inspected on the dedicated staging host, with amd64, arm64 and
other platform entries. The index identity is stable; the observed amd64 child is
`sha256:2b4f19dae3a777dfc3b76730bda1e82e1f66ab2a2686fa93ca78edbfb4f04ffe`.

Refresh evaluation locks in a dedicated builder with Python 3.12, pip 24.3.1 and
pip-tools 7.4.1:

```sh
pip-compile --generate-hashes --no-emit-index-url --no-emit-trusted-host --output-file=eval/requirements.lock eval/requirements.txt
```

Review all transitive changes. Never include private index credentials in a lock
header. Run the dependency verifier and a clean hash-required installation.

[Observed runtime SPDX inventories](runtime-sbom.md) now bind the three scanned
Linux amd64 images. They remain unsigned and are not license clearance or
complete client/build coverage; missing declarations are recorded for review.
