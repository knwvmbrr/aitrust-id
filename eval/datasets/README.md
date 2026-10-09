# Datasets

Only `unsafe_code/` currently contains detector fixtures. Its manifest classifies
four active development sets and one historical set, with hashes. The active
sets contain 60 cases in total. They have been used during implementation and
are not an independent holdout or evidence of a calibrated accuracy claim.

Run `make regressions` to check every active set. CI runs this independently of
the statistical gate. Missing classifications, changed hashes, malformed files
and classification errors fail the regression check. Historical
`counterexamples_v1.jsonl` preserves two superseded labels; the manifest explains
why `counterexamples_v2.jsonl` replaces it for current regression acceptance.

Fixtures are JSONL, with `text` and `labels`, and optional context metadata.
The following families remain planned; their presence and labeling are not claimed:

| Planned family | Tags | Required work |
|---|---|---|
| Grounded question/answer | NF, FI | Known answers and controlled corrupted variants |
| Unsourced assertions | HP | Invented statistics and citations with adjudicated ground truth |
| Persuasion | MT | Independent annotators and an accepted agreement protocol |

PS fixtures cover bounded command execution patterns and benign near misses.
A command-risk finding does not establish malicious intent or a scam. A frozen,
independently labeled holdout, agreed sampling policy and calibration evidence
remain separate release requirements.
