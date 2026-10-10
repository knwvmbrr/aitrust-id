# Open dependency audit — architecture before implementation

X-02 prohibits a closed-source or paid dependency in the personal processing
pipeline. Artifact pinning alone did not establish licenses. F-057 additionally
requires an SBOM and Sigstore release signatures; neither follows from an Apache
license on this repository.

Inventory all selected runtime images and install roots, model/runtime/font/data
assets and the build/verification tools. Preserve upstream license notices. Use
an open-source SBOM tool pinned to a verified release artifact to inspect the
actual Linux images, including OS packages and installed Python distributions.
Bind the inventories to immutable image identities and current source/lock hashes.
Inventory both npm locks, including optional platform packages, rather than only
the subset installed on this Mac. Declared license metadata is evidence to review,
not an automatic legal clearance. Missing or ambiguous licenses stay unresolved.

Create a versioned reviewed license policy with specific source/artifact evidence.
The offline verifier rejects unknown packages, changed locks/artifacts, unreviewed
license expressions, unresolved entries and conflicting active routes. Test missing
and proprietary license cases and preserve notices for redistribution. Distinguish
required processing dependencies from optional commercial hosting and owner-chosen
OS/browser applications. Demonstrate the open-source Linux/Chromium route; never
assert that commercial hosting itself is open source.

Generate inspectable SBOMs and an outside-user verification path. Sigstore requires
actual identity-based signing and transparency evidence: do not substitute a local
self-signed key, set a pass flag from documentation, or claim the unexecuted hosted
CI is working. If the account's CI restriction prevents signing, F-057 stays open.
No production credential, key, user content or private host address enters reports.

Risks: a scanner can miss vendored code, embedded runtimes and license obligations.
Supplement it with asset/source notices and explicit coverage limits. Open-source
licenses still impose conditions. This engineering boundary review does not replace
qualified legal advice, vulnerability review or independent tag validation. Future
routes and dependency changes reopen acceptance; fail closed pending review rather
than inventing a permission or silently narrowing the product's retained scope.
