# Inspect native dependency evidence

A package's license label does not explain every library inside its compiled
binary. This inventory makes those review inputs visible without running them.
It covers both complete npm locks, including platform alternatives that are not
installed on this computer.

Run the offline consistency check from the downloaded repository:

```sh
python3 scripts/verify-native-dependencies.py
```

The current observation covers 205 artifacts, 146 native-format or
executable-name candidates, 54 upstream README licensing declarations and 14
bundled-version lists. Candidates include script wrappers and unclassified
formats; the count is not a claim that all are native binaries. Original
licensing text and version declarations remain unchanged in a content-addressed
store. Existing full license notices remain in the separate notice inventory.

For an archive replay, use the already downloaded exact lock artifacts:

```sh
python3 scripts/verify-native-dependencies.py --archive-dir /path/to/locked-archives
```

Cache filenames follow the existing [notice-cache convention](dependency-notices.md).
Replay verifies each captured archive against its lock integrity and observed
SHA-256, then reproduces candidate hashes, declarations and nested-archive
identities from those same bytes. It installs, extracts and executes nothing.
Binary hashes cannot be substantiated without the archive bytes: the ordinary
offline check explicitly reports `binary_bytes_replayed: false`. Neither mode
authenticates the publisher or grants legal permission. Use the separate signed
source verification path for download authentication.

The entire 205-artifact replay has executed successfully. Thirty-two focused
checks cover actual committed-inventory verification, malformed archives,
unsafe/link/duplicate members, changed declarations, missing artifact coverage,
size limits and attempted permission/accuracy promotion. The initial scan
refused three workerd build binaries larger than 128 MiB. Only their exact
locked archive hashes and member names receive their observed size limits;
other members keep the original limit.

One nested archive, Pyodide's `python_stdlib.zip`, remains uninspected by this
scanner. Version lists and README tables are upstream declarations, not complete
source/relinking evidence or a substitute for full license terms. Native static
linkage, embedded code, model permissions, source-offer obligations and the
remaining runtime review stay open. `permission_cleared` and
`complete_transitive_coverage` remain false. F-057 and X-02 remain open.

Maintainers creating a new observation must explicitly identify the operator:

```sh
python3 scripts/verify-native-dependencies.py --collect --observer YOUR_NAME --archive-dir /path/to/locked-archives
```

Collection refuses an existing `sbom/native` directory. Preserve the prior
snapshot and review any replacement separately. Operator attribution is a
self-declared record, not an authenticated identity. A partial collection never
passes verification merely because files were written.

[Current inventory](https://github.com/knwvmbrr/aitrust-id/blob/main/sbom/native/manifest.json) ·
[Actual archive replay](https://github.com/knwvmbrr/aitrust-id/blob/main/runs/2026-10-15-native-archive-replay.json).
Upstream context: [Sharp's platform binaries](https://sharp.pixelplumbing.com/install/)
and [Pyodide's versioned license](https://github.com/pyodide/pyodide/blob/314.0.7/LICENSE).
