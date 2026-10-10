# Observed runtime SBOMs

These are inspectable SPDX 2.3 inventories of the three actual Linux amd64 staging
images, scanned on 2026-10-10 with Syft 1.54.1. They contain 421 package occurrences
across the images (shared packages are counted in each image), plus one image
subject per document. No production data or host configuration was scanned.

- [Gateway inventory](../sbom/runtime/gateway-linux-amd64.spdx.json): 118 packages.
- [Evaluator inventory](../sbom/runtime/evaluator-linux-amd64.spdx.json): 124 packages.
- [Redactor inventory](../sbom/runtime/anonymizer-linux-amd64.spdx.json): 179 packages.
- [Identity manifest](../eval/dependencies/runtime-sbom.json).
- [Actual scan and missing-license results](../runs/2026-10-10-runtime-license-inventory.json).

The scanner archive was checked against the upstream release checksum and GitHub
asset digest before execution. Its Sigstore identity has **not** been verified.
The SPDX documents are unsigned. A matching SHA-256 checks file identity, not
publisher authentication, malware, license clearance or accuracy. Package/build
inputs changing make the verifier refuse these inventories pending a rescan.
Image identities are observed build artifacts, not a reproducible-build claim.

Run the offline verifier from the downloaded repository:

```sh
python3 scripts/verify-runtime-sbom.py
```

It checks the exact three document hashes, build/package input hashes, SPDX
subjects against image/config and manifest identities, observed scan attribution
and unique package IDs. It refuses changed/missing artifacts, unknown images,
unsafe paths, symlinks and unsigned-to-signed or uncleared-to-cleared promotion.
It is a bounded consistency verifier, not a full SPDX standards validator.

For a new observed image, export an OCI archive on an isolated Linux builder,
then use the hash-verified scanner; no local Docker daemon is required:

```sh
syft scan oci-archive:gateway.oci --parallelism 2 \
  --source-name aitrust-gateway --source-version IMAGE_CONFIG_SHA256 \
  -o spdx-json=gateway-linux-amd64.spdx.json
```

Update each observed image and manifest from actual execution, preserve the scan
receipt, and review licenses before enabling any clearance gate. Do not treat
editing the manifest as evidence of a scan or signature. Source-bound release
signing requires the separate accepted Sigstore identity/transparency process.

There are seven packages without declared licenses in each smaller image and
19 in the redactor, including embedded launchers and the Python binary. Some may
have license notices the scanner did not recognize; missing metadata is not a
finding that software is proprietary. All need review. npm's optional platform
packages, browser/Pyodide/model/runtime/font/data assets, vendored components,
redistribution notices and other CPU architectures also need coverage. F-057
and X-02 remain open; this inventory alone cannot close either full requirement.

Upstream sources: [Syft source scanning guide](https://oss.anchore.com/docs/guides/sbom/getting-started/),
[output formats](https://oss.anchore.com/docs/guides/sbom/formats/),
[versioned release](https://github.com/anchore/syft/releases/tag/v1.54.1),
[Sigstore verification](https://docs.sigstore.dev/cosign/verifying/verify/),
[Open Source Definition](https://opensource.org/osd).
