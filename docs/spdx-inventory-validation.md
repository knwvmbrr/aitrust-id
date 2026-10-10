# Check the dependency inventories offline

The downloadable repository includes the three observed Linux amd64 image
inventories in `sbom/runtime/`. With the existing hash-locked gateway and
evaluation dependencies installed, run:

```sh
python3 scripts/verify-runtime-sbom-standard.py
```

No container daemon or internet connection is needed for verification. A missing
validator dependency, schema, license notice or inventory refuses the check.
The lighter `python3 scripts/verify-runtime-sbom.py` remains available without
third-party Python dependencies; it checks bindings, not the official schema.

The stronger check first verifies the actual inventory/image/source bindings.
It checks the unmodified official SPDX 2.3.1 JSON schema, pinned to upstream
commit `6f2cb47d13db19b12c23885573b22ef32ec1ada5`, and its original CC BY 3.0 notice.
The JSON parser rejects duplicate keys, oversized input and symlinks. Schema
resolution is local only. It then checks global element identities, local
relationships, creation time, described packages, SHA-1/SHA-256 digests and the
package verification codes supplied by the current inventories.

**All three inventories pass; 261 package verification codes reproduce.** The
focused inventory suites pass 55 tests. The complete current Python suite passes 1,099,
with one existing Starlette/httpx deprecation warning. The controls include
inventories whose altered bytes and manifest hashes were regenerated to match:
invalid schema data, colliding identities and malformed hashes still fail.
The real inventory test refuses any attempted socket connection.

[Actual inventories and checks](../runs/2026-10-10-spdx-standard-inventory.json)
· [Execution summary](../runs/2026-10-10-spdx-validation-controls.json)
· [Full current Python execution and target controls](../runs/2026-10-10-target25-source-checks-repaired.json)

The required `spec` CI job now runs the stronger verifier and corruption tests.
All eleven required contexts passed on both the first push and PR source
`a3c3e2509fa80aa4cc827395a8ecddefecce9437`; see
[actual hosted checks](../runs/2026-10-10-spdx-first-hosted-engineering-pass.json).
The README review correction requires fresh checks before normal protected merge.

## What a pass establishes

The pinned inventory bytes have valid official JSON structure and pass the
selected local consistency checks. A matching package verification code is
computed from the hashes recorded in that inventory. It does **not** authenticate
files that were not independently supplied and checked.

This is not full SPDX semantic conformance, a complete dependency inventory,
license permission, a vulnerability assessment, trusted scanner identity,
reproducible builds or a signed release. External documents, snippets and digest
algorithms outside SHA-1/SHA-256 need another reviewed profile. SPDX supports
more than this profile. The specification's optional verification codes stay
optional; this checker does not invent a requirement to include them.

F-057 and X-02 remain open at their existing milestones. Their full acceptance
still needs unknown/vendored/OS/model/client/build/architecture license coverage,
reviewed redistribution notices, trusted scanner identity and executed
source-bound Sigstore release signing. No tag or certification release is granted.

Primary sources: [unmodified upstream schema](https://github.com/spdx/spdx-spec/blob/6f2cb47d13db19b12c23885573b22ef32ec1ada5/schemas/spdx-schema.json),
[upstream license](https://github.com/spdx/spdx-spec/blob/6f2cb47d13db19b12c23885573b22ef32ec1ada5/LICENSE),
[SPDX package fields, including clause 7.9](https://spdx.github.io/spdx-spec/v2.3.1/package-information/).
