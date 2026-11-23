# Use the verified local MCP connector

The [Linux CPython 3.13 engineering preview](https://github.com/knwvmbrr/aitrust-id/releases/tag/mcp-linux-cp313-2026-11-23-7986680c) is downloadable without a GitHub account. It provides two read-only tools: **list_tags** and **check_text**. PS checks selected text for supported command patterns; it never runs those commands. A finding is a reason to inspect the command, and no finding is not a safety clearance.

## Get started

1. Use Linux x86-64 with glibc 2.34 or newer, normal GIL-enabled 64-bit CPython 3.13, existing pip 22.3+ and GitHub CLI. This managed package does not support macOS, Windows, phones or free-threaded Python. Keep at least 2 GiB plus 128 MiB free.
2. Download the six named release assets. Select and inspect trusted project source at **7986680cdf9edda736a488d7fa0a26d04d5290b1**. The release lists every file's size and SHA-256.
3. Follow the [installation instructions for that exact source](https://github.com/knwvmbrr/aitrust-id/blob/7986680cdf9edda736a488d7fa0a26d04d5290b1/docs/mcp-managed-release.md). Obtain trust roots independently with `gh attestation trusted-root`. The roots carried with the release are producer evidence; they must not choose your trust for you. Give the installer all artifact/evidence files and the exact source commit, and choose a new private output outside Git.
4. After successful verification, add the generated **connection.json** to a compatible local MCP host. Keep the adjacent private installed directory and allow only the two read-only tools. Start with invented text.

The installer checks the protected signature and current finite permission before creating the offline environment. It verifies the installed payloads and performs eight fixed synthetic SDK cases before publishing the connection. Failure remains **Unavailable**; never bypass the verifier or overwrite a failed installation. This local connector does not configure a ChatGPT or Claude account. The [remote HTTP/MCP connection](remote-ai-connections.md) is a separate option.

No automatic research upload, training collection or network AI model is enabled. Optional local privacy checking needs a separately configured service; an unavailable privacy check must leave PS usable. Keep credentials and private conversations out of test inputs and public reports.

## What was actually verified

[Protected producer](https://github.com/knwvmbrr/aitrust-id/actions/runs/45201307837): source7986680c, exact artifact signature, fresh Linux installation and eight synthetic SDK cases. [Collected execution](../runs/2026-11-23-mcp-protected-managed-install.json) and [independent-root authorization](../runs/2026-11-23-mcp-independent-root-authorization.json) are separate observations. Public downloads are compared byte for byte in the publication record.

This is a connector engineering release. It does not establish independent PS accuracy, malicious intent, AI authorship, overall project completion or professional license clearance. F-057 and X-02 remain open for other distribution routes and their full original acceptance. Other planned tags are not enabled by this package.
