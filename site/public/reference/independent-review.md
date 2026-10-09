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

From the repository folder, using a new destination in an existing private parent:

```sh
python3 scripts/prepare-ps-review.py freeze ../ps-review-items.jsonl ../ps-blind-review
```

The tool creates two separately shuffled CSV forms, the frozen items, and a hash
manifest. No detector is called. Spreadsheet formula prefixes are escaped in the
forms; the original frozen text is retained only in the private packet. Each
reviewer independently fills `label` with `positive`, `negative`, or `ambiguous`
and fills `reason`. Leave every other field unchanged. A PS positive is the
specified command pattern in a recommendation, including legitimate installers;
it is not a scam label. Capture uncertain use/mention cases as ambiguous.

```sh
python3 scripts/prepare-ps-review.py compare ../ps-blind-review
```

Incomplete, altered, duplicated or missing items fail the comparison. A detector
or policy change after freeze also fails it. The report names disagreement and
ambiguous IDs; it does not hide them or declare release. Record reviewer
independence and conflicts, adjudicate disagreements, retain all ambiguous items
and agree their reporting policy before evaluating. Two agreeing files alone do
not prove two independent humans reviewed them. The current harness's externally
supplied summary is not an attestation verifier; retain the full review evidence.
Calibration, accepted sampling, runtime and accessibility checks remain separate.

To volunteer, use the site's **Help improve this tag** control on PS, choose
**Independent labels**, and post a privacy-safe draft in the linked public GitHub
discussion. A maintainer coordinates the frozen packet; public posts are not
permission to train on private content.
