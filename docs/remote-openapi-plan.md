# Ordinary JSON API import manifest

Architecture before implementation, November 21, 2026. This is an additive
OpenAPI 3.1.1 description of the existing anonymous remote JSON transport:
POST `/v1/check`, GET `/v1/tags`, and GET `/healthz`. It neither adds routes nor
describes MCP as an ordinary OpenAPI operation. The sole server is the approved
provider hostname; public activation and AI-host import acceptance remain separate.

The manifest must preserve selected-text disclosure, development-only PS results,
remote PII unavailability, no application input persistence/research submission,
and complete/partial/unavailable distinctions. No credential scheme, truth,
safety, AI-origin or independently validated result is invented. Source code is
open; remote execution still sends explicitly selected text to the operator.

Risks: tools may ignore JSON Schema 2020-12 features; input byte limits and
duplicate JSON keys cannot be fully expressed by an OpenAPI object schema;
reverse-proxy refusals can be plain text rather than the application's JSON;
successful HTTP 200 can carry Unavailable. State all these limits explicitly.

A bounded standard-library checker reads the actual source AST and manifest,
without importing the optional MCP SDK, to compare selected routes, input schema,
constants, source identities and non-content output contract. Focused checks use
the already installed JSON Schema validator to accept canonical real PS results
and unavailable/partial projections and reject corrupt manifests and overclaims.
Do not rerun the remote service/browser matrix. The prior real HTTP/MCP and proxy
receipts establish only their own executed scope.

Owned files: `integrations/ai-tools/remote-openapi.json`,
`scripts/verify-remote-openapi.py`, `tests/test_remote_openapi.py`, this plan,
an immutable focused run, and an attributed changelog event. No route, runtime,
policy, scope, website build hook or public deployment changes.

Official format reference: [OpenAPI 3.1.1](https://spec.openapis.org/oas/v3.1.1.html).
