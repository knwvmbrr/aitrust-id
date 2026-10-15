# Check your implementation

Use the same public examples to find protocol differences before integration.
No account, service or real AI conversation is needed. The examples are invented.

```sh
python3 scripts/check-conformance-vectors.py
python3 scripts/check-conformance-vectors.py --implementation python3 /path/to/your/checker.py
```

Install the repository's hash-locked gateway requirements in your virtual
environment for the reference Python schema checker. Node is also required for
its extension profile. To run only one profile, put `--profile schema` or
`--profile extension` before `--implementation`.

## Adapter contract

Supply a trusted executable followed by its arguments. No shell interpretation
occurs. The harness appends `--profile schema` or `--profile extension`, writes one
UTF-8 JSON record to stdin and closes stdin. Start a fresh process for each case.
Return one JSON object on stdout containing:

```json
{"status":"accepted","profile":"schema","supported_version":"0.1.0","offline":true,"signature_verified":false,"independent_accuracy_verified":false,"certification":false}
```

Use `invalid`, `unsupported` or `unavailable` as appropriate. Their process exits
are 1, 2 and 3; `accepted` exits 0. Additional fields are ignored, never forwarded.
Only this offline structural/profile check is requested; signature, accuracy and
certification flags must remain false. Output must fit 8 KiB and finish within
three seconds. Timeout, malformed output, missing tools, excessive output or
wrong exit/status fail the run. Arbitrary output and command arguments are not
printed in the report.

The schema profile checks wire syntax including date and UUID formats. The
extension profile also refuses unsupported runtime capabilities, untrusted
signatures, duplicated tags, invalid floors and spans outside the subject.
A future wire version returns Unsupported rather than guessing a migration.

## What a pass establishes

The [versioned vectors](https://github.com/knwvmbrr/aitrust-id/blob/main/eval/conformance/assertion-v1.json) contain 14 cases,
run under both profiles for 28 checks. Each result identifies the case, expected
and observed state, process exit and response digest. The report binds the vector
and harness/reference source files; changed sources during the run prevent a
pass. Save stdout if you want a local report:

```sh
python3 scripts/check-conformance-vectors.py > conformance-result.json
```

A pass means these selected interface cases matched. It does not authenticate the
implementation executable, capture its complete dependency tree, prove all
protocol behavior, establish accuracy, replace an outside person's acceptance or
release a tag. A supplied executable can access your files and network with your
permissions. Process deadlines and output limits are resource controls, not a
security sandbox. Never run an untrusted implementation on your own computer.
