# PS reviewer handoff

PS has one job: flag supported commands that fetch code into an execution step,
or pass supported decoded payloads to `eval`/`exec`. It does not decide whether
an answer is true, whether an installer is legitimate, or whether someone is a
scammer. A legitimate installer can contain the pattern.

**Do not run any command in the examples.** Review text only.

1. A curator gathers new, authorized examples and records source and category.
   Include recommendations, downloads saved to files, quoted displays, warnings,
   encoded execution, and difficult mixed contexts. Do not reuse our development
   cases or private conversations. Agree sampling and candidate thresholds first.
2. Freeze the packet with `scripts/prepare-ps-review.py`. It records the detector,
   policy and dataset hashes and makes two separately shuffled CSV forms. The
   full procedure is in [independent-review.md](independent-review.md).
3. Each reviewer works alone, without detector results or the other's labels.
   Choose `positive`, `negative`, or `ambiguous`, and write a short reason. Do not
   change the example fields. Record any conflict or previous exposure.
4. Compare the forms. Keep disagreements and ambiguous items visible. Resolve
   disagreements with a recorded human adjudication before checking predictions;
   never drop hard cases to raise the score.
5. Run the frozen method only after review. Publish counts, denominators,
   intervals, category failures and sampling limits. A curated benchmark does
   not establish accuracy on every AI answer. Code, calibration, accessibility
   and the complete installed workflow have separate checks.

If a finding exposes a defect, record it. Fixing the detector requires a new
version and a new holdout; the exposed examples become development material.

Current engineering baseline: 134 Python tests and 86 development cases pass.
Independent labels have not been obtained. The release gate still fails.
The updated full container pipeline has not been rerun. No certification is claimed.
