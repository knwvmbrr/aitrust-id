# Notices that travel with the website

The normal site build now prepares its JavaScript notices automatically, before
Vite copies public files. No network access, package install or package execution
is added to preparation. The existing build and development routes retain their
behavior.

The public files are:

- `web-licenses/THIRD-PARTY-NOTICES.txt`: the complete retained text and first-party
  attribution, including an explicitly separated supplemental project notice.
- `web-licenses/packages.json`: all 35 non-development lock entries, archive
  identities, exact notice byte ranges, source bindings and unresolved limits.
- `web-licenses/web-runtime.spdx.json`: the selected npm cohort's SPDX 2.3 metadata.
  Declared licenses come from the locked observations; concluded licenses are
  `NOASSERTION`. This is not a complete website, runtime or build-tool SBOM.

All non-development lock entries are carried, including packages that a build
may tree-shake away. The record does not assert that every one ships or establish
the full bundled dependency graph. License text and attribution preservation are
not a blanket license or source-offer clearance.

## The one exact-release gap

Thirty-four package records have full notice members in their exact recorded npm
archives. `react-remove-scroll-bar@2.3.8` has no matched notice file; its README and
package metadata declare MIT, which is real publisher licensing evidence. The
registry's gitHead was not retrievable from the declared upstream repository.

The shipped notice bundle explicitly carries the separate upstream project's
complete MIT text, pinned to commit
`8ca9ba5ea52de03308fe8ced94f7b159a44d28ff`. That commit's package version is 2.3.7.
The bundle itself identifies this as supplemental project text and says the exact
2.3.8 source/license relationship is **unverified**. It is not silently treated as
an archive member, copied from a neighboring package, or claimed as complete
exact-release fulfillment. The source observation and original 404 are retained
in `sbom/reviews/web-js/react-remove-scroll-bar-2.3.8.json`.

[Upstream pinned license](https://raw.githubusercontent.com/theKashey/react-remove-scroll-bar/8ca9ba5ea52de03308fe8ced94f7b159a44d28ff/LICENSE)
· [Publisher's version metadata](https://registry.npmjs.org/react-remove-scroll-bar/2.3.8).

## Developer checks

```sh
npm run build:site
python3 scripts/web-distribution.py check-built
```

`check-built` reconstructs the expected notice files from the current trusted
repository inputs, compares their actual built bytes and checks the complete
project license carried at `reference/code-license.txt`. A received manifest
cannot approve its own changed notices. To inspect another owned copy of the
same build, use `--artifact-dir /path/to/build`; its path is never printed.
This checks the selected notice assets, not binary build provenance or every
file in the directory.

For an offline replay against already obtained, integrity-addressed archives:

```sh
python3 scripts/web-distribution.py replay-archives --archive-dir /path/to/cache
```

It verifies both npm-lock integrity and the recorded archive SHA-256 for all
35 tarballs, then compares every matched full notice member without extracting
or running package code. The one empty archive-notice observation stays empty;
the supplemental project text is verified separately. Compressed, expanded,
member and total-byte limits apply before unrestricted archive metadata parsing.
Normal preparation does not require these private archives or fetch anything.

```sh
npm run reviewed-release --prefix site
```

This explicit release check first requires the actual carried files, then checks
the existing `web-checker` dependency policy. It currently exits **1** because
other native/build/runtime/source obligations remain unresolved. Normal local
checking, the development preview and unrelated tag routes remain available.
Nothing in this notice repair changes the existing policy flags or permits a
required closed-source or paid dependency.

Preparation validates all source inputs before publishing a fixed three-file
directory. A write or publication failure restores earlier prepared output.
Source mutation before or just after the directory replacement refuses and rolls
back. Staging/old backups are kept outside public assets; a post-publication old
backup cleanup failure is reported explicitly and does not put it in the site.
These are process-level controls, not a filesystem-crash transaction or a promise
of protection from a malicious same-user process.

F-057 and X-02 remain open for their original complete obligations, the other
13 distribution scopes and eligible full artifact SBOM/signature evidence.

The combined16MB logical notice budget now accounts for source inputs, every
retained notice occurrence (even repeated hashes), planned bundle copies and
headers before reading/storing them. Every append also checks remaining capacity
before allocation. This is a byte-processing budget, not a16MB process-memory
claim. The earlier reduced-budget counterexample is retained with the correction.
