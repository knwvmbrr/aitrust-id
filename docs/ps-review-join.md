# Join an explicit review decision to local PS predictions

This is a usable **advisory development workflow**, not an independent evaluation
or a release approval. It works with current owner-private manifest-v2 packets
and completed JSON reviewer forms from the existing blind-review tools. It does
not collect examples, supply labels, resolve disagreement, verify people or fetch
URLs. Never execute commands contained in review examples.

Use the same already configured Python environment and checkout that froze the
packet. Changes to its declared execution recipe require a new packet. First
complete the existing private review workflow in [independent-review.md](independent-review.md),
including both reviewers' labels and reasons. Keep all original files unchanged.

```sh
python3 scripts/ps-review-join.py prepare --packet <private-packet> --output <new-private-template-folder>
```

Preparation validates both complete forms and the current frozen recipe. It
writes `adjudication.json` with **blank** labels/reasons and exact hashes for the
manifest, recipe, original items and both returned forms. It never runs the
checker or copies predictions into the form. The coordinator must enter an
explicit `positive`, `negative` or `ambiguous` decision and a reason for **every**
item, including agreements. Disagreements are not automatically settled. This
file records caller-supplied decisions; it cannot attest that a human made them,
prove independence, or adopt sampling/adjudication policy. Keep the file private
(mode 0600) in an owner-held folder (0700) outside the checkout.

```sh
python3 scripts/ps-review-join.py run --packet <private-packet> --adjudication <private-adjudication.json> --output <new-private-result-folder>
```

Execution refuses incomplete/changed forms, unknown or duplicate decisions,
changed item bindings, legacy recipes and unavailable predictions. No output
folder is overwritten. It launches the literal unchanged local
`check-ps.py --worker` under the current Python interpreter, using the same
source projection and frozen NFC. Nothing from the packet selects executable
code, imports, arguments or paths. The original recipe is checked for current
consistency; the executed **standalone projection** and this producer have their
own source identities. This is not execution of a gateway or a browser route.

The private result contains:

- `report.json`: existing `eval/harness.py` aggregate shape with PS counts,
  category failures/counts and explicitly advisory dataset flags.
- `predictions.json`: per-item original item/raw-text/source-field digests,
  frozen-NFC subject identity, both original labels, explicit decision/reason
  digest and full current PS signal/spans. No original text or reason is copied.

IDs, categories, hashes and signals can still identify or link private examples.
The output is private evidence, not a public publication bundle. Console output
has only fixed operation/count/false-claim fields. No account, upload, automatic
persistence or model is introduced. The trusted owned worker contains no network
operation; this tool does not claim an OS-wide networking sandbox.

Explicitly adjudicated ambiguous items remain listed and counted per category;
they are excluded from binary TP/FP/FN/TN denominators. This is transparent
advisory accounting, not permission to exclude ambiguity from a release study.
No per-signal ground truth is inferred from an aggregate PS label. Heuristic
scores are preserved as uncalibrated observations, never calibration pairs.

```sh
python3 eval/harness.py --results <private-result-folder>/report.json
```

The existing consumer can read the report and **must refuse release**: dataset
kind is `advisory_review_join`, `independently_labeled` and
`method_fixed_before_run` remain false, and calibration pairs are absent. No
`evaluation_gate_pass`, independent accuracy, representative sampling, human
operation, signature or full original requirement closure is earned by this join.

Limits: the existing packet member bounds plus a 32 MB captured packet total;
1,000 items; 20,000 codepoints/80,000 UTF-8 bytes per supported item; 4 MB explicit
decisions; 16 MB combined output; at most 10 seconds per fresh worker and 60
seconds for the cohort through final export validation. An oversized item is not
clipped or silently skipped. Required failures refuse the export and leave the
original packet and other tag tools unchanged. The coordinator's same OS-user
account remains trusted; hashes do not defend against a malicious owner rewriting
all evidence or establish trustworthy chronology.

An output-close or incomplete cleanup failure explicitly reports **export
uncertain**: private output may remain and must not be used as accepted evidence.
The tool never retries a released numeric descriptor or overwrites that folder.
