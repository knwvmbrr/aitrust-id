# What changed, and where does the wording appear?

Compare a few parts of a new draft with an earlier draft and the context you
choose. Everything runs on your computer. Nothing is captured or uploaded.
This is a free review tool, not an authorship detector or a released PA/FA tag.

The result sorts your selected wording into three groups:

- **Already in the earlier draft.** That exact wording was there before.
- **New wording found in supplied context.** It appears in at least one context document.
- **New wording not found in supplied context.** Read the wording and context together. An absent phrase does not explain where the idea came from.

For example, the context might say `2 + 2`, and the new draft might say `4`.
The literal `4` is absent, but the answer follows from the context. A paraphrase
can also have no exact match. Neither case establishes outside knowledge,
human authorship or AI authorship. Supplied context may be incomplete or wrong.

## Try the small practice example

Use Python 3.12 or newer on macOS or Linux and a current source checkout. No
account, Docker, model download or server is needed. From the repository:

```sh
install -d -m 700 "$HOME/AITrust-ID-review"
python3 scripts/prepare-session-revision-demo.py \
  --output "$HOME/AITrust-ID-review/revision-practice"
python3 scripts/review-session-revision.py \
  --previous "$HOME/AITrust-ID-review/revision-practice/previous.txt" \
  --current "$HOME/AITrust-ID-review/revision-practice/current.txt" \
  --context "$HOME/AITrust-ID-review/revision-practice/context.json" \
  --selections "$HOME/AITrust-ID-review/revision-practice/selections.json"
```

Expect one selected part, one new literal not found in context, and
`"tag_asserted": false`. This deliberately uses the arithmetic example above.
The output is a prompt to review the wording, not an accusation or a score.
If the practice folder already exists, choose a new name; the tool never
overwrites it.

To keep individual locations, repeat the comparison with
`--details "$HOME/AITrust-ID-review/revision-details"`. That creates a new
private folder. The ordinary console result shows counts only. Private details
include source identifiers, hashes and locations, which can link content.
Preview them before sharing. Deleting your original cannot recall a shared copy.

## Compare your own drafts

1. Save the earlier and current draft as UTF-8 text files in a private folder
   outside the checkout. An earlier draft may be empty; the current draft may not.
2. Build a context file using the [local reference corpus tool](local-reference-corpus.md).
   Include only context you have permission to use. This tool does not verify its origin or completeness.
3. Choose the parts to review. A private `spans.json` file contains a JSON array
   such as `[[14,15]]`: start position inclusive, end exclusive, starting at zero.
   Positions count Unicode codepoints after the project's frozen NFC normalization,
   not bytes, screen columns or JavaScript UTF-16 units. Use sorted, non-overlapping
   spans. Each must select nonblank wording.
4. Bind those selections with the preparation command below. It calculates the
   version hashes for you. Then run the comparison with its new selections file.

```sh
python3 scripts/prepare-session-selections.py \
  --previous "$HOME/AITrust-ID-review/my-revision/previous.txt" \
  --current "$HOME/AITrust-ID-review/my-revision/current.txt" \
  --context "$HOME/AITrust-ID-review/my-revision/context.json" \
  --spans "$HOME/AITrust-ID-review/my-revision/spans.json" \
  --output "$HOME/AITrust-ID-review/my-bound-selections"
python3 scripts/review-session-revision.py \
  --previous "$HOME/AITrust-ID-review/my-revision/previous.txt" \
  --current "$HOME/AITrust-ID-review/my-revision/current.txt" \
  --context "$HOME/AITrust-ID-review/my-revision/context.json" \
  --selections "$HOME/AITrust-ID-review/my-bound-selections/selections.json"
```

Both commands require owner-held regular files with mode 0600, in directories
with mode 0700. Symlinks, hardlinks, pipes and files inside the source checkout
are refused. Keep private wording out of shell arguments and Git.

Each draft is limited to 8,000 characters after normalization. Select 1–32
parts. Context supports up to 32 documents within the existing corpus limits.
The comparison is case-sensitive and finds the first exact normalized occurrence
in each document. It does not compare meanings, prove derivation or rank sources.

Editing a draft or context invalidates the old selection binding. Reprepare
selections for that exact version, checking the positions again. Changed inputs,
unsupported fields or unsafe files produce `UNAVAILABLE`, not a finding.

## Verify the tool

```sh
python3 -m pytest tests/test_session_revisions.py -q
python3 scripts/verify-session-revisions.py \
  --output output/verification/session-revisions.json
```

These checks use invented material. They exercise the command and private-file
controls; they are not independent accuracy evidence. Human context review and
the original outside-knowledge hypothesis remain separate acceptance work.

[Read the architecture](session-revision-plan.md) · [Read the executed result](session-revision-result.md)
