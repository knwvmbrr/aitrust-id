# Check a package spelling, offline

This tool compares explicitly supplied package names with your selected ranked
reference. It finds names one or two character edits away from a reference name.
It does not install packages or say a similar name is malicious.

Use Python 3.12 from a downloaded source checkout. No service or account is needed.
Prepare a JSON source with this shape; the following is **synthetic**, not a real
download ranking:

```json
{
  "format": "ranked-package-input/v1",
  "ecosystem": "pypi",
  "measurement": {
    "start": "2026-09-01T00:00:00Z",
    "end": "2026-10-01T00:00:00Z",
    "metric": "download_count_in_interval",
    "source_url": "https://example.invalid/synthetic-ranking",
    "synthetic": true
  },
  "packages": [{"rank": 1, "name": "requests", "downloads": 100}]
}
```

For a real ranking, preserve its source URL, measurement interval, download counts
and ranked order. The importer checks contiguous ranks and nonincreasing counts,
and binds the original file bytes by SHA-256. This does not establish that the
provider's counts are true or that the ranking is fresh. Synthetic input retains
its synthetic label in every observation. All supplied snapshots stay outside Git.

Create a private directory and import the source:

```sh
install -d -m 700 "$HOME/aitrust-package-references"
python3 scripts/package-proximity.py import \
  --source /path/to/ranked-packages.json \
  --output "$HOME/aitrust-package-references/pypi-snapshot.json"
```

Put one bare package name per line into a private input file. Check it:

```sh
python3 scripts/package-proximity.py check \
  --snapshot "$HOME/aitrust-package-references/pypi-snapshot.json" \
  < /path/to/package-names.txt
```

`SIMILAR_NAME` supplies the signal ID, input positions, reference name/rank and
edit distance. `NO_SIMILAR_NAME` means none matched this particular top-N snapshot;
it is not a package safety check. `UNAVAILABLE` means the input/reference was
invalid or unsupported. The process exits 2 for unavailable, 0 for a completed
observation. Nothing is downloaded, installed or submitted.

`--top-n N` selects a prefix of the supplied ranking. Exact canonical matches
are counted separately without a proximity finding. PyPI normalization follows
the [published PyPA rule](https://packaging.python.org/en/latest/specifications/name-normalization/).
npm uses a documented conservative ASCII subset of
[npm package names](https://docs.npmjs.com/cli/configuring-npm/package-json/);
[scopes](https://docs.npmjs.com/about-scopes/) remain part of the identity.
Unsupported names are refused; they are not silently converted to another name.

Limits: 2,048 ranked references, 16 input lines, 4,096 input characters, 128
characters per name and 32 returned findings. Distance is Levenshtein insertion,
deletion and substitution; swapping adjacent letters normally costs two edits.
The file hash detects changes to a saved snapshot. It does not authenticate the
ranking provider. Output contains reference metadata, positions and a subject
hash, which can correlate guesses of a short package list. Review before sharing.

This implements the separately testable F-013 component. Its PS enhancement
integration and independent accuracy gate remain open. The live PS detector is
unchanged. Run its controls with `python3 -m pytest tests/test_package_proximity.py -q`.
