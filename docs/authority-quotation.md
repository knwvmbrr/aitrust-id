# Inspect authority wording in quotation context

This optional, local command separates supported authority phrases inside ASCII
double quotes from phrases outside them. It helps inspect a quotation-context
gap in the older authority observation; it does not issue MT or other tags.
It is not selected automatically by `check-mt-evidence.py`. The combined workflow
now accepts the separate explicit `--check authority-quotation` option, with a
versioned full-record adapter and bounded canonical replay; see
[the workflow guide](https://github.com/knwvmbrr/aitrust-id/blob/main/docs/mt-quotation-workflow.md).

Use Python 3 from the repository root. Supply selected English text through stdin:

```sh
printf '%s' 'The example says "Experts agree"; studies show benefits.' |
  python3 scripts/authority-quotation.py --language en
```

The brief JSON reports one quoted phrase and one outside phrase without a local
marker. It includes no input text, subject hash or evidence locations. A zero
exit status means the supported inspection completed, not that the text passed
a trust or safety check. Exit status 2 with `UNAVAILABLE` means no valid result
was obtained; do not treat that as zero observations.

For exact evidence locations, choose a **new folder inside an existing private
0700 directory outside the checkout**:

```sh
python3 scripts/authority-quotation.py --language en \
  --details /absolute/private/directory/new-observation < /private/selected-text.txt
```

This creates `authority-quotation.json` with mode 0600 in a new 0700 folder. An
existing destination, symlink or nonprivate parent is refused. No input is saved
by this command. Details contain an NFC-normalized subject SHA-256, exact Unicode
codepoint spans, normalization identity, source fingerprints and method
`ascii-quoted-authority-observations/1.0.0`. Hashes and locations can still link
private information: keep this file private and share it only deliberately.

## What the counts mean

| Field | Literal observation |
| --- | --- |
| `outside_supported_quotes_without_marker` | Supported authority phrases outside the supported quotes, without an outside marker in the same literal unit. |
| `outside_supported_quotes_with_marker` | Outside phrases sharing that unit with an outside URL or `[number]` marker. |
| `quoted_phrase_count` | Supported phrases inside a supported quotation, retained separately regardless of markers. |
| `supported_quote_count` | Balanced ASCII double-quote pairs, including empty pairs. |

`OBSERVATIONS` means the first count is nonzero. `NO_SUPPORTED_PATTERN` means
that count is zero; check the other counts for quoted or marked phrases. Neither
state establishes authorship, endorsement, accuracy, coercion or manipulation.

URLs and `[number]` strings are **markers**, not verified sources. No lookup is
performed, and same-unit proximity does not establish semantic attribution.
Quoted and unquoted marker contexts stay separate. Different quotes cannot lend
markers to each other. Outside segments can share an outside marker in the same
literal unit even when quoted material lies between them.

## Boundaries

This candidate reuses the older English phrase vocabulary and literal sentence
units. It does not infer language, parse complete grammar, interpret negation or
resolve who endorses a quotation. It scans alternately paired, unescaped ASCII
`"` characters; it does not infer nesting. Single quotes and apostrophes are
ordinary characters, so a single-quoted phrase remains outside the supported
double-quote grammar. It refuses curly double quotes, guillemets, backticks,
escaped ASCII quotes and unmatched double quotes across the selected subject.
No unsupported quote form is silently repaired.

The full input is limited to 8,000 characters before and after frozen NFC
normalization and 32,000 UTF-8 bytes. The candidate also caps quote pairs at 64,
phrases at 128, nonempty literal units at 512 and source markers at 256. Excess,
invalid Unicode, NUL and empty input yield Unavailable with a fixed diagnostic.

The existing urgency, authority and other MT components retain their original
method contracts and selection behavior. Failure to import this optional
candidate does not prevent those existing executables from running. All examples
and checks here are authored controls, not independent accuracy evidence.

Run the bounded executable controls:

```sh
python3 scripts/verify-authority-quotation.py
python3 -m pytest -q tests/test_authority_quotation.py
```
