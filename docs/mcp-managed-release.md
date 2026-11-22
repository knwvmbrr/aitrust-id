# Install a verified MCP connection

This optional local stdio connector runs the PS development pattern checker in a
private offline environment. It does not configure a ChatGPT or Claude account.
The operating HTTPS API is a separate connection. No new server is needed here.

The managed installer requires an eligible current source policy, a protected-main
attestation and fresh installed-tool checks. Source code or an unsigned development
ZIP alone does not qualify. The earlier four-target runtime qualification covers
the developer bundle, not this new managed consumer; use the exact release's
separate operational verification evidence.

## When an eligible release is available

Select a trusted project source checkout and exact source commit yourself. Obtain
its target-specific ZIP, evidence packet, SPDX JSON and detached Sigstore bundle.
Obtain verification trust roots independently with the documented GitHub
attestation tooling; a received archive must not choose its own trust roots.
Use an existing matching CPython 3.12 or 3.13 interpreter and an existing pip
interpreter. Nothing installs into either interpreter or a shared environment.

Create a new empty private directory outside any Git checkout, then run:

```sh
MCP_PRIVATE_DIR="/absolute/path/outside-your-checkout/private-mcp"
mkdir -m 0700 "$MCP_PRIVATE_DIR"
python3 -I -S -B scripts/install-managed-mcp.py \
  --artifact /absolute/path/to/checker.zip \
  --packet /absolute/path/to/evidence.json \
  --spdx /absolute/path/to/artifact.spdx.json \
  --bundle /absolute/path/to/sbom.sigstore.json \
  --trusted-root /absolute/path/to/independently-selected-roots.jsonl \
  --source-commit EXACT_TRUSTED_40_CHARACTER_COMMIT \
  --python /absolute/path/to/matching/python \
  --pip-python /absolute/path/to/existing/pip/python \
  --output "$MCP_PRIVATE_DIR/connection.json"
```

The installer first reconstructs the exact artifact/SPDX and checks current route
permission. It then requires the protected project `artifact-sbom.yml` main-ref
identity and GitHub issuer, exact source digest, subject and predicate. The existing
`gh` verifier must be available. Missing permission, roots, signature or runtime
prerequisites refuse before any SDK installation.

After authorization, it creates a private pip-free environment, installs only
the exact bundled wheels offline, checks the actual interpreter and payloads, and
exercises the two read-only tools and eight fixed synthetic modern/legacy SDK
cases. These checks include canonical PS records and an unavailable optional PII
service that leaves PS usable. No user text is part of these tests. A successful
check does not establish independent detector accuracy or source truth.

Only then is a new 0600 connection JSON published without overwriting anything.
Its `mcpServers` entry can be supplied to a compatible local MCP host, subject to
that host's own configuration and permissions. The developer configuration's
`release_authorized: false` field remains a developer-format fact; the separate
managed install result records this consumer's authorization. Neither field is a
tag verdict or a blanket license-clearance promise.

## Failure and retry

Exit 2 means Unavailable. A prepublication refusal reports
`output_may_exist: false`: no new final connection was created. Private temporary
files or an incomplete installation remain for operator inspection. The managed
consumer does not recursively delete a private stage after failure: pathname
replacement could otherwise delete a different directory.
The managed consumer never deletes a pre-existing output or recursively removes
another workspace.

`output_commit_uncertain` with `output_may_exist: true` means a complete final
connection may already exist. Inspect the requested destination and private
directory before retrying. Do not overwrite, automatically remove, or reuse a
retained `.mcp-managed-*` directory. Error output does not include private paths,
submitted text, configuration contents or raw subprocess errors.

Keep the private `.mcp-managed-*` directory next to the connection file: it holds
the installed environment and the exact authenticated evidence. Moving only the
connection JSON breaks its absolute launch paths. At least 2 GiB plus 128 MiB free
space is required before work begins; the underlying installer rechecks its own
reserve. No `HOME` changes, global package installs or service installation occur.

The first planned managed producer targets Linux x86-64 CPython 3.13. Other
qualified development targets need their own actual protected signatures before
this consumer can authorize them. Whole-project F-057/X-02 obligations and all
unreviewed distribution routes remain open.
