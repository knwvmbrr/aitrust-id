# Offline local MCP installation bundle

This development bundle contains the actual local MCP server and its 30 locked
runtime packages. It is not yet an admitted release: all-target runtime proof and
distinct grant/notice/source review are still required. A format-valid
ZIP does not authorize its distribution. Existing personal PS commands need no
SDK and remain separate.

Select a trusted source checkout independently. From its root, build or inspect
a target bundle with the standard-library tool:

```sh
python3 -I -S -B scripts/mcp-distribution.py build --target cp313-macosx_11_0_arm64 --wheelhouse /absolute/private/wheels --output /absolute/private/checker.zip
python3 -I -S -B scripts/mcp-distribution.py verify /absolute/private/checker.zip
```

The private immediate directory must be owned by you with mode 0700; wheel files
must be 0600. Outputs never replace existing files. Target profiles cover CPython
3.12/3.13 on macOS arm64 (11+) and Linux x86_64 (glibc 2.34+). Windows, musl,
free-threaded Python and other architectures/minors are not qualified. The
interpreter and an existing pip 22.3+ installer are separate prerequisites, not
bundled components. No operating-system or interpreter installation is performed.
Installation requires a 2 GiB free-space reserve plus 128 MiB working allowance.
A fixed capacity refusal creates no new installation workspace or connection file.

Install only into a new owned private workspace using an existing matching
interpreter and your explicit existing pip interpreter:

```sh
python3 -I -S -B scripts/mcp-distribution.py install /absolute/private/checker.zip --output /absolute/private/connection.json --python /absolute/existing/python3.13 --pip-python /absolute/existing/pip-environment/bin/python
```

Installation creates a pip-free venv, installs only the exact selected wheels
offline without dependency resolution or builds, and checks that precisely the
30 expected runtime distributions are installed. Private `connection.json`
contains actual MCP launch paths; use it with a host supporting local stdio MCP.
No path or configuration is printed to stdout. Keep the sibling owned workspace
while using that connection. The installer preserves the existing HOME unchanged
and strips inherited service credentials, proxies and pip configuration, using
only task-specific temporary/configuration paths. It does not install a privacy service or models,
read a service environment, open HTTP or send inspected text to a server.

The two tools are `list_tags` and `check_text`. PS remains a development pattern
check. PII_REDACTED optionally uses your separately selected existing local
service; a missing privacy service must not erase PS. No input is included in
this artifact, uploaded for research, or treated as code to execute. See
[the application guide at the selected baseline](https://github.com/knwvmbrr/aitrust-id/blob/cd3beab02774fa939e3a2bd8a0d87913d9e8fd81/docs/ai-tools.md)
for method and host privacy boundaries.

Verify the installed source and each unchanged wheel payload against the selected
trusted source and retained ZIP. Then run the fixed invented stdio exercise:

```sh
python3 -I -S -B scripts/mcp-distribution.py verify-install /absolute/private/checker.zip --connection /absolute/private/connection.json --python /absolute/existing/python3.13
python3 -I -S -B scripts/mcp-distribution.py probe /absolute/private/checker.zip --connection /absolute/private/connection.json --python /absolute/existing/python3.13
```

The probe verifies modern and legacy tool discovery, complete canonical PS
records, unsupported/oversized request refusal and optional-privacy isolation.
It uses the same frozen method, providing mechanism parity rather than independent
accuracy. It uses only authored synthetic input and an absent private privacy
configuration; it never reads your service credentials or runs a privacy service.
An SDK/worker failure remains Unavailable. No caller input is evaluated as code.

Refusals have fixed nonleaking diagnostics and exit 2. Prepublication failure
creates no new final output file, but private temporary files/directories can
remain if cleanup fails. After publication, an I/O or close failure returns
`output_commit_uncertain` with `output_may_exist:true`. Inspect the requested
destination and its private directory before retrying; do not assume rollback,
overwrite old data or automatically remove an uncertain installation.

Publisher wheel bytes are preserved. Their license texts and SBOMs remain inside
the wheels; inventory records distinguish declared/observed dependencies from a
complete compiled-closure claim. Project source is Apache-2.0 with root NOTICE;
the assertion schema is separately CC BY 4.0, and the NFC table retains Unicode
terms. Supplemental libffi and scoped Rust standard-library/Unicode/backtrace/
compiler-builtins/libm terms are actually included, with exact source/notice maps
and small replayable source evidence. The format verifies these assets; all-target
runtime and distinct review still control later distribution admission.
Nothing here is full F-057/X-02, independent accuracy, safety clearance, or an
operating organization/privacy service approval.
