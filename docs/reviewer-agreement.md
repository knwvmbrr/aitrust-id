# Compare reviewer agreement

This standalone tool answers **“Did the supplied reviewers use the same categories consistently?”** It does not decide whether they were correct, issue MT or verify that aliases represent independent people. It needs no account, server, model or network.

Create one local JSON file with these exact keys:

```json
{
  "schema_version": 1,
  "kind": "nominal_agreement_ratings",
  "target_tag": "MT",
  "reviewers": ["ReviewerA", "ReviewerB"],
  "categories": ["Tactic", "NotTactic", "Unclear"],
  "units": [
    {"id": "ItemOne", "ratings": {"ReviewerA": "Tactic", "ReviewerB": "Tactic"}},
    {"id": "ItemTwo", "ratings": {"ReviewerA": "NotTactic", "ReviewerB": "NotTactic"}},
    {"id": "ItemThree", "ratings": {"ReviewerA": "Tactic", "ReviewerB": "NotTactic"}}
  ]
}
```

```sh
python3 scripts/reviewer-agreement.py /path/to/private/ratings.json
python3 scripts/verify-reviewer-agreement.py
```

Aliases begin with a letter and contain at most 32 ASCII letters, digits, underscores or hyphens. Do not include examples, names, emails, detector answers, rationales or private content. Each unit has every reviewer key; use `null` for a missing rating. An `Unclear` category is a supplied nominal judgment, distinct from a missing rating. Its interpretation must be agreed in the annotation protocol before collecting real labels. This tool does not silently turn uncertainty into a negative answer.

The output omits aliases, original units, category names, input hashes and free text. It reports pairable-unit coverage, anonymous category counts, disagreements and nominal Krippendorff’s alpha. Labels from units with fewer than two nonmissing ratings do not enter the coefficient’s expected disagreement. Negative coefficients stay negative. No pairable values or no category variation produce `UNAVAILABLE` and exit 2; unanimous constant labels never become “perfect” agreement. Invalid files also exit 2 with a fixed error. A computable coefficient exits 0, which is successful computation, not release acceptance.

Optional `--output output/verification/agreement.json` saves aggregate results atomically; that local output path can be replaced. Use a fresh `runs/*.json` path for an exclusive retained execution record. Nothing is uploaded. Even anonymous counts can reveal a small set’s distribution; review your report before choosing to share it.

The coefficient uses exact rational coincidence counts and then `1 − observed disagreement / expected disagreement`. This is the **nominal** metric; ordered or numerical ratings need a separately validated metric. The 0.55 MT value is reported only as an unaccepted candidate comparison. No confidence interval, sampling adequacy, missing-at-random inference, calibration or independent human evidence is established. MT’s annotation guide, blind collection, adjudication and accepted threshold remain unfinished. MT agreement cannot block PS or other independent tags.

The implementation is checked against three worked examples and missingness/ordering/privacy controls. Those are computational regression checks, not an MT study. Methods and formulas: [Krippendorff’s primary computational paper, sections A–C](https://www.asc.upenn.edu/sites/default/files/2021-03/Computing%20Krippendorff%27s%20Alpha-Reliability.pdf).

Report destination failures are distinct from invalid rating data. Execute unsafe-output refusal and exclusive retained-report overwrite checks; an output failure prints no coefficient and does not modify the retained record.
