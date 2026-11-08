# PII separator correction: bounded implementation plan

The retained compact-address engine observations fully mask six synthetic
addresses, but two IP candidates also consume a field-separator colon.
A separate false IN_PAN finding masks the literal ip_address field label.
These are different defects; this increment addresses only the two IP
separator overhangs and preserves the other known failure.

Within the existing complete-IPv6 recognizer, replace an upstream IP_ADDRESS
candidate extending exactly one colon before the independently parsed full
value only when that colon is the delimiter of an already supported explicit
IP/IPv6/addr/address/host label. Preserve all other results, including their
scores, all non-IP categories, malformed/scoped/embedded inputs and current
thresholds. Never remove a possible identifier to hide a false-positive count.

Risks: an over-broad overlap filter could lose adjacent identifiers or scoped
addresses. Exact label/value offsets, one-character separator limits and
negative controls must constrain the change. No endpoint, model, collection,
production change, local Docker or new generation tag is introduced.

Use the unchanged fixed synthetic cohorts for before/after development
observations. Establish the current pinned engine in a separate private Python
environment; do not modify the shared verification environment. Record actual
source/model identity and execution profile. Keep Mac direct-engine evidence
distinct from historical Linux container and HTTP integration evidence.
A dependency or model identity failure stops that route; do not relax pins.

Acceptance: preserve complete address coverage, remove only the known separator
overhangs, retain other findings and the existing independent/privacy/human
gates. PII_REDACTED and F-023 remain open at their existing full acceptance
boundary; PS accuracy is neither used as a dependency nor credited.

## Real-engine diagnosis before publication

The first exact-end filter passed focused tests but changed no real output.
The pinned engine actually emits a short separator-crossing candidate, such as
4..6, before anonymization. The anonymizer mutates it to 4..8 while merging
overlaps. The diagnostic had recorded findings after that mutation and called
them raw candidates. Existing records remain historical observations.

Snapshot predicted entity/span values before calling the mutating anonymizer.
Reset applied-operation observations for every row and restore the diagnostic
wrapper even after failure. Keep the original operation and its arguments.
Replace only an IP candidate that crosses the single known label delimiter and
ends inside the independently validated full value. Preserve candidates reaching
beyond that value and every other entity category. Test the real mutation and
no-operation/failure paths, then rerun both unchanged fixed cohorts.
