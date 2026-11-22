# Verify the signed PS source download

These versioned files preserve the actual PS source package and SPDX/Sigstore
companions from protected run44992617061. Downloading them needs no GitHub
account. They remain useful after the Actions artifact expires. This is source
integrity and signer verification, not independent detector accuracy or general
licence clearance.

## Select trust first

Before using these commands, independently decide whether you trust repository
`knwvmbrr/aitrust-id`, source commit
`cd3beab02774fa939e3a2bd8a0d87913d9e8fd81`, and its protected-main signing workflow
`.github/workflows/artifact-sbom.yml`. Review the
[public commit](https://github.com/knwvmbrr/aitrust-id/commit/cd3beab02774fa939e3a2bd8a0d87913d9e8fd81)
through a trusted channel. A downloaded manifest, checksum or previous success
observation cannot choose a trusted repository, commit or root key for you.

Use existing Python3.12+, Git and the official GitHub CLI on macOS/Linux. The recipe installs no
project packages or models. Bring the listed tools; they are not bundled. A
GitHub account is not required. Obtain the full verification source at your
independently selected commit; a public Git checkout needs no GitHub account:

```sh
trusted_commit=cd3beab02774fa939e3a2bd8a0d87913d9e8fd81
git clone --no-checkout https://github.com/knwvmbrr/aitrust-id.git aitrust-verification-source
git -C aitrust-verification-source checkout --detach "$trusted_commit"
git -C aitrust-verification-source rev-parse HEAD
```

Confirm the displayed full commit matches your selection. The small PS ZIP alone
does not include the complete artifact verification tools.

## Download the fixed version

Use a new owner-private folder outside every Git checkout. This command creates
one and resolves macOS temporary-directory symlinks. Each output name is new.

```sh
proof_dir="$(python3 -c 'import tempfile;from pathlib import Path;print(Path(tempfile.mkdtemp(prefix="aitrust-ps-provenance-")).resolve())')"
base=https://aitrustid.com/downloads/provenance/cd3beab02774fa939e3a2bd8a0d87913d9e8fd81
for file in checker.zip evidence.json artifact.spdx.json sbom.sigstore.json verified-observation.json manifest.json; do
  curl --fail --location --proto '=https' --tlsv1.2 "$base/$file" --output "$proof_dir/$file"
done
```

The expected ZIP SHA256 is
`1720be1015f7ab1e295de97dbc503723b486209b2f7dc09e2ebd6130c6fb42d1`.
Checksums identify bytes and help detect handling errors; they are not a substitute
for the independently selected signer and cryptographic verification below.
These public files contain source and provenance, not submitted checker text.

## Obtain roots independently and verify

Obtain trusted roots through the official CLI or your independently approved
trust process. The versioned download deliberately supplies no root file:

```sh
gh attestation trusted-root > "$proof_dir/independently-selected-trusted-root.jsonl"
chmod 0600 "$proof_dir/independently-selected-trusted-root.jsonl"
```

Do not replace that step with a root chosen by the downloaded artifact. The
[official CLI options](https://cli.github.com/manual/gh_attestation_verify)
explain bundle, root and exact signer/source verification. These commands can
run without GitHub login; the root retrieval uses ordinary network access.

From the selected source checkout, run:

```sh
cd aitrust-verification-source
python3 -I -S -B scripts/distribution-artifact.py verify-attestation --route ps-source --artifact "$proof_dir/checker.zip" --commit "$trusted_commit" --packet "$proof_dir/evidence.json" --sbom "$proof_dir/artifact.spdx.json" --bundle "$proof_dir/sbom.sigstore.json" --trusted-root "$proof_dir/independently-selected-trusted-root.jsonl" --output "$proof_dir/verified-now.json"
```

The verifier requires the exact protected-main workflow identity, GitHub OIDC
issuer, source commit/ref, hosted-runner policy, subject hash and complete SPDX
predicate. It also reconstructs the binding packet from the selected source and
checks the canonical PS ZIP. A successful verification reports `VERIFIED` and
`attestation_verified:true`; verify-only leaves `release_authorized:false`.
A refusal is Unavailable, never safe, cleared or a partially accepted signature.
No existing output is overwritten. An uncertain output commit requires inspecting
the requested destination and private directory before retrying.

## Read the files correctly

- `checker.zip` is the actual131,039-byte source package, not an interpreter.
- `artifact.spdx.json` is the exact signed SPDX predicate.
- `sbom.sigstore.json` carries the actual signature/certificate/transparency data.
- `evidence.json` is the original preparation packet. Its
  `attestation_verified:false` and `release_authorized:false` are intentionally
  unchanged; later verification did not rewrite its captured state.
- `verified-observation.json` preserves an earlier successful managed-policy
  verification. It is an unsigned observation, not a trust anchor or replacement
  for your own verification. Its recorded root fingerprint does not select roots.
- `manifest.json` identifies these fixed bytes; it is not separately signed.

This proves neither independent PS accuracy, all-project licence permission nor
any other platform artifact. The source-only PS policy remains separate from the
thirteen unapproved distribution scopes. No participant data, account, training,
research forwarding or operating certification is introduced. A repository copy of this guide does not prove that a host currently serves the
files. Check the live responses and exact bytes when downloading.
