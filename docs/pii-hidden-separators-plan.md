# Mask email candidates separated by invisible format characters

The fixed development challenge `challenge_zero_width` currently leaves most of
`pilot@exam\u200bple.com` visible. The existing URL finding masks only its tail.
This is a demonstrated development privacy defect, not evidence about population
accuracy. Preserve every existing fixture, language boundary, score and gate.

## Architecture and user protection

Extend only the existing offline email recognizer. Keep its normal analysis
unchanged. When one of four explicitly supported separators (U+200B, U+200C,
U+200D or U+FEFF) occurs, construct an in-memory projection without those
characters, run the same upstream email pattern and packaged suffix validator,
and map new candidate boundaries back to the original string. Add a candidate
only when its mapped span actually contains one of those separators. Preserve
scores and recognizer metadata. Never normalize the shared input globally, open
a URL, query DNS, log or retain the projected address, or alter another tag.

Risks are joined false candidates, incorrect Unicode offsets, stale replay
identity, overlapping partial findings and added work on long strings. Keep
whitespace and all other characters; cover adjacent and non-ASCII text, missing
parts, invalid suffixes, repeated separators, boundary controls and worst-size
input. Inputs without a supported separator must retain the original result
objects and NLP arguments. Do not turn off an entity category or raise a
threshold to make an example pass.

## Verification and completion boundary

Exercise the actual pinned recognizer and anonymizer, then the full fixed
English/challenge and compact cohorts with the complete engine. Record Mac
diagnostics separately from a source-current, nonroot, network-isolated Linux
engine and service/replay checks. Keep production and local Mac Docker out of
this increment. Only a fully measured current engine may replace site charts;
retain all original failed observations. Unknown or stale evidence must refuse
publication. Keep English extra masking and unhandled obfuscations visible.

F-023 and T-PII remain open until their independent representative and human
acceptance succeeds. A corrected synthetic challenge does not close either
full requirement, expand supported languages, or release an independently
validated tag. App signing and the on-device PS build remain separate.

## Candidate findings — November 12, 2026

The candidate passed 58 focused source, contract and HTTP-privacy checks. In the
isolated pinned Linux engine, the fixed 42-row cohort changes only the hidden
email challenge: the full address is masked. The other 41 rows and all six
compact rows are identical to the previous observations.

Twenty-one actual in-process ASGI requests exercised masking, validation errors,
body bounds, method handling, health, response privacy headers and source
identity. All twelve hidden-separator email variants were fully masked. Five
also masked surrounding text because the unchanged NLP engine identified an
overlapping person. This remains an error to improve; the probe reports those
extra characters separately. Its initial exact placeholder/unchanged label
assumption failed. The revised probe observes the actual anonymizer's original
spans instead of hiding the overlap or disabling name recognition.

These are synthetic development results from a read-only source overlay in an
existing image, running without network, capabilities or root. They do not
replace the published charts, a rebuilt network/pipeline run, clean setup,
independent representative validation or human acceptance. Existing staging
services were not replaced. See
[the execution receipt](../runs/2026-11-12-hidden-email-development.json).
