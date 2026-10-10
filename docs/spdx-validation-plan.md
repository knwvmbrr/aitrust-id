# SPDX inventory validation: architecture and limits

Use the unmodified SPDX 2.3.1 JSON schema from upstream commit
`6f2cb47d13db19b12c23885573b22ef32ec1ada5`, stored with its original
CC BY 3.0 license and attribution. Pin the schema and notice by SHA-256.
The verifier reads bounded, duplicate-free local JSON. Schema resolution is
local only: verification never fetches a schema, license, package or image.

Keep the existing image/source binding check. Add a separate verifier for the
full official schema and a selected internal-consistency profile: global element
IDs, local relationships, creation time, described packages, supported checksums,
and reproducible package verification codes. Package verification codes are
optional for analyzed packages under clause 7.9; they are forbidden when
`filesAnalyzed` is false. SHA-1 here reproduces SPDX inventory bookkeeping,
not a secure release signature or authentication of source-file contents.

Run this verifier in the required `spec` CI job, which installs the existing
hash-locked jsonschema environment. Keep the standard-library-only inventory
identity check in `scope-plan`. Exercise malformed records and altered trust
inputs, including missing/changed schema or notices and external references.

Risks and scope: passing a schema cannot establish package completeness,
license permission, vulnerabilities, authentic files, trusted scanner identity,
or a signed release. External document references, snippets and checksum
algorithms outside SHA-1/SHA-256 require a separately reviewed profile. These
are local profile limits, not claims that the SPDX standard forbids them.
F-057 and X-02 remain open until their full license/signing requirements pass.
No tag semantics, human validation requirement or production service changes.
