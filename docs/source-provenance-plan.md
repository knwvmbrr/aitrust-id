# Source provenance implementation plan

Owner: Michael. Implementation: Codex. Direction: preserve all 202 requirements,
continue to 25 open full jobs, protect users and publish reviewable source.

## Boundary and intended outcome

Produce a deterministic development source snapshot from a specified committed
Git tree, including its file inventory. Only regular public tracked files enter
it; untracked files, ignored assets, history, links, submodules, private key paths
and local credentials refuse or remain excluded. Verification never extracts or
executes downloaded code. Size/count/path limits apply before parsing. This
makes a downloadable snapshot independently checkable without Docker.

A job in the existing CI workflow runs only on this repository's protected main
push after all eleven required engineering contexts succeed. Its own token has
contents read, attestations write and OIDC signing permissions. Other jobs and
all PR executions retain contents read. Pin every action used by the privileged
job to an observed official commit; do not execute artifact-supplied scripts.

Attest the exact source archive with the official GitHub/Sigstore action. This
job does not sign the earlier remote container images or attach their inventories
as if they described the archive. Keep independent tag release gates separate:
the artifact is explicitly a development snapshot, not a validated tag release.

The independent verifier uses GitHub CLI's cryptographic verifier with an
explicit saved bundle and separately obtained trusted root. Require the exact
repository, workflow, protected main ref and an expected source commit supplied
by the user. Reject wrong identities/digests, missing trust inputs or failed
verification. Check the signed archive's bounded inventory after authentication.
Save the bundle/root alongside the download for offline verification. The root
must be obtained from a trusted channel, never accepted from the archive itself.

## Risks and acceptance

Runner or protected source compromise can produce signed malicious source;
provenance is origin evidence, not code safety. GitHub and Sigstore remain trust
dependencies. Tokens stay job-local and are never committed. A pathname filter
is not a general secret scanner. Source confidentiality is the publication audit's
responsibility. Dependencies/models installed later are outside this snapshot.

Exercise deterministic repeat builds, dirty/untracked exclusion, changed source,
link/private-path refusal, traversal/duplicate/oversized archives, corrupted bytes,
wrong commit, wrong repo/workflow and missing bundle/root. Run real hosted signing
and real cryptographic acceptance/refusals before reporting operation; fake verifier
outputs are only local policy tests. Execute offline verification on network-isolated
Linux. Record checks, limitations, state and changelog through protected PRs.

F-057 and X-02 remain open until their full license, inventory, scanner and release
acceptance passes. RFCs, legal authority and tag accuracy are not adopted here.

Primary references: [GitHub provenance signing](https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations),
[offline verification](https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/verify-attestations-offline),
[CLI identity and source verification](https://cli.github.com/manual/gh_attestation_verify).
