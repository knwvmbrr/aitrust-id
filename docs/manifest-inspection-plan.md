# Attached-manifest inspection plan — 2026-10-11

F-025 remains the job of inspecting an external attached C2PA manifest. This
iteration reads supported PNG with the official pinned SDK (JPEG remains open),
retain source/asset identity and positive/failed validation observations, and
return unsupported/unavailable explicitly. It does not issue image credentials,
change the text-only gateway, assert FA/PA, identify a person or establish truth.

The existing SDK-status adjudicator does not parse files. Add a separate CLI
adapter using c2pa-python 0.38.0 in an optional dedicated environment, with exact
package/wheel and native library hashes. The normal personal checker acquires
no dependency on it. Do not use global settings or silently fetch manifests,
OCSP, trust lists, identities or thumbnails. A per-reader context disables
remote fetch and OCSP and allows no network hosts. Revocation remains unknown;
unchecked revocation cannot be upgraded to a valid authority verdict.

Read only an explicitly selected regular file within a declared size limit.
Run the native parser in a separate bounded child, with a deadline and memory
limit where supported. Native crashes/timeouts return unavailable. Default
output is a minimal inspection summary; do not echo raw author/GPS/content
metadata or the private file path. A full SDK report needs explicit separate
output selection to an owner-private new file outside the repository.

Risks: hostile native inputs, implicit network access, missing validation
successes, accidentally exposing embedded identity data, native library/version
mismatch and interpreting signer trust as content truth. Exercise signed,
unsigned, altered and malformed real assets, negative/unknown validation cases,
private-output refusal, isolation and crash/timeout behavior. Pin test fixtures
and their provenance/licensing; do not manufacture a passing accuracy claim.

Before completion credit, demonstrate the full declared bounded job, successful
and failed cases, inspect the actual output and current executable evidence.
Release interpretations and broader formats remain their own acceptance gates.

Sources checked: [official context settings](https://github.com/contentauth/c2pa-python/blob/main/docs/context-settings.md),
[SDK manifest validation](https://opensource.contentauthenticity.org/docs/manifest/reading/manifest-validation/),
[pinned package](https://pypi.org/project/c2pa-python/0.38.0/).
