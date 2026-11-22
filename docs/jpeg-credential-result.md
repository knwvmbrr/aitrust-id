# JPEG credential/action CLI · selected Linux result

This development component now works in the selected Linux qualification. It is
independent of PNG, PS, MT, the browser app and the remote gateway. It issues no
FA/PA tag and does not close their original requirements.

Executed source: `194a095752452d21465a628a69aeb6b6bb7fd01c`.
[Actual hosted qualification](https://github.com/knwvmbrr/aitrust-id/actions/runs/45041728639)
passed on Ubuntu24.04 x86_64 / CPython3.13.18 using the existing exact ten-package
lock, c2pa-python0.38.0 and native SDK0.91.0. No model or new dependency version
was introduced; nothing was installed locally. macOS native JPEG execution was
not assessed.

From that checkout, use a private environment and a deliberately selected local
JPEG. The existing guide describes its bounds and privacy choices:

```sh
python3 -m venv /your/private/jpeg-reader
/your/private/jpeg-reader/bin/python -m pip install --require-hashes -r eval/c2pa-inspection.lock
/your/private/jpeg-reader/bin/python -I -B scripts/inspect-jpeg-provenance.py --image /your/local/photo.jpg
```

Add `--json` only when you want a linkable encoded-file fingerprint and software
identity record. Default text contains no filename, path, creator, GPS, raw
metadata or hash. There is no automatic save/upload and no raw-report export.

The actual run passed20 focused safety groups and14 qualification cases:
four complete bounded projections compared with an independently called pinned
reader (creation, edit, ordinary, altered), four private-text cases, per-call
public-root trust/context isolation, unsigned/refusal cases, missing SDK with
actual PS survival, and fresh-worker recovery. “Four projections” means the
complete public fixed observation, not a dump or independent semantic review of
the private native report. Synthetic test declarations are not AI-origin ground
truth; no accuracy, authorship, authenticity or content-truth claim follows.

The altered image retained a matching record signature but mismatched image
binding and no accepted action declaration. The synthetic public root established
trust in that one context; the next default invocation was untrusted. Revocation
remained unknown throughout. No overall “Valid” result was issued.

The actual process had a distinct network namespace, no effective capabilities,
no supplementary groups and no-new-privileges. Both selected outbound connection
probes refused. Settings disabled remote-manifest and OCSP fetches and used an
empty network-host allowlist. This is not a universal native sandbox or a proof
about every possible SDK syscall. Temporary synthetic images and the owned SDK
environment were removed; ephemeral private keys were never written.

Three failed candidates are preserved. The first used an unsuitable nonroot
init-namespace read; the second failed before its broad signing step completed
and had a late native-execution marker (explicitly qualified as unknown); the
third diagnostic located an edit fixture missing its required inception. The
corrected fixture uses a software-created inception followed by editing and
explicit current-claim attribution. The reader, signature/content/action rules,
SDK pin, budgets and14 acceptance cases were not weakened to obtain success.

Exact receipts are in `runs/2026-11-22-jpeg-native-linux-actual.json` and
`runs/2026-11-22-jpeg-credential-component-assembled.json`. The latter binds the
execution commit, retained artifact,17 before/after/current source hashes,
installed versions and cleanup observations. Result prose is written after that
source-frozen execution; it is not relabeled as an execution input.
