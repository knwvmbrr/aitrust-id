# Ownership and dependency automation — execution plan

F-152 names four mechanisms. Main protection and required checks operate; add
CODEOWNERS and scheduled Dependabot updates, then observe GitHub accepting and
executing them before completing the whole record. The accountable owner remains
the existing repository owner; a bot or AI assistant is not a human reviewer.

Assign the complete source tree, including its ownership configuration, to the
existing account with write access. Zero approving-review requirements remain
explicit while only one human operates the project. This is accountable routing,
not a claim of independent review or an operating foundation.

Monitor the six active install roots, the three active Dockerfiles and GitHub
Actions. Keep the inactive registry prototype outside the selected deployment.
Use weekly, bounded proposals without auto-merge, private registries, new tokens,
external package execution permissions or a production deployment trigger. The
configuration uses JSON syntax, a subset of YAML, to reject duplicate keys with
the standard-library offline verifier. GitHub acceptance remains a separate check.

Risk: a proposed package or base-image update can invalidate a hashed lock,
model seal, observed SBOM, replay identity or source-bound receipt. That must fail
CI until the maintainer regenerates the relevant artifacts, builds and checks the
changed route, and records actual evidence. The bot does not get a changelog
exception. A proposal failing those prerequisites is held, not silently merged.
A static file does not prove the scheduled service has executed.

Check missing install roots, overrides, duplicate configuration, invalid owners,
unsupported execution privileges, mutable ownership evidence and symlinks using
real temporary files. Add the verifier to existing required scope checks, keeping
all eleven required engineering contexts and the separate release refusals.
Read back CODEOWNERS errors and actual Dependabot update jobs on GitHub after the
configuration reaches main; retain public source IDs and results, not credentials.

References: [GitHub CODEOWNERS](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners),
[Dependabot configuration](https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference).

## Reviewed pin synchronization correction

PR review found a real gap: existence of requirements.lock did not establish
that a Dependabot change to requirements.txt changed the installed dependency.
The selected dependency verifier also omitted the direct manifest. Add a shared
standard-library parser for the bounded pinned forms actually used here. Compare
every direct manifest pin with the hashed lock; services also compare every frozen
build pin and each direct manifest pin with the frozen input. Resolve normalized
package names and the accepted uvicorn standard extra explicitly; unknown extras,
ranges, markers, options, duplicate normalized names and credential-bearing URLs
fail closed. Do not silently treat unsupported forms as unconstrained.

Use the same check in dependency proposal, selected dependency and deployment
boundary verification. Bind the direct/frozen files into the selected inventory.
Reproduce all four real direct-manifest version bumps with their original locks,
then exercise missing pins, frozen drift and URL/extras controls. Keep lock contents
and observed installed-image/SBOM identities unchanged for this enforcement-only
repair. Do not resolve the review thread until the implemented controls pass.
