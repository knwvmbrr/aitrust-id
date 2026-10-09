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
