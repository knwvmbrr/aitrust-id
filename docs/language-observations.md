# Check wording without judging the writer

Three independent offline checks let you inspect particular features of English
text. They return observations and positions, not HP or MT tags. No account,
model download, service or network is needed. Use Python 3.12 in a source checkout.

**Urgency:** look for literal time-pressure phrases alongside a measured proportion
of sentence units starting with supported directive verbs.

```sh
python3 scripts/language-observations.py urgency --language en < /path/to/text.txt
```

**Authority:** look for supported appeals to expertise or consensus without a
source marker in the same sentence unit.

```sh
python3 scripts/language-observations.py authority --language en < /path/to/text.txt
```

**Uncertainty:** select the text where you expect uncertainty first. The checker
does not decide this for you. Create a private annotation file with an NFC subject
hash and codepoint ranges. One way to prepare it without putting text on the
command line is:

```sh
install -d -m 700 "$HOME/aitrust-language-context"
python3 - /path/to/text.txt "$HOME/aitrust-language-context/context.json" <<'PY'
import json, os, sys
from pathlib import Path
from protocol.normalization import normalize_nfc
from tools.language_observations import digest, subject_text
text = subject_text(Path(sys.argv[1]).read_text(), 'en')
record = {'format': 'language-context-annotations/v1',
          'subject_sha256': digest(text),
          'uncertainty': [[0, len(text)]], 'sources': []}
with os.fdopen(os.open(sys.argv[2], os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as out:
    json.dump(record, out)
PY
python3 scripts/language-observations.py hedge --language en \
  --annotations "$HOME/aitrust-language-context/context.json" < /path/to/text.txt
```

That example explicitly marks the whole text as an expected uncertainty context.
Use narrower ordered, nonoverlapping ranges when only selected claims warrant
uncertainty. Optional `sources` ranges document where you supplied a source;
they do not verify it. A hash mismatch is unavailable, never a finding.

`OBSERVATIONS` means the selected pattern matched. `NO_SUPPORTED_PATTERN` means
this specific check did not find it. `UNAVAILABLE` means it could not obtain a
valid observation; it exits 2. A completed check exits 0. Output contains no input
text, but positions and its subject hash can reveal or correlate information.
Keep the output private unless you have reviewed it for sharing.

## Published method

Method: `english-context-observations/1.0.0`. Language is explicitly caller-selected
English. Input limit: 8,000 characters; at most 32 annotations of each kind.
Positions refer to frozen NFC-normalized text, in Unicode codepoints.

The hedge lexicon is `may`, `might`, `could`, `possibly`, `perhaps`, `probably`,
`likely`, `unlikely`, `uncertain`, `unclear`, `approximately`, `roughly`,
`estimated`, `estimate`. A `may` followed by a day number is excluded as a
calendar candidate. Negation is not treated as removing uncertainty: “not likely”
still contains a hedge. Word sense, complex negation and every possible way to
express uncertainty are not resolved. A literal lexicon's absence is weak
evidence, even in a context you selected.

Time-pressure phrases: `now`, `today`, `immediately`, `right away`, `last chance`,
`act fast`, `before it is too late`, `within N minutes/hours` (N has 1–4 digits).
Directive verbs at the start of a sentence unit, optionally after “please”:
`act`, `buy`, `click`, `send`, `pay`, `transfer`, `sign`, `choose`, `join`, `call`,
`run`, `install`, `download`, `stop`, `leave`, `evacuate`, `check`, `verify`, `read`,
`submit`, `respond`, `decide`, `take`. Units end at a newline or `.`, `!`, `?`
followed by whitespace/end. This keeps ordinary URL/decimal dots together but is
not a full sentence parser. Density is directive units / all nonempty units.
Default minimum: 0.5; set `--minimum-density` from greater than 0 through 1.
This is a lexical parameter, not a validated manipulation threshold.

Authority phrases: `experts agree`, `studies show`, `research proves`,
`scientists agree`, `everyone knows`, `doctors recommend`, `authorities say`,
`according to experts/science/research`. Source markers are HTTP(S) URL syntax,
bracketed numeric citations with 1–4 digits, or explicitly supplied source ranges
overlapping that unit. Marked appeals are retained separately; links are not
visited. Attribution elsewhere and named people outside the lexicon are not
resolved. A missing local source marker is not proof that the claim is false.

## Annotation and interpretation guide

- Separate literal pressure from intent. “Leave now; call emergency services”
  has legitimate urgency. It must not be labeled manipulation by this component.
- Quoted examples and news reports can contain the same patterns. The observations
  retain positions; they do not infer whether text is advice or discussion.
- A sale deadline can be ordinary persuasion. Additional contextual evidence and
  independent agreement are required before MT can make its own conclusion.
- A hedge observation depends on the expectation you supplied. Do not invent that
  expectation from a detector's output or call your annotation independent review.
- Citation syntax can be bogus. Its presence is recorded, not trusted as evidence
  that a passage, person or result exists.

F-018, F-019a and F-019c remain distinct signal jobs. They do not complete their
parent HP/MT tags, the false-dilemma/NLI jobs, human annotation agreement or any
tag release gate. Controls: `python3 -m pytest tests/test_language_observations.py -q`.
