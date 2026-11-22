# Keep an assertion compatible without changing its findings

This free offline tool converts a **complete unsigned assertion** between the
existing `0.1.0` format and the separate complete-preprocessing `0.2.0` format.
Only `spec_version` changes. Tags, evidence, thresholds and all other values stay
the same. Nothing is uploaded, evaluated again or automatically enabled.

The website, gateway, extension and replay tool still use `0.1.0`. They explicitly
refuse `0.2.0`; converting back makes a complete supported record compatible with
their existing capability. This tool does not release a new tag or production
protocol. An unchanged finding still carries its original method and limitations.

Use Python 3.12+ with this repository's existing hashed verification dependencies
(`eval/requirements.lock`) and `jsonschema`/Pydantic available. No model, container,
account or new service is needed. Missing dependencies produce Unavailable.

## Check first, then save privately

Keep the original assertion outside Git in a private regular file owned by you,
mode `0600`. Resolve any symbolic links in its containing path first. To inspect
conversion without saving a new record:

```sh
python3 scripts/migrate-assertion.py /private/path/original.json --to 0.2.0
```

The brief result lists the source and target versions and whether conversion was
possible. It never prints the assertion, its fingerprints or your private path.
`-` accepts at most 2 MiB from standard input instead of reading a file.

To save, use a **new** destination under an existing directory owned by you with
mode `0700`, outside Git. Existing files are never overwritten:

```sh
python3 scripts/migrate-assertion.py /private/path/original.json --to 0.2.0 --output /private/path/upgraded.json
python3 scripts/migrate-assertion.py /private/path/upgraded.json --to 0.1.0 --output /private/path/restored.json
```

Exports are mode `0600`. They retain hashes, spans, timestamps and method metadata
that can link information. Preview/redact separately before sharing; an export
is not automatically safe to publish. Original bytes are never modified.

## When conversion stops

| Result | Meaning | Next step |
| --- | --- | --- |
| Transformed (exit 0) | Both schemas and the complete, self-consistent preprocessing identity passed. | Keep the original; choose explicitly whether to export. |
| Invalid (exit 1) | Malformed, duplicate-key, nonfinite, non-scalar, too-deep, oversized or schema-invalid input, or a number that would lose decimal precision. | Correct the source from its genuine provenance; do not invent missing history. |
| Unsupported (exit 2) | Unknown source/target version or a same-version request. | Preserve the record and use a supported route. |
| Unavailable (exit 3) | Missing/incomplete history, any signature member, missing dependencies, changed schemas or unsafe private input/output. | Keep the original; resolve the specific prerequisite. |

Signed assertions are refused even if the signature is empty or null: changing a
version invalidates signed bytes. This tool does not strip, verify or reissue
signatures. Missing preprocessing defaults are never filled in. A matching
self-digest establishes consistency, **not authenticity** or historical runtime
availability.

The supported numeric representation preserves integer precision (including
integers larger than JavaScript's safe range) and floating/integer types.
Floating decimal values that Python's JSON representation cannot round-trip
without rounding or underflow are refused **before** conversion. Whitespace,
key order and equivalent exponent notation are not byte-preserved; the unchanged
original remains available for those details.

If `output_may_exist:true` appears after a publication, synchronization or close
failure, a complete destination may already exist. Inspect that exact destination
before retrying. No rollback, forensic erasure or crash-durability guarantee is
made. No output is created for input/schema refusals.

## Reproduce the compatibility checks

```sh
python3 scripts/verify-assertion-migration.py --report output/verification/assertion-migration.json
```

The published invented vectors and independent Node reference cover version-only
transformation and numeric-preserving round trips. The reference is for trusted
vectors, not untrusted user input. Actual CLI checks also cover current consumers,
private export, unsafe inputs, publication uncertainty and unrelated PS operation.
These checks establish compatibility, not independent tag accuracy.
