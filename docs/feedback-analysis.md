# Understand feedback without collecting private conversations

This free, offline preparation tool compares two **invented** batches of the
structured PS feedback fields. It helps test the analysis pipeline before a
real pilot is accepted. It does not collect feedback, contact a database, upload
anything, train a model, measure accuracy or issue a tag.

## What the numbers mean

A record is one set of choices. It is not necessarily one person, one independent
check or one confirmed error. Twenty identical records remain twenty records;
this tool does not guess whether they came from the same person. Repeating a
choice does not prove duplicate users, fraud or corroboration.

The tool counts reported outcomes, failure categories and usability choices.
It compares each category's share using its own batch denominator. More records
with the same proportions produce no rate change. A change means **review the
reports**, not "the detector got worse" or "this is an anomaly."

An inspection rule is explicit: minimum records in each batch and absolute
percentage-point change. The defaults, 20 records and 10 points, are preparation
settings, not scientific thresholds or release gates. Exact fractions determine
whether the rule is met; displayed changes are rounded to six decimal places.
Both increases and decreases can prompt inspection. Insufficient counts are
reported separately and produce no inspection prompt. A sufficient batch with unchanged category proportions has its own no-change state, even when record totals differ. Small changes below the chosen rule remain changes with zero inspection prompts.

## Try the whole workflow

Use Python 3.12 or newer on macOS or Linux in a current source checkout:

```sh
install -d -m 700 "$HOME/AITrust-ID-feedback"
python3 scripts/prepare-feedback-analysis-demo.py --output "$HOME/AITrust-ID-feedback/practice"
python3 scripts/analyze-feedback.py \
  --before "$HOME/AITrust-ID-feedback/practice/before.json" \
  --after "$HOME/AITrust-ID-feedback/practice/after.json"
```

Expect 20 invented records per batch and six category inspection prompts. There
are only two distinct sets of choices in this example; neither file represents
20 people. Six prompts are not six verified failures.

Add `--details "$HOME/AITrust-ID-feedback/details"` to the same command to inspect
the individual counts, denominators, directions and percentage-point changes.
The destination must be new. Existing files are not overwritten. Use
`--minimum-records 21` to see the insufficient-records state for this example.

When finished, delete the private practice/details folders you created. The tool
keeps no separate copy. Deleting your copy cannot recall a file you shared.

## Strict preparation boundary

Input uses `synthetic-feedback-batch/1.0.0`, `synthetic: true` and a `records` array.
Each record must match the same eight-field website feedback contract: schema
version, purpose, PS tag, `context-v6` method, local-file sharing, reported result,
failure category and usability feedback. All 80 allowed combinations are supported.
Maximum: 5,000 records and 2,000,000 bytes per batch. Unknown fields, versions,
methods, choices, duplicate JSON keys, nonfinite values, private text, tokens,
timestamps, hashes and explicitly real batches refuse.

Input files must be owner-held mode-0600 regular files in mode-0700 directories
outside the source checkout. Links, pipes, public permissions, invalid UTF-8 and
existing output destinations refuse. Console output contains record totals, the
number of inspection prompts and status flags. Optional private details contain
only fixed-choice distributions, not the input records or identities. Aggregate
counts can still reveal information about a small group; do not publish them
without the separately accepted pilot/privacy rules.

The synthetic flag is a caller declaration, not proof of consent or authentication.
Do not relabel real contributions as invented to bypass the pilot boundary. Real
analysis needs the accepted collection/purpose, withdrawal, retention, access,
authentication and participant workflow. Reports remain observations; independent
labels and separately authorized examples are needed for any accuracy study or
training dataset. This component creates neither.

## Run its checks

```sh
python3 -m pytest tests/test_feedback_analysis.py tests/test_research_admission.py -q
python3 scripts/verify-feedback-analysis.py --output output/verification/feedback-analysis.json
```

These execute invented arithmetic, real CLI, private-file and failure controls.
They do not validate PS's detection accuracy or complete a recruited pilot.
