# iOS runtime notices and bundled preferred source

This source implementation projects the reviewed five-file Pyodide314.0.7 /
CPython3.14.2 cohort into both the App and Share resources. It carries17 Notice
files, including the unchanged project NOTICE, complete selected embedded-runtime
notices, and three physically bundled preferred-source ZIPs. The nine checker
asset hashes, PS method, WebKit asset allowlist and privacy manifest are unchanged.
This is a packaging component, not iOS route admission, signing, AppReview,
compiler reproduction, independent accuracy or an original-requirement closure.

Use the repository's existing Python environment. No SDK, runtime install,
credentials, provisioning-profile contents, network or publisher code is needed
for the source-only command:

```sh
python3 scripts/verify-ios-runtime-obligations.py
```

To write the17 public Notice resources, choose a **new** directory beneath an
existing owner-private0700 parent outside every Git checkout:

```sh
python3 scripts/verify-ios-runtime-obligations.py --prepare /absolute/private-parent/new-notices
```

The operation never overwrites a destination. Files are0600; directories0700.
A failed operation may retain private output. The fixed uncertainty warning means
inspect that output before trying another destination; no recursive cleanup is
attempted. The helper requires2GiB free space plus128MiB allowance before writes.
On macOS supply the canonical OS path (for example `/private/var/...`); no-follow
ancestry deliberately refuses arbitrary directory symlinks.

For already materialized App/Share resource directories:

```sh
python3 scripts/verify-ios-runtime-obligations.py --app /absolute/AITrustID.app --share /absolute/AITrustID.app/PlugIns/AITrustIDShare.appex
```

For an explicitly selected received IPA:

```sh
python3 scripts/verify-ios-runtime-obligations.py --ipa /absolute/received.ipa
```

The received check streams both five-runtime copies, all17 Notice files and
AppLicense against trusted source-derived bytes:23 selected files per target,
46 total. It refuses missing, changed or coherently rebound carrying. It does
**not** extract an IPA, read provisioning contents, inspect every executable,
check a signature or approve unclassified package bytes. A received mutable
index is never an authority. The earlier signed Nov18 artifact is expected to
refuse this new complete carrying contract; it is preserved unchanged.

The IPA path has a64MiB whole-artifact bound. Before constructing ZipFile it
checks the EOCD and a262144-byte maximum central directory, at most256 entries,
no ZIP64/multidisk/links/encryption/noncanonical names,128MiB expanded declarations,
selected member at most12MiB and compression ratio at most512. Selected members
are streamed in at most65536-byte chunks and CRC/hash checked. One60-second
whole-operation deadline covers source generation, I/O, rechecks and final close.
The160 logical-call/64,000,000 logical-byte cap counts source capture and every
decoded selected-member byte; stream chunks count bytes, not separate calls.
Separate physical limits cover two64MiB whole-hash passes and at most64MiB
selected compressed bodies, plus the explicitly bounded ZIP headers. These
physical rereads are not silently described as64MB total I/O. The128MB logical
payload reservation is a conservative allocation contract, not measured RSS.

## Native access

The generated project copies the same Notices folder into both targets using
the existing resource phase. Privacy & open-source notices is available in both
checker modes. Existing text entries remain paginated at3000 characters; new
entries cover repository attribution, complete selected runtime notices and the
local source guide. Opening the index does not load document text.

Three explicit source actions offer **only** a fixed bundled public ZIP through
UIKit's share sheet after its exact size/SHA verification. Selected text, checker
result and original Share items are never activity items. Nothing is uploaded or
saved automatically. Cancelling source sharing does not initiate a check. ZIP
paths are not added to the JavaScript scheme or WebKit navigation allowlist.
The unchanged repository NOTICE includes font/schema attribution as repository
context; those components are not added to this PS-only native cohort.

Fresh compiled App/Share UI, source-export cancellation, signature and simulator
acceptance require the separate native qualification. Source fixtures do not
establish compiled UI behavior, physical-device accessibility, Apple review or
release approval. The seven named UI workflows retain the six original checks
and add an explicit source-export/cancel case; no native run is claimed here.

Architecture and complete mapping: [plan](ios-runtime-obligations-plan.md).
Underlying grants/preferred sources remain exactly those in
`sbom/web-runtime/manifest.json`; this projection does not reinterpret them or
cover unrelated native SDK/model distribution rights.
