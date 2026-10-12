# Independent review needed before release

## Ground-truth review

The current regression corpus and context tests were used during development and cannot be a held-out evaluation. Freeze a new independent set before viewing detector predictions. Include executable recommendations, explicit warnings, quoted mentions, mixed clauses, multiline commands, comments, benign encoding, and unsupported variations. Record provenance, category, reviewer labels, disagreements, and adjudication without private content.

The positive class is a recommendation containing one of the supported hazardous patterns. It is not a claim that the issuer is a scammer. A legitimate install instruction may still be a positive pattern. Ambiguous cases must be explicitly marked and counted separately, not silently removed to improve metrics.

Agree coverage and sampling before execution. Precision denominator is predicted positives; recall denominator is ground-truth positives. A curated regression corpus does not establish population performance. Two-sided Wilson 95% intervals and candidate lower bounds 0.93 precision / 0.75 recall are proposed, not accepted by a measured result. No minimum deterministic abstention quota applies.

## Human accessibility script

Using a dedicated test profile with synthetic content:

1. Install and configure the extension without assistance from the developer.
2. Navigate to an assistant response, find its compact tag or check-status marker,
   and open it by keyboard. Activate Recheck locally inside the dialog.
3. Hear the pending and completed states without an assertive interruption.
4. Read the short finding and limitation. Download its structured record and locate
   the method and redacted-text offsets; use the site catalogue for full definitions.
5. Press Escape; confirm focus returns to the evidence trigger.
6. Encounter invalid-token/backend-down and no-finding states; explain their difference.
7. Use browser zoom and narrow width; confirm all controls and evidence remain operable.
8. Remove the token and unload the extension using written instructions.

Record assistance needed and failures. Do not publish a tester's identity without consent. Critical failures block release. Automated axe results are only one part of this check.

## Live-site adapter check

Use a logged-in ChatGPT session and a dedicated extension test profile. Confirm normal completion, regeneration, navigation while pending, and manual checking all attach to the correct unchanged response. Do not publish screenshots or logs of private conversations. The automatic stream-completion heuristic is deliberately conservative and may need updating if the site changes.

## Prepare the first PS review

A dataset curator supplies **new**, shareable or authorized items, sampled under
an agreed protocol. Do not recycle active development datasets. Each JSONL row
contains exactly `id`, `text`, `category`, and `source` as nonempty strings.
Source records the origin and permission; category records the pre-agreed stratum.
Do not put credentials, private conversations or personal data into public issues.
Keep the corpus outside the repository. Write the protocol and fix the detector
before the reviewers see any prediction.

From the repository folder, create a private workspace outside the source checkout:

```sh
install -d -m 700 ../ai-trust-id-review
```

Put your authorized new items in `../ai-trust-id-review/items.jsonl`. Verify it is an ordinary file you own, rather than a link; set its permissions to 600. Then use a new packet name:

```sh
python3 scripts/prepare-ps-review.py freeze ../ai-trust-id-review/items.jsonl ../ai-trust-id-review/packet
```

The CLI works on Linux/macOS with private owner-held directories (700) and files (600). It refuses reused destinations, file links, shared permissions, duplicate JSON fields and malformed text. Source JSONL and phone forms are limited to 10 MB, items/CSV to 16 MB each, the manifest to 64 KB and the generated packet to 32 MB total. Oversized output fails before any packet is created. Identifiers must be unique opaque IDs; spreadsheet-escaped IDs must also remain unique. Source and category fields each allow 1,000 characters. These limits protect your machine; they do not establish a representative sample.

The tool creates two separately shuffled CSV and phone-friendly JSON forms, the frozen items, a hash
manifest and an owner-private execution-context member. New packets use private manifest v2; reviewer forms stay v1. Their opaque `method_sha256` binds the complete selected execution recipe; its raw evaluator-file hash is retained inside the private context. The context binds the selected Python evaluator, frozen NFC code/data, evaluation and preparation sources, Python executable/regex code and sixteen declared installed import dependencies and the gate schema/category code. Compare checks this recipe before labels and again afterwards. A dependency or runtime update needs a fresh packet; a packet prepared on another host may not match this coordinator host. This is a selected offline route identity, not whole-host attestation, a timestamp authority or a service/browser measurement. No detector is called. Spreadsheet formula prefixes are escaped in the
forms; the original frozen text is retained only in the private packet. Each
reviewer independently fills `label` with `positive`, `negative`, or `ambiguous`
and fills `reason`. Leave every other field unchanged. A PS positive is the
specified command pattern in a recommendation, including legitimate installers;
it is not a scam label. Capture uncertain use/mention cases as ambiguous.

```sh
python3 scripts/prepare-ps-review.py compare ../ai-trust-id-review/packet
```

Incomplete, altered, duplicated or missing items fail the comparison. A detector
or policy change after freeze also fails it. The report names disagreement and
ambiguous IDs; it does not hide them or declare release. Record reviewer
independence and conflicts, adjudicate disagreements, retain all ambiguous items
and agree their reporting policy before evaluating. Two agreeing files alone do
not prove two independent humans reviewed them. The current harness's externally
supplied summary is not an attestation verifier; retain the full review evidence.
Calibration, accepted sampling, runtime and accessibility checks remain separate.

For current packets, require the execution binding explicitly:

```sh
python3 scripts/prepare-ps-review.py compare ../ai-trust-id-review/packet --format json --require-execution-binding
```

Legacy manifest v1 packets can still be compared for their labels with the original command. The report says `execution_binding_verified: false`: comparison preserves the original historical labels and frozen hashes, even when the current evaluator or instructions have changed. It reports current method, gate and policy matches separately; mismatches never supply current execution or release evidence. The require-binding option refuses them. Retain the old files; do not rewrite their manifest to manufacture historical dependency evidence. Hashes can be rewritten by whoever controls a packet, and agreeing files do not prove independent humans. No freeze or comparison runs the detector, evaluates accuracy, uploads content or approves release.

To volunteer, use the site's **Help improve this tag** control on PS, choose
**Independent labels**, and post a privacy-safe draft in the linked public GitHub
discussion. A maintainer coordinates the frozen packet; public posts are not
permission to train on private content.

## Review on a phone

Open https://aitrustid.com/#person/PS and choose **Review test examples**. Open
your `reviewer-1.json` or `reviewer-2.json` file, label each example and give a
reason, then **Download labels**. Download progress before closing the page;
reopen the downloaded JSON to resume. Nothing is uploaded or saved by the site.
Return the completed file privately to the coordinator. Import only an ordinary independently copied file, keep the private packet directory at 700 and set the imported form to 600 before comparison. Do not use permission changes to disguise a symlink or hardlink. The coordinator puts each file back
in the corresponding private packet location and runs:

```sh
python3 scripts/prepare-ps-review.py compare ../ai-trust-id-review/packet --format json
```

CSV remains available. Choose one format consistently for both reviewers. JSON
comparison checks the same frozen hashes and exact original item fields as CSV.
This form reduces setup work; it does not supply labels, prove independence or
replace adjudication. Do not open the checker on your review examples.

The phone form strictly reads UTF-8 and rejects duplicate fields, non-scalar text, excessive nesting and invalid shape. Rejected files never become a review. Completed labels remain on your device until you choose to download them. The CLI comparison preserves disagreements and never calls the detector. See [the packet safety plan](blind-review-privacy-plan.md) for the controls and their threat boundary.
