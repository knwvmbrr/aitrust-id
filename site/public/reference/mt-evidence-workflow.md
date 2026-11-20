# Look at wording, keep the decision

This free local research tool offers four separately selected checks in one command. It
helps you examine a message without judging its writer. Nothing is uploaded.
MT is still in development; these observations are not an MT tag.

From the [downloaded source repository](https://github.com/knwvmbrr/aitrust-id/archive/refs/heads/main.zip),
use Python 3.12 or newer on macOS or Linux:

```sh
python3 scripts/check-mt-evidence.py --language en \
  --check urgency --check authority < /path/to/message.txt
```

- **Urgency:** an instruction and time phrase appear in the same sentence unit.
  “Leave now” can be important safety advice. The tool does not call it manipulation.
- **Authority:** an expertise or consensus phrase has no source marker in the same
  sentence. It does not search elsewhere or check whether a citation is real.
- **Authority quotation (opt in):** add `--check authority-quotation` to keep
  supported ASCII-double-quoted phrases separate from outside phrases. It keeps
  the complete canonical record and performs a bounded same-method replay. It
  does not infer endorsement, negation or semantic attribution. See the
  [quotation workflow guide](https://github.com/knwvmbrr/aitrust-id/blob/main/docs/mt-quotation-workflow.md). The older `authority`
  check keeps its original contract; no automatic substitution occurs.
- **Choice:** the two-choice wording and additional passage **you select** can be
  inspected too. Follow the [private choice-packet guide](choice-framing.md), then
  explicitly add `--check choice --choice-packet /path/to/packet`. Feed the same
  subject text on stdin. A different subject or missing packet makes only choice
  unavailable; it does not change the other selected checks.

Choose only the checks you want. A quiet result means that method did not find
its supported pattern; it does not clear a message. Findings are related lexical
observations, not independent votes or a combined confidence score.

## See the evidence

By default the short result omits your text, fingerprints, locations and private
paths. Add `--details /path/to/new-private-parent/result` to deliberately save
`framing-evidence.json`. Its parent must already be an owner-held mode-0700
folder outside the checkout. The new folder and file use 0700 and 0600, and no
existing destination is overwritten. There is no server or training enrollment.
Delete your local input/result folders when you no longer want them.

Detailed evidence includes exact method/source fingerprints, subject fingerprint,
NFC Unicode-codepoint spans, context sentence/frame spans and selected-reference
fingerprints/locations where applicable. Your text is excluded, but fingerprints
and positions can still reveal or link information. Keep them private. Save the
original source and context yourself if you need to reproduce the observation.

Each selected check runs in its own child process. A crash, timeout, malformed
result or output flood is contained to that check. Supported input is explicitly
selected English, at most 8,000 characters and 32,000 UTF-8 bytes. Each legacy worker has
a six-second wall deadline and one-million-byte output cap. The optional quotation
check uses an observation child and a canonical-replay child within one shared
six-second budget. Its complete record is capped at 100,000 serialized bytes;
an oversized record makes only that check Unavailable, without clipping evidence. The supervisor kills
a failed process group. This is fault containment, not protection against a
modified checkout or compromised computer, and it is not an OS network sandbox.

Exit `0` means all requested observations completed; `3` means a partial result;
`2` means no valid result or refused input/export. These are not severity scores.
No hidden background process remains. No installation, credential or service is
needed beyond the open-source checkout and Python.

## What still needs work

The optional quotation check covers its declared literal placement grammar only.
Broader context/quotation interpretation, genuine versus rhetorical authority, additional-option
feasibility, accepted annotation/error policy, independently blinded labels,
reviewer agreement and human route accessibility remain MT release requirements.
The [published observation methods](language-observations.md) and
[tag contract](tags/MT-01.md) retain those limits. This command does not change
production tag mapping or another tag's availability.

Recheck the actual command with:

```sh
python3 scripts/verify-mt-evidence.py --output /path/to/new-controls.json
```

The controls use invented examples. They are engineering evidence, not a measured
real-world error rate.
