# Remote tag connectors: architecture and risk plan

Base e8287050493f3f30b6c92967beed224a6c8b4dc3. This is a new explicitly requested integration enhancement, not completion of an original tag requirement. PM approved the local code route contract before implementation: POST `/mcp`, GET `/v1/tags`, POST `/v1/check`, GET `/healthz`. No public hostname, deployment or AI account connection is approved by this document.

Use the existing hash-locked MCP2.3.0 environment and its official Streamable HTTP session manager, stateless JSON-response mode; no dependency installation. Keep existing stdio and local privacy API unchanged. Each PS request launches the unchanged canonical `scripts/check-ps.py` in its own bounded isolated Python subprocess. Validate its complete input-bound result and project only the existing brief signal counts/method identities. Remote PII is explicitly unavailable and never invokes the local gateway. Text, offsets, subject hashes, URLs and exceptions are not returned or logged.

Security: bind loopback only; exact operator-selected Host and optional Origin allowlists, absent Origin allowed for server clients; no wildcards, forwarded-header trust, cookies, authorization passthrough, sessions or URL/query inputs. Reject duplicate/conflicting framing/compression and oversized/ambiguous UTF-8 JSON. One12-second request budget includes body intake and work; cap wire256KB, input20,000 codepoints/80KB, child output2MB, two PS workers and finite active HTTP requests. Separate small discovery/health rate bucket remains usable during PS saturation. No IP or text retention; NoAuth means public resource abuse remains possible, so TLS/proxy admission and log suppression are deployment obligations. No endpoint fetch, execution of submitted text, database, research submission or model API.

Cancellation and shutdown must kill/reap only owned workers, preserve admission until cleanup and refuse stale/partial results. Test actual official MCP client discovery/positive/no-finding/refusal/recovery; actual ordinary HTTP, malformed framing/origins/hosts/resource pressure, cancellation and shutdown. Input canaries must be absent from responses and captured logs. Preserve historical failures as separate receipts. Do not call an anonymous read-only tool a private local check: submitted text reaches the selected remote operator, and the AI host has its own handling rules.

Primary references checked November21,2026:

- [Current MCP HTTP transport](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http): POST request-scoped transport, Host/Origin security, protocol metadata, stream-close cancellation and legacy interoperability. The installed SDK's legacy2025 compatibility is tested separately.
- [MCP security guidance](https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/security_best_practices): no token passthrough/SSRF, precise trust boundaries.
- [OpenAI custom MCP guide](https://developers.openai.com/api/docs/guides/custom-mcp-server) and [Anthropic remote connector](https://platform.claude.com/docs/en/agents-and-tools/mcp-connector): remote accessibility/host policies remain actual owner/platform gates; stdio alone is not a public remote connection.

No independent accuracy, global redistribution clearance, hosted PII or full original requirement closure is implied.
