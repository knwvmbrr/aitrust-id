# Prepare private MT wording reviews

This account-free offline tool turns explicitly supplied examples into two blank
forms using the [candidate annotation guide](mt-annotation-guide.md). It does not
run a detector, upload anything, adopt a protocol or verify that two people took
part. Existing MT observations and other tags do not depend on it. Python3.12+ on macOS/Linux with no-follow/directory-FD support
and the repository's standard library tools are sufficient; no package install.

Create a real private folder **outside every Git checkout**, mode0700. Input and
returned JSON files must be owner-held0600 regular files, with no symlink
ancestors. Use actual paths (macOS `/tmp`/`/var` aliases may be symlinks). The input
has exactly this shape; contexts may be empty, but remain caller-selected and
unverified:

```json
{"profile":"mt-label-items/v1","language":"en","items":[
  {"id":"example-one","text":"Experts agree.","context":"An article analyzes this phrase as an example, without adopting it."}
]}
```

```sh
python3 -I -S -B scripts/mt-label-preparation.py prepare --items /private/reviews/input.json --out /private/reviews/new-packet
```

The new packet includes frozen items/guide/rubric, a manifest and independently
shuffled `reviewer-A.json`/`reviewer-B.json` blank forms. Source IDs are replaced
with neutral unit ordinals. No model answer, suggested label, ground truth or
source/category hint is included. The packet binds exact original bytes and
frozen NFC identity. It is private and linkable, not an authenticated attestation.

Give each rater only their own form plus the guide. They complete all four axes,
reasons and NFC codepoint spans. Use the guide to distinguish legitimate urgency,
choice feasibility, source attribution and quotation/use, while preserving
uncertainty. Example annotation shape (a formatting illustration, not a suggested
answer for the item above):

```json
{"label":"uncertain","reason":"The supplied context supports multiple readings.","text_spans":[],"context_spans":[]}
```

Keep the fixed facts in each response unchanged. Save returned files0600 in a
private0700 directory. You can validate each response before comparing:

```sh
python3 -I -S -B scripts/mt-label-preparation.py validate --items /private/reviews/input.json --packet /private/reviews/new-packet --slot A --response /private/reviews/returned-A.json
python3 -I -S -B scripts/mt-label-preparation.py compare --items /private/reviews/input.json --packet /private/reviews/new-packet --a /private/reviews/returned-A.json --b /private/reviews/returned-B.json --out /private/reviews/new-comparison
```

The original input is required again: a packet cannot authenticate itself merely
by carrying matching mutable hashes. Changed examples/raw Unicode/source version,
wrong slots, missing answers, unknown fields or invalid evidence refuse. Completed
supplied-label processing exits0; refusal exits2. An unavailable coefficient (for
example constant ratings) remains Unavailable and is not a workflow/MT pass.

The console shows anonymous aggregates only, without examples, reasons, IDs,
paths or input hashes. The new private comparison contains `agreement.json`,
standard per-axis `matrices.json` compatible with the unchanged agreement helper,
and `review-queue.json` with the private cases requiring review. No adjudicated
answer is filled in. Inspect before any deliberate sharing; even counts may
reveal a small cohort's distribution. Existing destinations are never overwritten.
If `OUTPUT_UNCERTAIN` is printed, private output may remain; inspect it and do not
use it as accepted evidence. There is no crash-atomic rollback promise.

Limits:1–256 English-labeled examples;8000 raw/NFC codepoints per text/context;
2MiB per input/response;8MiB total output. This is annotation preparation only.
Human independence, representative sampling, adjudication, accepted thresholds,
category-error assessment, confidence calibration and MT release remain pending.
