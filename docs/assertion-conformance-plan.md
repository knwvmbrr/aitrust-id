# Offline assertion conformance: architecture before implementation

An outside implementer needs a local command for their own JSON record, separate
from running our evaluator. Add a bounded, offline command over the reference
2020-12 schema and the current extension profile. The schema layer checks syntax;
the extension layer checks current version, supported capabilities, coordinate
bounds and the unsigned preview boundary. Neither proves accuracy or signer trust.

Read at most 2 MiB from standard input or a regular file, with strict UTF-8,
unique object keys and finite numbers. Refuse external schema references. Never
print submitted data, paths inside the record, signature bytes or exceptions.
Return one small JSON summary: accepted (exit 0), invalid (1), or unsupported
version/capability (2). Missing tooling is unavailable (3). The extension profile
uses the same JavaScript validator that actually runs in the extension; do not
create another approximation. Node is needed only for that optional profile.

Compatibility is explicit: 0.1.0 is the only implemented wire version. Reserved
schema fields are syntactically checkable but are not runtime support. Future
versions are retained unchanged and refused by current consumers; never relabel
PS as UC or guess a migration. Any future migration must identify both schemas,
the transformation, evidence loss and round-trip behavior before acceptance.

Risks: a schema pass can look like certification. Summaries must always state that
signature verification and independent accuracy are not performed. The stricter
extension profile can legitimately reject a schema-valid proposed capability.
Test those distinctions, duplicates, invalid dates, scalar UTF-8, oversized input,
non-finite numbers and missing checker dependencies. Executing copies of synthetic
third-party records tests the tool; it is not an actual outside-person review.
