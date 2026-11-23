# Check a selected source copy

**Historical selection:** the commands and counts below describe the original V2 source at `80ec9523`. The current protected-source continuation uses [the current guide](source-snapshot-rights-current-main.md); do not treat these earlier receipts as current qualification.

This optional local checker identifies the source-copy obligations for one finite,
reviewed repository tree. It does not build or approve an archive, install a
runtime, sign anything, contact a server or issue a tag.

From a trusted checkout containing this v2 implementation:

```sh
python3 -I -S -B tools/source_release_policy_v2.py --source-commit dfcfb45ef79bca97d4b4c3ad41bb89b73865d341
python3 -I -S -B tools/source_release_policy_v2.py
```

The first command selects the exact known development source independently of
the actual checkout. The second selects actual HEAD and refuses new unclassified
paths. A passing result reports both identities and `source_copy_profile_satisfied`.
`dfcfb45` is an unprotected development commit; the protected baseline is
`085106c1`. Neither command makes a protected-release or authenticity claim.

V1 remains unchanged and independently callable. V2 inherits its exact source
categories, grants and notice requirements, then records 567 explicitly reviewed
file changes/additions with 292 origin/grant records. The selected tree has
13,468 files and 139,954,777 raw source bytes. The 521 formerly unknown paths
include the CFFI/libffi, Rust and MCP cohorts and named project code and records.
No suffix or future directory is automatically assigned a license.

Existing CC-BY specification/schema attribution, Unicode notices, OFL fonts,
C2PA/NLI component terms and source-specific copyright blocks remain applicable.
New retained CFFI/Rust source has its own original grants; it is not relabeled
Apache. The source tree carries all referenced grant/notice bytes. The aggregate
MCP notice and obligation index retain their individual component terms. The
exact publisher OpenSSL build-tool attribution remains a source-only observation,
not an assertion that GPL/Artistic tools are shipped in an installed runtime.

Only named maintained project text can change under the existing project grant,
with its recorded declaration lines preserved. Eight named new v2 source/docs/
evidence paths may use the existing project LICENSE/NOTICE. This trusts the
reviewed maintainer attribution contract; it is not forensic authorship detection
and does not authorize copied outside material to acquire the project license.
Changed third-party files, altered grants, missing notices, unknown paths,
malformed policy, unsupported Git entries and unavailable checks fail closed.
Unavailable results omit file observations rather than inventing measured zeroes.

The checker reads committed Git objects using a captured hash-pinned neutral
supervisor. It ignores inherited Git configuration/replacements and preserves the
existing HOME value without reading home configuration. Copied subject files are never imported
or executed. Limits are 16,384 source entries, 32 MB per source blob, 256 MB raw
source, 2 MB Git listing/output, 12 MB policy and a 30-second whole-check budget.
Changed named project text has an additional 2 MB individual/64 MB aggregate
inspection budget. These are decimal byte counts. No source archive is retained.

A source-copy result alone does not bind a received archive to that source. The
separate archive-to-trusted-Git verifier, actual distribution policy, applicable
runtime obligations, protected signing and managed consumer still apply. Legal
clearance, runtime permission, accuracy, release approval, source-archive admission
and complete F057/X02 acceptance remain false. The existing PS and MCP distribution
routes are unchanged by this standalone helper.
