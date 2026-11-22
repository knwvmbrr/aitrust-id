# Durable PS source provenance downloads — before implementation

Base and signed source: `cd3beab02774fa939e3a2bd8a0d87913d9e8fd81`, actual protected
run44992617061. Preserve the actual subject ZIP, SPDX predicate, raw binding packet,
Sigstore bundle and separate verification observation byte-for-byte. Publish them
under one immutable commit-specific directory in site/public/downloads/provenance.
No GitHub account or expiring Actions artifact should be needed to retrieve them.

Never edit the original packet's false/unverified fields or the packet-bound
existing distribution guide. A new separate guide distinguishes those preparation
fields, an unsigned past verification observation, and the user's own detached
verification. The user independently selects a trusted repository/commit/signer
and obtains trusted roots independently, not from the downloaded artifact set.
Keep personal source operation and licence/accuracy claims separate.

Validate exact hashes against the actual protected files, packet/SPDX/ZIP/bundle
relationships, private-path/credential absence and actual account-free detached
verification in a temporary empty GitHub configuration. No credentials, new
package install, model, endpoint, production change or deployment. Failure to
verify cannot become a safe/clear result. Historical proof and all broader
F057/X02 obligations remain unchanged. PM integrates/publicly delivers later.
