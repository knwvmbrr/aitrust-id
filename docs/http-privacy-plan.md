# HTTP privacy boundary — current three-service route

The synthetic gateway probe returned its submitted private marker in a 422
validation error. FastAPI's default validation handler includes input values.
This is a real response disclosure, even when the endpoint rejects evaluation.

Use the shared Uvicorn application factory with one ASGI privacy middleware and one fixed validation-error handler in
the gateway, anonymizer and evaluator. Preserve schema validation, authentication,
body limits and successful output contracts. Every HTTP response carries
`Cache-Control: no-store` and `X-Content-Type-Options: nosniff`. Validation failures
contain only a fixed explanation. An unexpected failure before response headers
produces a fixed 500 without logging exception content; failure after headers
propagates because sending a second response would corrupt the stream. No new
endpoint, storage, telemetry or remote research intake is introduced.

The two internal images use the repository root as their build context so they
copy the same shared module; explicit COPY statements still select only their
own runtime code and that module. The factory wraps the existing service app;
detector source identity and the on-device projection remain unchanged. Disable Uvicorn access logs because request URLs
can contain private query values. Keep startup and operational health reporting.

Risks: removing detailed errors reduces caller diagnostics; the fixed messages
must still distinguish validation, authentication, unavailable dependencies and
unexpected internal failure through status codes. Middleware ordering must cover
413 body-limit errors and avoid swallowing cancellation/disconnection. This is
an application response/log boundary, not secure RAM erasure, browser-vendor
privacy, general PII detection, or independent tag accuracy.

Acceptance: inject synthetic canaries into body values, field names, malformed
JSON, paths and upstream exceptions; check fixed response bytes, no-store
headers and captured logs. Verify successful current assertions still satisfy
the complete schema. Rebuild and run the actual three-service Linux staging
route, including direct internal error requests and application-log inspection.
Consent/pause/reset and browser cache checks remain separate work and cannot be
closed from this middleware alone.
