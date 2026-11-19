# Inspect quotation placement beside your other MT observations

Use the existing local command and select the quotation check explicitly:

```sh
python3 -I -S -B scripts/check-mt-evidence.py --language en \
  --check authority-quotation < /your/private/message.txt
```

For `The training example says "Experts agree".`, the short result reports one
quoted phrase and zero outside phrases without a local marker. That differs from
the older `--check authority` observation, which does not classify quotation
context. Both are still available under their own names. No substitution, default
selection, MT tag or intent judgment is introduced.

To look for urgency independently in the same text:

```sh
python3 -I -S -B scripts/check-mt-evidence.py --language en \
  --check urgency --check authority-quotation < /your/private/message.txt
```

Only selected checks run. Unsupported quotation syntax, a missing optional module,
a timeout, malformed evidence or a failed replay makes the quotation component
Unavailable. Completed urgency, legacy authority and choice observations are
retained. Missing choice context affects choice only, not this check.

The command requires the source checkout and Python 3.12+ on macOS/Linux, with no
third-party package, Docker, account, model or service. Download the repository or
clone `https://github.com/knwvmbrr/aitrust-id.git`, enter `aitrust-id`, then run the
command above. Text comes from your stdin; the command creates no input file,
upload, telemetry or training enrollment. These changes do not mount a new site
or app route or change the existing browser explorer.

## What the observations mean

This route reuses **unchanged** `ascii-quoted-authority-observations/1.0.0`.
It reports supported authority phrases inside balanced unescaped ASCII double
quotes, outside those quotes with a same-literal-unit outside source marker, and
outside without one. A URL or numbered marker is not a verified source. Markers
cannot be borrowed from another quotation context. No phrase means no supported
literal vocabulary matched; it does not clear the text.

Quote placement does not establish use versus mention, endorsement, semantic
attribution, negation, coercion or manipulation. Single quotes remain ordinary
characters under this exact existing grammar; it does not infer nested quotes.
Curly double quotes, guillemets, backticks, escaped/unmatched double quotes and
existing quote/phrase/unit/marker caps refuse instead of being repaired. See the
[canonical method boundaries](authority-quotation.md).

## Private details and identity

The console shows short counts only. To save the entire evidence record,
explicitly choose a new directory inside an existing owner-held 0700 directory
outside the checkout:

```sh
python3 -I -S -B scripts/check-mt-evidence.py --language en \
  --check authority-quotation --details /your/private/new-result \
  < /your/private/message.txt
```

The new directory is 0700 and `framing-evidence.json` is 0600. Existing destinations
are refused without overwriting. Delete your own files when no longer needed.
The detailed record includes raw UTF-8 SHA-256/count/bytes, frozen Unicode 15 NFC
subject identity, exact method/source identities, counts, quote/unit/phrase/marker
positions and the entire unmodified canonical record. It contains no input text
or private input path. Hashes and positions can still reveal or link information;
keep this evidence private and share it deliberately.

Selections containing this check use
`independent-framing-context-evidence/v1`. The new component row is
`framing-quotation-component/v1`. Legacy-only selections retain
`independent-framing-evidence/v1` and their existing row shapes and methods.

## How the software verifies the record

The parent accepts only closed outer/canonical/nested schemas, exact raw and NFC
subject identities, source fingerprints and bounded typed spans/counts. Unknown
fields are refused before any result or details are exposed. A shape-correct
record could still omit a finding or move its context, so the parent also asks a
second bounded child to execute the actual canonical method and compare the
**complete strict JSON record**. Changed evidence, coherent omissions and numeric
boolean substitutes cannot pass as the canonical result.

Both child executions share one six-second component budget. The supervisor
retains its existing one-million-byte output cap and 200,000-byte request cap.
The optional full-record adapter is capped at 100,000 serialized bytes, leaving
space for input and replay framing. Larger records are Unavailable in full,
never clipped. This is subprocess fault containment, not an OS network sandbox
or protection from a compromised computer/modified checkout.

The second execution is the **same method**, not an independent source, vote,
accuracy assessment or reviewer. No combined score or corroboration is claimed.
Full MT still needs wider contextual methods, accepted error/annotation policy,
independent blinded labels/agreement and human accessibility/route acceptance.
T-MT and F-019c are not closed by this software increment.

Reproduce the affected engineering controls with the existing pinned test setup:

```sh
python3 -m pytest -q tests/test_mt_quotation_workflow.py \
  tests/test_mt_workflow.py tests/test_authority_quotation.py
python3 scripts/verify-mt-quotation-workflow.py --output output/verification/mt-quotation-workflow.json
```
