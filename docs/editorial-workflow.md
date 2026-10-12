# Review an AI answer in your editorial workflow

Keep the AI Trust ID finding and your editorial decision side by side. You can review, disagree, hold an item back and record a correction without changing what the tag reported. Your files stay with you. There is no account, upload or signup gate.

This free open-source tool runs on Linux or macOS. Its private HTML view works offline in a browser. It uses the existing personal checker; it does not add a newsroom CMS plugin, authenticate a reporter or determine whether an answer is true.

## Start with an invented example

From your downloaded repository, install the existing pinned Python dependencies once. This is a separate development environment, with no Docker or service to start:

```sh
python3 -m venv .editorial-venv
. .editorial-venv/bin/activate
python3 -m pip install --require-hashes -r services/gateway/requirements.lock -r eval/requirements.lock
```

Use a new private folder outside the repository. The following commands create invented practice files. They do not read your messages or run the command inside the example:

```sh
AITRUST_REVIEW_HOME="$HOME/AITrust-editorial-practice"
install -d -m 700 "$AITRUST_REVIEW_HOME"
python3 scripts/prepare-editorial-demo.py --output "$AITRUST_REVIEW_HOME/input"
```

Read `input/source.json` and `input/subject.txt`. Choose your decision, then make the review packet:

```sh
python3 scripts/prepare-editorial-review.py \
  --source "$AITRUST_REVIEW_HOME/input/source.json" \
  --subject "$AITRUST_REVIEW_HOME/input/subject.txt" \
  --reviewer editor-one --decision needs_review --reason needs_context \
  --output "$AITRUST_REVIEW_HOME/packet" --reviewed-record
python3 scripts/editorial-review.py \
  --packet "$AITRUST_REVIEW_HOME/packet" \
  --output "$AITRUST_REVIEW_HOME/first" --reviewed-record
```

Open `first/editorial-review.html`. You will see the source finding as a small expandable tag and your decision in a separate section. `first/editorial-review.json` records exact file and method identities, the decision and its limits. The console gives only a brief result.

Existing output folders are refused. For another review, choose new packet and output names.

## Review an answer you selected

On the PS modal, choose **Check on this device**, paste the answer and choose **Check answer**. To import its detailed evidence, open **Detailed record for reproduction**, deliberately select **Include fingerprints and evidence positions**, then **Download detailed record**. This exports `ai-trust-id-ps-record.json`. It does not include the answer text.

Place that file in a private input folder and save the exact answer you checked as `subject.txt`, encoded as UTF-8. Set both files to mode `0600` and their private folder to `0700`. Use the same two review commands above, selecting these files explicitly. The importer checks that the normalized text, positions, current method, bundle, runtime and result format agree.

**Download summary** intentionally omits fingerprints and positions. It cannot bind this review and is refused. A detailed download is still an unsigned preview, not an independently validated tag or proof of who produced it.

The other supported input is the current unsigned gateway wire assertion, version `0.1.0`, with its complete preprocessing identity. Select the exact **already-redacted evaluated text**, not the original text before redaction. Current PS and procedural PII_REDACTED findings are retained separately. A historical or different method, signature requiring unimplemented trust verification, unsupported code, malformed record, mismatch or changed file is refused rather than reinterpreted. Vendor manifest and watermark evidence are not converted into content truth.

The web preview accepts up to 20,000 characters; a current gateway record accepts up to 200,000. The private reader preserves each producer’s own limit, including multi-byte UTF-8 text. Every PS finding must include evidence positions and a score consistent with its recorded signals.

## Choose what you mean

| Decision | Meaning |
| --- | --- |
| `needs_review` | The named editor wants another look. |
| `reviewed` | The editor reports completing their review. This is not a verified-content badge. |
| `withheld` | The editor is holding the item back. This does not accuse its author. |

Reasons are `needs_context`, `source_checked`, `disagreed`, `privacy` or `scope_mismatch`. Your declared reviewer handle is 3–64 lowercase letters, digits, underscores or hyphens. It is not authenticated. Nothing automatically becomes a training label, public assertion, receipt, certification or release approval.

## Record a correction

Keep the first record. Select its exact private JSON as `--previous`, use new packet and output folders, then run with `--supersede`:

```sh
python3 scripts/prepare-editorial-review.py \
  --source "$AITRUST_REVIEW_HOME/input/source.json" \
  --subject "$AITRUST_REVIEW_HOME/input/subject.txt" \
  --reviewer editor-one --decision withheld --reason disagreed \
  --previous "$AITRUST_REVIEW_HOME/first/editorial-review.json" \
  --output "$AITRUST_REVIEW_HOME/correction-packet" --reviewed-record
python3 scripts/editorial-review.py \
  --packet "$AITRUST_REVIEW_HOME/correction-packet" \
  --output "$AITRUST_REVIEW_HOME/correction" --reviewed-record --supersede
```

The correction binds the earlier journal’s exact bytes. It cannot replace the source findings or overwrite the first journal. Keeping both gives you the selected local history; it does not prove no other private history exists.

## Keep sharing deliberate

The HTML omits the evaluated text by default. To include it privately, add `--include-subject` to the review command. This is a separate choice; it can expose personal or confidential information. Browser previews perform no redaction, and gateway redaction can miss information.

Source identifiers, method identities, subject fingerprints and evidence positions in the JSON can link or reveal content. Hashes do not provide anonymity. Review every file before sharing. Sharing or copying files outside this tool is your decision and is not controlled by this workflow. Nothing is forwarded to an in-house database.

The source is not authenticated. Matching identities show consistency with the selected checkout, not that the source producer actually ran that code. This review is separate from blind independent validation; an owner’s review cannot substitute for that release evidence.

## Remove it

Delete only the private practice or review folders you created when you no longer need them. Your original answer and source record, personal checker, repository and other tools remain separate. If you installed the optional `.editorial-venv` solely for this workflow, deactivate it and remove that environment. This tool starts no service and creates no browser account, persistent storage or automatic background collection.

## Check this workflow yourself

```sh
python3 -m pytest tests/test_newsroom.py tests/test_editorial_cli.py -q
node scripts/verify-editorial-workflow.cjs
```

The browser verifier needs the repository’s normal prepared site build and existing Playwright/axe dependencies. It uses invented input, the actual detailed browser download, private commands, corrections, offline Chromium/WebKit views, light/dark themes, 320-pixel reflow, keyboard expansion and automated accessibility checks. It removes its own temporary files. These are engineering checks; they do not constitute physical-phone testing, human accessibility acceptance or independent tag accuracy validation.
