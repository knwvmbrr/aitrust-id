# Straight and curly quote preview

This is an optional MT wording method, not a released MT tag. On a build containing
this preview, open MT, choose **Include curly quotes · preview**, paste English
text and choose **Explore wording**. It runs on your phone or computer. The first
run downloads the on-device Python runtime. Your pasted text is not uploaded or
saved by this tool. The older authority and urgency selections stay available.

Try this invented example:

> The example says “Experts agree [1]”.

The result reports one phrase inside supported quotes and none outside. It does
not say that the writer endorses the phrase or that reference [1] is real. Mixed
results show separate counts for quoted phrases and outside phrases with/without
a nearby source marker. These are related literal observations, not independent
votes, a manipulation rating, an intent judgment or a confidence score.

## Exact boundaries

Method `mobile-double-quote-authority-observations/1.0.0` accepts one double-quote
style per passage: straight ASCII quotes, or curly opening “ and closing ”.
ASCII quotes pair consecutively; their positions do not establish intended
nesting. For example, `"He says "Experts agree" then leaves"` leaves the authority
phrase outside those lexical pairs. Adjacent pairs remain separate quoted ranges.
Curly direction makes repeated openings detectable, and those nested openings
refuse. Mixed styles, mismatched/unclosed delimiters, backslash-adjacent quotes,
guillemets and backticks are unsupported. Single quotes and apostrophes remain
ordinary text. The tool refuses instead of guessing or silently repairing them.

The new candidate preserves the original quote/phrase/source-marker algorithm
on a one-codepoint projection of curly delimiters. Original normalized subject
identity and Unicode-codepoint positions remain bound to your actual text.
Source markers must be in the same literal unit and quotation context; nothing
is fetched or verified. A URL, citation marker, quote or absent phrase cannot
establish truth, endorsement, attribution, coercion or safe content.

English input is bounded to 8,000 codepoints and 32,000 UTF-8 bytes. Existing
limits remain 64 quote ranges,128 authority phrases,512 sentence units and256
source markers. Complete browser evidence is capped at100,000 serialized bytes;
oversized evidence becomes Unavailable without clipping it. Each explicit run
owns a fresh worker with bounded loading/check times. Editing, clearing, changing
the selection or closing the modal cancels work and removes stale results.

## Private details and local use

**Method and exact positions** is optional. It reveals a full source-bound record
with original raw UTF-8 fingerprint/count/bytes, frozen Unicode15 NFC fingerprint,
quote/phrase/unit/marker locations and method/source identities. Your text is
excluded. Fingerprints and positions remain linkable; keep them private. Nothing
is automatically exported, enrolled for training or sent to a server.

From a downloaded repository, the standalone method also works with Python3.12+
and no additional package, Docker, account, model or service:

```sh
python3 -I -S -B scripts/authority-mobile-quotation.py --language en < /your/private/text.txt
```

To deliberately save full details, add `--details /your/private/new-folder` in an
existing owner-held mode0700 parent outside the repository. A new0600 evidence
file is created; existing destinations are refused. Delete your own files when
finished. The default console result contains counts, not text or fingerprints.

The optional export uses the same analysis record and does not change quotation
recognition. If an explicit export fails, the console keeps the supported
analysis state and counts, sets `private_details_saved:false`, and adds a
separate `private_export` result. `UNAVAILABLE` means no new output from this
attempt is claimed; a pre-existing destination is preserved. `OUTPUT_UNCERTAIN`
with `private_output_may_remain:true` means a private file or directory may
remain: do not use it as accepted evidence. The command exits2 in either case.
A failed export is not evidence of unsupported quotation, no pattern or safe
content. Check and remove only your own residual private files when appropriate;
retry in a fresh destination. Missing optional export support leaves the default
recognition-only command usable.

Every remaining parent is walked without following symlinks. Arbitrary parent
symlinks, parent traversal, final existing names/links, unsafe permissions and
Git ancestors are refused. Only the actual fixed macOS system aliases `/tmp`
and `/var` may map to their exact `/private` counterparts when used as parent
components; the final requested name is never resolved or adopted. The adapter
reuses the unchanged private packet IO foundation, not MT labeling or another
tag's availability. It provides no universal hostile same-user/crash guarantee.

## What the checks establish

The browser checks closed record shape, source/subject identities, quote grammar,
span relationships and counts. Actual native/browser fixture comparisons test
complete canonical records. That boundary trusts the hash-verified canonical
worker; the JavaScript validator does not independently replay phrase matching
or prove semantic completeness. It never claims to detect all intended ASCII
nesting. A modified checkout, browser or computer can bypass local controls.

Canonical parity, invented examples and emulated browser checks are engineering
evidence. Independent representative labels, disagreement/error policy, broader
context/use-mention interpretation, accepted MT mapping, actual physical-phone
and human accessibility acceptance remain open. Neither MT nor F-019c is closed
by this selected-method preview.
