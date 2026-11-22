# JPEG credential details · development CLI

This optional local reader checks attached Content Credentials and two bounded
recorded-action declarations. It uploads nothing and does not issue FA, PA or
another tag. It cannot determine whether an image is AI-generated, authentic,
true or complete. PNG and text tools do not depend on it.

Use Python 3.13 on Linux x86_64 or macOS arm64 and an isolated environment with
the repository's existing `eval/c2pa-inspection.lock` (c2pa-python 0.38.0, native
SDK 0.91.0). The lock hashes and installed wrapper/native bytes are checked;
other versions refuse. No model, account, key, GPU or server is needed.

```sh
python3 -m venv /your/private/jpeg-reader
/your/private/jpeg-reader/bin/python -m pip install --require-hashes -r eval/c2pa-inspection.lock
/your/private/jpeg-reader/bin/python -I -B scripts/inspect-jpeg-provenance.py --image /your/local/photo.jpg
```

Choose a real regular file with no symlink ancestors. The default output omits
names, paths, URLs, creator data, raw metadata and hashes. The original image
may still contain identifying information. Nothing is automatically saved.
The reader is limited to 10 MiB encoded files, 4 million header pixels and the
reviewed baseline 8-bit single-scan JPEG framing subset. Progressive/multiscan
and other valid unsupported encodings are unavailable, not corrupt or malicious.
Pixels and entropy values are not decoded or authenticated by this preflight.

An explicit `--json` includes the **encoded-file** SHA-256 and byte count,
implementation/SDK hashes, fixed observations and optional public-root hash.
Those hashes can link copies; share only deliberately. This encoded identity is
not the reserved decoded-image subject identity. JSON never exports embedded
metadata, certificates, report URLs or arbitrary assertion strings.

The output separates:

- Image binding to the recorded bytes.
- Cryptographic record signature.
- Signer trust within this invocation's SDK context.
- Revocation, which remains unknown when online checks are disabled.
- Bound active-manifest declarations of generative creation or editing.

No overall “Valid” or origin verdict is produced. Signature matching alone does
not establish image binding or signer trust. A signed declaration remains the
producer's statement, not independent proof of AI use, human intervention or a
complete history. Unknown, regional/template/related or unbound actions do not
become declarations. An absent credential does not imply a human-created image.

For a deliberate local trust context, add `--trust-anchors /your/public-roots.pem`.
Only up to four public CA certificates, totaling 64 KiB, are accepted. Private
keys and URLs refuse. This does not install roots or modify the SDK trust store;
trust applies to that one reader invocation. It does not establish institutional
endorsement, authorship, copyright, provenance completeness or content truth.
Native qualification must demonstrate this exact versioned behavior before it
is called supported. Without that proof this option is a candidate only.

Remote manifests and OCSP fetching are disabled; the native allowlist is empty.
No URL or local filename is supplied to the reader, only captured JPEG bytes.
An attached manifest can still contain identifying metadata, which this CLI
filters out. One fresh owned child per call has an 8-second CPU limit, 12-second
worker budget, 4 MiB report cap and Linux 1 GiB address-space cap. Kill/reap cleanup
may take a further five seconds. These limits are not a complete native sandbox;
for hostile files use the demonstrated non-root Linux network namespace.

The disposable qualification workflow signs only synthetic test JPEGs, never
writes the ephemeral private keys, and runs actual reads without a network
namespace route. Its engineering cases are not an accuracy study or user-origin
corpus. Missing SDK, malformed files and worker errors affect only this CLI.
Remove the private environment to remove the optional dependency; the repository
and original image remain unchanged.

Sources: [C2PA content binding](https://spec.c2pa.org/specifications/specifications/2.5/specs/C2PA_Specification.html#_binding_to_content),
[C2PA trust model](https://spec.c2pa.org/specifications/specifications/2.5/specs/C2PA_Specification.html#_trust_model),
[IPTC generative editing declaration](https://cv.iptc.org/newscodes/digitalsourcetype/compositeWithTrainedAlgorithmicMedia).
These are reference meanings, not a claim that every current specification
feature is implemented by this pinned SDK profile. Project LICENSE and NOTICE
apply; existing SDK/cohort notices and source obligations remain separate.
