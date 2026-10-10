# Keep a receipt. Verify it without us.

This optional development tool binds your text file to your editing summary and
signs that record with your own key. It is free, open source and runs offline.
It does **not** prove human authorship or issue PA, FA, IV or a certification.
You can keep using every personal checker without creating a receipt.

Requires Node 24 and an owner-controlled Unix-like computer. Start with the
[offline editor](composition-observations.md), write test text, Pause, then
Download this summary. Choose Download your text to save the exact editor value as a UTF-8 `.txt` file
with no added newline. Its hash is in the summary; issuance refuses different bytes.
The summary excludes your words, raw timings and key names.

Create a private directory **outside** the downloaded repository:

```sh
mkdir -m 700 "$HOME/aitrust-receipts"
node scripts/receipt.cjs keygen Ed25519 "$HOME/aitrust-receipts/private.pem" "$HOME/aitrust-receipts/public.pem"
node scripts/receipt.cjs issue "$HOME/aitrust-receipts/artifact.txt" "$HOME/aitrust-receipts/observation.json" "$HOME/aitrust-receipts/private.pem" "$HOME/aitrust-receipts/receipt.json"
node scripts/receipt.cjs verify "$HOME/aitrust-receipts/receipt.json" "$HOME/aitrust-receipts/public.pem" "$HOME/aitrust-receipts/artifact.txt"
```

Use your actual file paths. Never publish `private.pem` or send it to us. Private
keys must have owner-only permissions (0600); generation refuses to overwrite a
file or follow a symlink. Keep backups privately. Friendly recovery and automatic
key replacement are not implemented. The key identifies a cryptographic key,
not a legally identified person. Establish a trusted public-key fingerprint with
the other party through your chosen channel; an embedded key is never trusted.

The result separates these facts:

- **Record integrity:** the signature matches the public key you selected.
- **Artifact binding:** the supplied file matches the signed hash and length.
- **Expiry:** within, before or after the declared local-clock window.
- **Revocation:** unchecked. No transparency log or fresh status evidence exists.
- **Authorship:** unestablished. Invented events can be signed too.

`certified_valid` always remains false. An expired receipt can still have an
intact signature; the CLI exits 3 when outside its declared window. Invalid
records, keys, artifacts, permissions or prerequisites exit 2. Success verifies
only those bounded facts. No network or provider contact occurs.

## Format and algorithms

`offline-receipt/1.0.0` contains the exact artifact SHA-256 and byte count, the
versioned observation record, issue/expiry times, and these mandatory boundaries:
`forgery_cost_class: unvalidated`, `signature_proves: record_integrity_only`,
`authorship_proven: false`, `independent_timestamp: false`,
`revocation_status: unchecked`, `tag_issuance: false`.

`detached-record/1.0.0` binds canonical payload bytes, algorithm and key
fingerprint. Canonicalization is this profile's sorted UTF-16-key JSON encoding
using ECMAScript finite-number serialization; no normalization of strings. It
does not claim an independently certified canonicalization implementation.
Duplicate keys, unsafe integers, invalid Unicode, noncanonical signed payloads,
unknown fields, excessive size/nesting and unrecognized algorithms fail closed.

Supported algorithms: **Ed25519** and **ECDSA P-256 with SHA-256**, using Node's
built-in cryptography. P-256 signatures use 64-byte IEEE P1363 encoding. Changing
algorithm requires an explicit profile/key selection; no silent downgrade. Both
profiles have executed tamper and mismatched-key tests. This is algorithm
dispatch and expiry handling, not a claim of post-quantum or permanent safety.
The default receipt lifetime is one day; permitted lifetime is 60 seconds to
seven days. Neither issuer nor verifier clock is an independent timestamp.

## Detached assertion integrity

The same signature profile optionally wraps an existing assertion:

```sh
node scripts/receipt.cjs sign-assertion assertion.json "$HOME/aitrust-receipts/private.pem" signed-assertion.json
node scripts/receipt.cjs verify-assertion signed-assertion.json "$HOME/aitrust-receipts/public.pem"
```

Both operations require the project's Python schema validator and hash-locked
gateway/evaluation dependencies. Set `AITRUST_VERIFY_PYTHON` to that environment's
Python. UUID/date-time checks are mandatory; missing prerequisites refuse the
operation. Signature validation occurs before schema acceptance. Existing
gateway/extension assertions are unchanged and **not automatically signed**.
Signature-before-badge-render (F-036) remains open.

Run `node --test tests/offline-receipts.cjs` with the schema environment configured.
The suite generates and deletes disposable synthetic keys. No production signing
key or real composition data is created by the verification suite.

RFC-0002 remains unadopted as a standard. Independent RFC 3161 timestamping,
revocation transparency, offline freshness, institutional anti-coercion
conformance, non-technical key recovery, group receipts and PA/FA/IV validation
remain separate unfinished requirements. No foundation, certifier or public
authorship registry is operating.
