# Run the PS source-only development checker

This archive contains the selected PS command-pattern checker source, its frozen
Unicode normalization data, applicable included notices and these instructions.
It contains no interpreter, operating system, user input, account, service,
model weights, browser extension or other tag implementation. It is not a
whole-repository snapshot described as PS-only.

You need an independently obtained CPython 3.12 or newer on macOS or Linux.
Python and your operating system are external prerequisites, not bundled or
cleared by this source archive. No third-party Python package installation,
account or network connection is required to run this selected checker.

Before extracting, inspect the archive using a separately trusted source
checkout and its current approved dependency-policy profile:

```sh
python3 scripts/export-ps-source.py verify /path/to/ps-source.zip
```

The archive manifest records exact source identities and prerequisites. Its
hashes do not authenticate its publisher. Inspection compares every member with
the trusted checkout policy; a matching manifest from the same untrusted
download is not an independent trust root. Use your normal trusted distribution
or separately verified signature to authenticate the artifact. The export and
inspection commands do not inspect or accept answer text.

After verification, extract into a new private directory, open a terminal in
that directory and run:

```sh
python3 -I -S -B scripts/check-ps.py
```

Paste text you are authorized to inspect, then send end-of-input (Control-D on
an empty line). Or pass the path to your UTF-8 response file:

```sh
python3 -I -S -B scripts/check-ps.py /path/to/response.txt
```

The selected checker reads the evaluator source as an AST and projects its
reviewed PS functions; it does not import the FastAPI service or execute the
inspected command. It normalizes using the included frozen Unicode tables.
Maximum input is 20,000 characters and 80,000 UTF-8 bytes. The isolated worker
has the existing ten-second deadline and bounded result output. A failed check
is Unavailable, never a no-finding result.

A finding identifies a supported download-and-run or encoded-command pattern.
No finding is not a safety clearance. This is a development method, not an
independently validated release, scam-intent judgment or AI-authorship
classification. No personal-information redaction is performed. The checker
does not upload the input. Your terminal, file permissions, Python installation
and OS remain your responsibility.

`--json` explicitly prints metadata including hashes and offsets that can link
to your input; keep it private. It does not include the original input text.
`--fail-on-finding` exits 2 for a finding; exit 1 means Unavailable. Without that
flag both completed result states exit 0. The checker does not save a history.

Included licenses remain at `LICENSE` and `eval/vectors/unicode/LICENSE.txt`.
They do not replace terms for Python or your OS. Removing this extracted
directory removes this source copy; separately owned inputs and exported
metadata remain under your control.

Developers with the reviewed repository can create a new archive using:

```sh
python3 scripts/export-ps-source.py build --output /existing/directory/ps-source.zip
```

The output must not exist. Build and verification refuse links, altered or
missing approved files, unexpected archive members and a non-allowed route.
The deterministic ZIP contains only the exact policy-approved members plus its
generated `.aitrust-ps-source.json` manifest. No interpreter, input text or
private environment is added during export.

## Project attribution — retained from NOTICE

AITrust-ID
Copyright 2026 Michael Raashad McGuire and AITrust-ID contributors.

This is the applicable project attribution from the repository NOTICE. The
separate specification, font, Pyodide and SPDX assets described there are not
included in this source-only package. Their distribution notices remain with
their own artifacts. The retained Unicode notice is included separately above.
