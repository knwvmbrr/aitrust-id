# Check where a source download came from

The optional source snapshot packages only a committed public Git tree. It does
not execute files, start Docker or collect your input. Its internal inventory
binds each included file to a hash and the selected commit. The archive is a
**development source snapshot**, not an independently validated tag release.

The protected-main CI job generates a GitHub/Sigstore attestation after the
required engineering checks pass. PRs cannot run that signing job. Each signing
run retains a downloadable `authenticated-development-source` artifact for 30
days. Long-term release storage is not implemented. Before reporting any
particular snapshot authenticated, use its actual signing and verification record.

## Download and verify

Open the repository's [Actions runs](https://github.com/knwvmbrr/aitrust-id/actions/workflows/ci.yml),
choose a main push with a successful `source-provenance` job and download its
`authenticated-development-source` artifact. It contains:

- `aitrust-id-source.tar.gz`: committed source and internal file inventory;
- `source.sigstore.json`: the attestation bundle;
- `trusted-root.jsonl`: the roots obtained by that run, for inspection.

Install the open-source [GitHub CLI](https://cli.github.com/) from its trusted
distribution. While online, obtain the verification roots independently:

```sh
gh attestation trusted-root > trusted-root.jsonl
```

Keep that file separately. Do not accept the download's root file just because
it arrived next to the archive. Confirm the expected source commit through a
trusted repository/run view; the archive's own claim is not your trust decision.
Then, using the trusted copy of this repository's verifier, run:

```sh
python3 scripts/verify-source-provenance.py aitrust-id-source.tar.gz \
  --bundle source.sigstore.json --trusted-root trusted-root.jsonl \
  --commit YOUR_EXPECTED_40_CHARACTER_COMMIT
```

Replace the final placeholder with the exact lowercase commit. It is deliberately
required. The verifier checks the signature, witnessed timestamp, source digest,
main ref and exact `knwvmbrr/aitrust-id/.github/workflows/ci.yml` signing identity.
It rejects self-hosted-runner signatures. It then reads the bounded archive
inventory without extracting or executing anything. Missing prerequisites,
changed bytes or failed checks exit 2. A passing result describes origin/integrity;
it does not install the product or issue a tag.

You can also reproduce the snapshot bytes from that committed repository:

```sh
python3 scripts/build-source-snapshot.py --commit YOUR_EXPECTED_40_CHARACTER_COMMIT \
  --output source-reproduced.tar.gz
```

The builder reads Git objects, ignores working-tree changes and refuses to
overwrite the destination. Repeated builds with the same Python/zlib implementation and source commit
produce identical bytes. Different compression-library versions may encode the
same tar payload differently; a download must match its own attested digest.
This is not a reproducible container/model build.

## Trust and remaining work

Provenance identifies the protected workflow and source used to make these
bytes. A compromised workflow can still sign harmful source. GitHub, its OIDC
identity and Sigstore trust roots remain trust dependencies. Retain the bundle
and separately trusted roots for offline checks. Dependencies installed later,
ignored model assets, runtime container authenticity, vulnerability review and
full redistribution-license clearance remain separate unfinished work.

The source inventory is not an SPDX runtime SBOM. The older Linux inventories
are not attested as GitHub-built images. No safety clearance, authorship proof,
certification, institutional authority or independent tag accuracy is granted.
F-057 and X-02 remain open until their full acceptance passes.

See [architecture and risks](source-provenance-plan.md),
[GitHub's offline verification instructions](https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/verify-attestations-offline)
and [CLI identity policy](https://cli.github.com/manual/gh_attestation_verify).

Local controls: [1,144 passing Python checks on fixed inputs](../runs/2026-10-10-source-provenance-stable-controls.json)
and [actual repeated committed-tree build](../runs/2026-10-10-source-snapshot-reproduction.json).
The [first real attestation](https://github.com/knwvmbrr/aitrust-id/attestations/54693572)
was generated for source `8c21e39dd7fd34b5de0affda193636be7dee9e9d`.
The hosted verifier then refused incompatible CLI flags and withheld its download;
[that failure is preserved](../runs/2026-10-10-source-attestation-hosted-contract-failure.json).
The corrected verifier authenticated the actual signed bytes on
[the Mac](../runs/2026-10-10-source-attestation-real-verification.json) and
[network-isolated Linux](../runs/2026-10-10-source-attestation-offline-linux.json).
[Eight real acceptance/refusal cases](../runs/2026-10-10-source-attestation-real-refusals.json)
include modified bytes/signatures and wrong repository, workflow, source commit
and ref. The saved public bundle and root inventory are in
`provenance/8c21e39dd7fd34b5de0affda193636be7dee9e9d/`. They are evidence of that
historical source, which contains the old verifier; use the corrected trusted
verifier and do not interpret co-delivered roots as automatically trusted.
The corrected hosted job must still execute before offering its new download.
