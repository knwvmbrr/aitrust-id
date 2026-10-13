# Compare a claim with your references — research tool

Choose a short English claim and your own reference text. The tool finds similar passages, then asks one pinned local model how each selected passage relates to the claim. Nothing is uploaded. No account is required.

This is an optional computer-based research command. It does not issue NF, FI or any other tag, verify a fact or establish that a reference is accurate or current. Fingerprints identify selected bytes; they do not authenticate the publisher. Phone use and independent accuracy validation are not supplied by this command.

## Three steps

1. Follow the [sentence-pair setup guide](nli-pairs.md) for a separate private environment and verified model cache. Use the exercised Apple Silicon/Python 3.12 or Debian x86-64/Python 3.13 environment. Setup uses the internet; evaluation uses the existing network-denied worker.
2. Import your references with the [local corpus guide](local-reference-corpus.md). Save the claim in a private UTF-8 text file. Keep both outside the checkout, in an owner-held `700` folder with `600` files. Avoid private text in shell commands.
3. Run this command, replacing `PRIVATE` and `REPO` with your absolute paths. `PRIVATE/result` must be a new folder.

```sh
PRIVATE/nli-env/bin/python REPO/scripts/check-nli-references.py --corpus PRIVATE/corpus.json --subject PRIVATE/claim.txt --model-cache PRIVATE/nli-assets --details PRIVATE/result
```

Omit `--details PRIVATE/result` for a short console summary only. Deliberately requested details are in `PRIVATE/result/reference-observations.json`: exact claim/reference locations, corpus/source fingerprints, retrieval parameters, model/version/Python/architecture identity, all three model scores and tied labels. They omit text, but fingerprints and locations can still reveal or link information. Keep them private. Existing folders are never overwritten. Nothing is automatically shared or used for training.

## Read the result

**Passages compared:** the reference is the model's premise; your claim is its hypothesis. Contradiction, entailment and neutral describe one model's interpretation, not verified facts or measured probabilities. Multiple passages still share one model; they are not independent corroboration. Reversing the direction may change the output.

**No similar passage:** lexical selection completed, but nothing met the threshold. The model did not run. This does not mean the claim is false, fictional or unsupported everywhere. No model identity or invented score is attached to an unperformed evaluation.

**Unavailable:** no usable result was obtained. A short category explains whether to check private files, pinned cache, dependencies, supported sandbox or deadline. Exit status is `2`; the command returns no partial result or tag.

## Reproduce the limits

The default ASCII word-count cosine selector uses `0.75`. “The room is empty.” and “There are people in the room.” score about `0.408`: the default misses a relevant contradictory reference. That failure remains in tests. An explicit `--threshold 0.4` exercises this particular selected pair; it is a research parameter, not a validated remedy or release threshold.

The same model has called the compatible sky/books sentence pair a contradiction in actual tests. It can be wrong after the right passage is selected. Search thresholds cannot fix that model error. Source date, relevance, reliability and freshness remain separate questions.

Bounds: 2,000 subject characters and 32 nonempty lines; 512 ASCII word tokens per lexical passage; at most five model pairs, 2,000 characters per passage, 20,000 total prepared characters and 512 model tokens per pair. Existing corpus limits also apply. Unsupported references are counted; unsupported claims and overlong model input refuse without truncation. The outer 55-second deadline ends its owned worker session. The nested worker retains its 35-second CPU/45-second wall deadline, one-thread inference and Linux 2 GiB address-space bound.

## Check and remove

### Optional: limit when your saved references may be used

You can supply a date window for the references you reviewed. First inspect their
content yourself and choose a UTC start and expiry. This is your declaration;
neither preparing the file nor passing the date check proves a source is current
or true. Preparing it automatically binds the dates to every attached document,
so you do not have to copy fingerprints by hand.

Use real dates you have chosen in place of `START` and `EXPIRY`, in
`YYYY-MM-DDTHH:MM:SSZ` format. `PRIVATE/windows` must be a new private folder.

```sh
python3 REPO/scripts/prepare-reference-review-windows.py --corpus PRIVATE/corpus.json --opens-at START --expires-at EXPIRY --output PRIVATE/windows
PRIVATE/nli-env/bin/python REPO/scripts/check-nli-references.py --corpus PRIVATE/corpus.json --subject PRIVATE/claim.txt --model-cache PRIVATE/nli-assets --review-windows PRIVATE/windows/review-windows.json --details PRIVATE/result
```

The checker uses its UTC machine clock. Every attached document must be inside
its declared window, both before and after comparison. Start is inclusive; expiry
is exclusive. Missing, changed, unopened or expired policies stop the guarded
command. A clock moving backwards during the comparison also refuses. If expiry
occurs while the model runs, no partial result folder is written.

The short summary says whether the **caller-declared window** passed; it still
reports actual reference freshness as **unestablished**. With `--details`, a
separate `reference-window-check.json` saves exact check times and binding hashes
in your private result folder. Those details can link information: keep them
private. The existing `reference-observations.json` retains its own profile.
Omitting `--review-windows` preserves the earlier workflow. Nobody is silently
enrolled, and no policy file is automatically uploaded or renewed.

### Verify the command

```sh
python3 REPO/scripts/verify-nli-profile.py
python3 REPO/scripts/verify-reference-review-windows.py
PRIVATE/nli-env/bin/python REPO/scripts/verify-nli-references.py --python PRIVATE/nli-env/bin/python --model-cache PRIVATE/nli-assets --output output/verification/nli-reference-controls.json
```

The second command uses invented examples only. Receipts use the checkout's existing `runs/` or `output/` contract. It exercises engineering controls and retains a selection miss; it does not measure independent accuracy. Default CI checks contracts without downloading weights.

Delete your private environment, cache, inputs and results to remove local data. No background service, endpoint, system setting, telemetry or enrollment is installed. A compromised administrator, same-account malicious process, modified checkout or compromised native runtime remains outside these controls. Notices are preserved; qualified licensing review and full signal/tag validation remain open.
