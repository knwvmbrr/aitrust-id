# Explicit bracketed email recognition — architecture before implementation

F-023/T-PII retain an existing synthetic challenge: `Contact pilot [at] example
[dot] org.` The annotated email occupies original characters8..36. The current
source-bound November12 Linux observation reports no candidate or applied mask:
all28 annotated characters remain visible. All five redactor source identities
still match this checkout. That retained observation is not a new runtime probe.
The fixed English/challenge and compact fixtures remain unchanged.

## Narrow job and protection

Extend only OfflineEmailRecognizer for one explicit ASCII form containing both
bracketed `[at]` and `[dot]` markers within the same bounded address candidate.
Case variants of those literal markers may be accepted; ordinary prose `at` or
`dot`, unbracketed alternatives, non-ASCII local/domain forms and arbitrary
whitespace joining are outside this increment. Bound local/domain labels,
inter-marker ASCII spacing and the complete projected address. Reject malformed,
embedded, truncated and over-limit candidates rather than masking a suffix.

Construct a private per-candidate projection, pass it to the same existing
upstream email recognizer and offline packaged suffix validator, and require a
whole-candidate email result. Add only that candidate's original full span;
preserve upstream score, explanation and recognizer metadata. Original input is
never globally rewritten, executed, sent to DNS or retained. The ordinary email
path, existing four invisible separators, other entities, scores and thresholds
remain intact. No new entity, dependency, model, endpoint, permission, storage,
collection or tag dependency is introduced. PII transformation and recognition
quality remain distinct; neither depends on a PS verdict. The source identity
must naturally change when code changes; never reuse an old method identity.

## Risks and controls

Bracketed prose could resemble an address, and an overlong or malformed address
could lend a valid suffix. Require explicit paired markers, complete bounded
candidate acceptance and strict original boundaries. Test ordinary prose and
invalid suffixes, punctuation, adjacent/multiple addresses, ASCII marker case,
Unicode context/offsets, disallowed internal whitespace, invalid/oversized tokens,
missing markers, unrequested categories, duplicate findings and forwarded NLP
arguments. Keep the exact upstream objects on unaffected input. Exercise maximum
supported input size with a bounded synthetic adversarial string. Do not suppress
another recognizer to hide an overlapping false mask.

## Actual runtime qualification

The Mac currently has no installed pinned Presidio/spaCy engine. Do not install
one or start local Docker. A read-only metadata audit locates the existing
nonroot staging redactor image on the dedicated Linux host. Its live service
uses a bridge network and is not the probe target. A separately approved owned
container may reuse that exact installed image with network none, read-only
root, no capabilities, no new privileges and explicit resource/timeout limits.
No service rebuild, replacement, public route or production change is authorized
by this plan alone.

First obtain actual baseline source/model identity and the fixed challenge from
that isolated image; refuse any stale five-source or model identity. After code
freeze and different source review, separately authorize an immutable candidate
source overlay in another owned isolated process. Run the real recognizer and
anonymizer plus unchanged42 English/challenge and six compact rows; report
remaining misses and extra masking without modifying their annotations. Require
all unaffected rows and source/model/dependency pins unchanged. Source-current
in-process ASGI controls may verify the unchanged redaction HTTP contract, but
are not a rebuilt public service or pipeline acceptance. Parent integration owns
new method selection, published charts and replay/service rollout.

The bounded software outcome is fixing the measured bracketed challenge without
weakening existing privacy behavior. Independent representative recognition,
human operation, broader languages/obfuscations, tag release and full original
requirement acceptance remain open. No percentage or release gate changes here.
