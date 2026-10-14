# Research transport

The default ASGI application is disabled. It never reads a feedback body or
consults an environment variable to enable collection. It is independent of
the gateway and every detector.

The separately constructed development application is exercised by
`python scripts/metadata-store-sandbox.py --profile http`. It accepts invented
metadata only in a newly owned private PostgreSQL sandbox. It is not a participant
service or a production deployment template.

See [the operating guide](../../docs/research-http.md) and
[architecture and risks](../../docs/research-http-plan.md). Existing pinned gateway
dependencies supply Uvicorn for the verifier; no additional package is introduced.
