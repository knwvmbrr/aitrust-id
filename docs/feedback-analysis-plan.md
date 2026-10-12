# Next independent buildable job: feedback analysis without prompt collection

Architecture before implementation, 2026-10-12. N-011 separates collection,
training and analysis. A complete optional offline metadata analyzer can be built
without a new endpoint, a live participant database, raw examples or a pilot.
Start with explicitly invented closed-schema batches of the same eight website
feedback fields already validated by research_admission.metadata. Reuse that
validator; no weakened copy, timestamps, hashes, tokens, personal text or free text.

Capture private files with the existing descriptor/owner/link/size guard. Reject
unknown batch versions, invalid fields, duplicate keys, nonfinite values, nesting,
overlong batches and mixed methods. Read each file once; no database credentials,
server connection, SQL, auto enrollment, upload or background retention. Optional
private details use a new exclusive output directory outside the checkout.

Compute record counts and fixed-choice distributions; compare two equally scoped
batches as descriptive changes in reported outcomes and usability. Show exact
record denominators, not people or accuracy. Count identical metadata combinations
without assuming duplicate combinations came from the same person. Do not dedupe
away real people or claim that repeated rows represent distinct people. No Wilson
accuracy intervals, classifier accuracy, verified failures, independence, population
inference, fraud accusations or automatic training labels. A selected voluntary
report is not independently verified ground truth.

Any review flag uses an explicit caller-selected minimum record count and absolute
percentage-point change in a reported category. Present the rule and denominator,
label it an inspection prompt, and preserve insufficient-data/no-change states.
Keep both batches method-scoped and distinguish denominator changes from rate
changes. This is not calibrated anomaly detection. No metadata report becomes a
new tag, origin assertion or automatic correction of a user's private result.

Execute exact arithmetic and real CLI privacy/refusal controls on Mac and isolated
non-root Linux using invented batches; source hashes before/after; cleanup owned
files. Publish a simple practice generator and guide if the complete component
passes. N-011 remains open for accepted collection/authentication, real consent,
retention/withdrawal, backup expiry, replacement recovery and an actual pilot.
