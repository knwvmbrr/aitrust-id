# Look at two-choice wording — local research tool

Does a message present two choices? This tool records the exact wording you select and a separate passage you nominate as another option. You decide whether that passage is relevant. Nothing is uploaded and no account, model download or extra package is needed.

This is a computer-based practice tool, not a released MT tag. It does not decide that an alternative works, that the two choices are exhaustive, or that someone is manipulating you. Quoted examples and legitimate safety advice can contain the same wording.

## Try it in three steps

Download the [open-source repository](https://github.com/knwvmbrr/aitrust-id/archive/refs/heads/main.zip), unzip it and open Terminal in its folder. The command has been exercised with Python 3.12 on Apple Silicon and Python 3.13 on Debian x86-64.

1. Create an owner-private practice folder outside the repository:

```sh
practice="$(mktemp -d "${TMPDIR:-/tmp}/aitrust-choice.XXXXXXXX")"
```

2. Prepare the invented example. This reads none of your own messages:

```sh
python3 scripts/prepare-choice-demo.py --output "$practice/demo"
```

3. Check it:

```sh
python3 scripts/check-choice-framing.py --packet "$practice/demo"
```

The result means: **the selected wording presents two choices; the extra passage is nominated context, not a verified alternative.** The practice example is deliberately simple. Success demonstrates this command path, not its real-world accuracy.

## See the exact locations

Add `--details "$practice/details"` to the check command. The new private folder contains `choice-observations.json`. It records the selected frame, two choice locations, either/or markers, nominated reference locations, source fingerprints, method fingerprint and actual Python/Unicode version. It does not include the source text. Fingerprints and locations can still reveal or link information; keep the result private. Existing folders are never overwritten.

The short console result leaves out text, fingerprints, raw locations and runtime details. No result is automatically stored on our server, shared, enrolled or used for training. Deleting the practice folder removes its local inputs and any deliberately saved results. There is no background service to uninstall.

## Use your own example — advanced

Keep all inputs outside the repository in an owner-held `700` folder with `600` files. Private files must be regular, singly linked files. Use the [corpus guide](local-reference-corpus.md) to create `corpus.json`; keep the original references for reproduction. Save your text as UTF-8 `subject.txt` and an exact `context.json` alongside it. The `--packet` command reads only those three named files.

Context format: `choice-frame-context/v1`, language `en`, the NFC subject SHA-256, the corpus manifest SHA-256, and `frames`. Each frame contains its NFC code-point `span`, two ordered nonoverlapping `choices` spans, and an `additional_reference` with document ID, raw source SHA-256 and NFC `source_span`. The practice packet supplies a complete example. Do not reuse its hashes or locations for different text. Alternative selection belongs to you; a different string is not necessarily a genuinely different or feasible option.

The observer checks at most 16 ordered frames in 8,000 subject characters. A frame and its nominated passage are each bounded to 2,000 characters; each choice is bounded to 256. All context and corpus bindings must validate before any findings are returned. Unsupported encodings, stale bindings, ambiguous extra fields or unsafe file access return **Unavailable**, exit `2`, without a partial result. No supported either/or pattern means only that this grammar did not match; it is not a safety clearance.

## What remains to validate

Only caller-selected English either/or constructions are implemented here. Broader exclusive statements without either/or, automatic selection, negation, feasibility, source freshness, quotation/use context and independent error measurement remain open. Urgent safety advice and ordinary binary choices are retained as controls, without a manipulation verdict. This observation is proposed for `sig.false_dilemma.v1`; no tag mapping is accepted or activated.

A modified checkout, malicious same-account process or compromised administrator can bypass local protections. This is not an identity, truth or host-security attestation.

## Recheck the command

From the repository, run:

```sh
python3 scripts/verify-choice-framing.py --python "$(command -v python3)" --output output/verification/choice-controls.json
```

The 19 controls use invented examples. They exercise private access, exact bindings, no-overwrite behavior, malformed input refusal, the practice path and unavailability. They do not measure independent MT accuracy. [Scope and evidence](scope-progress.md) keep the full requirement open.
