# Inspect the component notices

The repository now preserves 224 distinct upstream notice texts, with a
content-addressed manifest. Collection inspected the same three Linux amd64
staging images already identified by their SBOMs: 449 installed notice
occurrences. It also inspected 205 artifacts from both complete npm locks,
including platform alternatives not installed on this Mac: 149 notice
occurrences. Repeated texts are stored once; original installed paths or archive
member names remain in the manifest.

From a downloaded checkout, run:

```sh
python3 scripts/verify-redistribution-notices.py
```

This check needs no package installation, account or network. It verifies the
current lock and image-inventory bindings, the collector's bytes, every recorded
notice digest and byte count, unique identities and source stability. Unknown
packages, altered locks, unsafe paths, symlinks, missing notices, unregistered
store entries and unsupported permission claims refuse verification. The output
separates **evidence integrity** from **license clearance**.

The package archives themselves are not committed. For a stronger npm origin
check, download the exact `resolved` URLs recorded in the manifest into a private
archive directory. Each cache filename is SHA-256 of the lock's `integrity`
string, followed by `.tgz`. Then run:

```sh
python3 scripts/verify-redistribution-notices.py --archive-dir /path/to/archives
```

This rechecks every archive against its actual lock integrity and observed
SHA-256, and reproduces the selected notice extraction. Parsing uses the same
verified bytes held in memory; changing a file after the digest check cannot
substitute another archive. Nothing is extracted to disk or executed. The
recorded check reprocessed all 205 actual archives successfully.

```sh
python3 scripts/verify-redistribution-notices.py --require-clearance
```

That command currently exits **1**. The collection does not clear license
obligations. Some platform artifacts contain a license declaration but no file
matching this collector's notice-name profile. That is recorded as an absent
matched file, rather than a claim that the component is proprietary or has no
license. Vendored code, source offers, other assets and architectures need
further review. Native C2PA SDK/transitive notices remain a separate part of
that broader audit. F-057 and X-02 remain open.

A recorded hash proves consistency with the retained observation, not a trusted
scanner identity, legal permission, complete license coverage, security or
independent tag validation. An upstream notice is preserved verbatim; this
project's Apache license does not replace it.

[Notice store and exact inventory](../sbom/notices/manifest.json) ·
[Current identity check](../runs/2026-10-11-license-notices-checkout-bytes.json) ·
[Actual archive extraction check](../runs/2026-10-11-license-archives-checkout-bytes.json)

Checkout preserves original bytes for source, locks and notices, even with Git line-ending conversion enabled. Fifty focused controls include actual synthetic clones with core.autocrlf=true and input. All 224 committed notice blobs were checked against their retained content digests. Only upstream notice formatting is exempt from whitespace cleanup.

The separate [selected asset check](asset-notices.md) now binds self-hosted fonts, frozen Unicode resources and their bundled notice, runtime member observations and the optional model-card declaration. It does not replace this dependency audit or grant broader clearance.
