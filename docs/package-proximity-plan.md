# Package-name proximity — architecture and acceptance

Implementer: Codex. Scope: F-013. This is an offline observation component,
separate from the existing PS detector and release gate.

The supplied input is one package name per line, with an explicitly selected
ecosystem. A versioned snapshot supplies a contiguous ranked top-N list, its
measurement description, observation interval, source URL and source-byte hash.
The importer preserves the original source bytes by hash and normalizes names
according to the selected ecosystem. It never fetches, installs or executes a
package. A synthetic fixture cannot present itself as a production ranking.

The observation reports Levenshtein distance 1–2 from the supplied top-N list.
Exact canonical matches do not produce a proximity finding. npm scope names
remain part of the comparison: `@one/name` and `@two/name` are distinct. PyPI
case and runs of `-`, `_`, `.` use the published name-normalization rule.
Offsets refer to the original, explicitly supplied package-name input.

Risks: a similar name can be legitimate; a malicious name can be dissimilar;
an old or fabricated ranking can mislead. Hashes establish byte integrity, not
ranking truth or freshness. Results therefore declare their reference identity,
measurement interval, unverified ranking/freshness and no maliciousness verdict.
No PS assertion, calibrated confidence, package safety claim or automatic
download is permitted. Unsupported names and corrupt manifests fail explicitly.

Acceptance checks cover independent edit-distance oracles, canonical equality,
scope boundaries, deterministic ordering, Unicode/invalid-name refusal, duplicate
JSON keys, altered/rehashed manifests, limits, private input/output controls,
actual CLI execution, and an actual network-isolated Linux run. Promotion into
PS requires a separate use/mention contract and independent held-out measurement.
F-013 remains open until that full enhancement acceptance is available.

Sources checked 2026-10-11:
[PyPA names and normalization](https://packaging.python.org/en/latest/specifications/name-normalization/),
[npm package.json](https://docs.npmjs.com/cli/configuring-npm/package-json/),
[npm scopes](https://docs.npmjs.com/about-scopes/).
