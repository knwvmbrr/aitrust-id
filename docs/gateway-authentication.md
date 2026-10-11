# Connect the extension to your gateway

The extension authenticates every result before showing a tag. A selected key
proves which gateway signed the bytes. It does not prove tag accuracy, human
authorship, certification or that a command is safe.

## Set up your own key

With Node.js installed, create an owner-only directory **outside the repository**:

```sh
install -d -m 700 "$HOME/aitrust-gateway-keys"
node scripts/gateway-key.cjs keygen "$HOME/aitrust-gateway-keys/private.pem" "$HOME/aitrust-gateway-keys/public.json"
```

Both files are created without overwriting existing files. Keep the private PEM
file secret. Public JSON contains only the key and its SHA-256 fingerprint.
To derive a fresh public JSON copy from an existing key:

```sh
node scripts/gateway-key.cjs public "$HOME/aitrust-gateway-keys/private.pem" "$HOME/aitrust-gateway-keys/public-copy.json"
```

For a gateway running directly as your Linux user, set
`AITRUST_SIGNING_KEY_FILE` to the absolute private PEM path before starting it.
Only P-256, a regular file owned by that process user, and mode 0400 or 0600
are accepted. A bad configured key prevents startup. Missing signing
configuration leaves CLI calls compatible, but authenticated extension requests
return unavailable before any evaluation.

For the non-root container, have its administrator install a separate private
copy outside the repository, owned by UID 10001 with mode 0400. Set
`AITRUST_SIGNING_KEY_FILE` to that host copy and add
`-f deploy/docker-compose.signing.yml` after `-f deploy/docker-compose.yml` in
your existing Compose command. The optional overlay mounts that single key
read-only. It adds no public port, collection endpoint or detector egress.
Do not mount an entire key directory, make the key world-readable, or commit it.

Check the actual container configuration after deployment. Our observed Podman
Compose recreation did not apply `pids_limit: 128`; an administrator restored
128 for each isolated staging service before the unchanged runtime checks passed.
Do not assume that parsed Compose settings are enforced by every engine/version.
The service verifier inspects actual limits and fails when they are missing.
This observation does not establish clean-clone setup on every user's machine.

## Choose the public key and turn checks on

Open extension settings. Choose **Gateway public-key file (JSON)**. Compare the
displayed fingerprint with your gateway operator through a separate trusted
channel. Enter the local gateway token, then enable ChatGPT checks explicitly.
Saving a token or key alone does not enable capture. No account is required.

An unavailable marker means no authenticated valid evaluation was obtained.
Check the token, signing setup and selected fingerprint, then request a new
check. The extension never falls back to displaying an unsigned verdict.

## Rotate or reset

Generate a new key pair at new paths. Restart the gateway under the new private
key. Confirm its new fingerprint independently, then select the new public JSON
in extension settings. Replacement cancels pending checks, removes old tags and
requires fresh evaluations. Reset removes the token, public key and consent
from this browser profile. It does not delete conversations or user-owned files.

## Exact transport contract

Profile: `loopback-response/p256-sha256/v1`. Each request carries one lowercase
64-hex `X-AITrust-Nonce`, generated from 32 random bytes. The signature input is
ASCII `profile + newline + nonce + newline + SHA256(exact request bytes) + newline`
followed by exact UTF-8 response bytes. ECDSA uses P-256/SHA-256; the response
`X-AITrust-Signature` is canonical unpadded base64url of the 64-byte `r || s`
signature. `X-AITrust-Key` is SHA-256 of the uncompressed 65-byte public point.
`X-AITrust-Profile` identifies this profile. Duplicate or malformed nonces fail.

The bounded worker verifies the response before parsing or schema validation.
Wrong key, altered response/request, replayed nonce, missing signature and an
unknown profile cannot reach the verdict UI. Assertion schema v0.1 remains
unchanged; its optional Ed25519 envelope signature is a different contract.
The isolated content script accepts verdicts only from the extension worker's
authenticated-result channel. Host-page messages cannot provide verdicts.

This connection profile is not a global revocation service. A compromised
gateway or trusted key can sign incorrect results. Saved summary/replay exports
are not portable signed receipts: transport authentication is checked in the
current connection and does not establish their independent truth or identity.

Author: Codex. Tag-specific release validation remains separate.
