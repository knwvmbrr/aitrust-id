# Confidence-floor enforcement audit — F-005

The existing gateway admits evaluator PS candidates at a rule score of 0.70 or above. A score below that threshold produces a schema-valid `below_floor` abstention. Other known evaluator codes are withheld with a null floor; unknown codes fail the upstream contract. Procedural redaction is owned by the redactor, not an evaluator-supplied PII claim.

The HTTP audit exercises the value immediately below the floor, the exact floor, the value immediately above it and both score endpoints. Boolean, string, null, out-of-range and non-finite confidence values return an explicit dependency error with no assertion. All nine inactive known codes and four unknown proposals are exercised through the HTTP handler. These are synthetic upstream responses, separate from actual service and independent accuracy evidence.

The 0.70 rule score is not a measured probability and is not the 0.93 precision lower-bound release gate. F-005 advances to 60% for its current contract, mechanism and executable checks. Meaningful per-tag calibration, agreed evidence-supported confidence policy and final acceptance remain open; no inactive tag is released and no independent validation is claimed.

The tests use the current production handler without changing gateway, evaluator, thresholds, permissions or collection. The recorded source identities reopen the audit when these inputs change. A malformed dependency must not turn an unavailable result into an assertion.

[Executed audit](../runs/2026-10-13-confidence-floor-http-audit.json) · [Tests](../tests/test_gateway_integration.py) · [Setup service evidence](../runs/2026-10-13-one-command-complete-input-linux.json)
