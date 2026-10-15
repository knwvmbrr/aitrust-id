# Inspect the evidence in a source download

An evidence packet makes it easier to tell what actually ran and what still
needs work. From the downloaded repository, run:

```sh
python3 scripts/build-evidence-packet.py > evidence-packet.json
```

The command inspects the five execution receipts selected in `state.json`: PS,
privacy redaction, protocol, extension and website. It compares their recorded
source files, commands and outcomes with this checkout. It does not rerun those
commands or start any service. The JSON includes each receipt's digest, current
or stale status, refusal reasons, a combined public-file digest inventory and
all open acceptance records. Missing or broken evidence is shown as a failure,
not omitted.

Use this stricter command when current engineering evidence is required:

```sh
python3 scripts/build-evidence-packet.py --require-current > evidence-packet.json
```

Exit 0 means an index was assembled; with `--require-current`, all five selected
engineering checks must also be current. Exit 1 means the source changed during
inspection or the required current checks failed. Exit 2 means the index itself
could not be assembled. Read `packet_valid` separately from
`engineering_checks_current`. No result from this command grants release.

The packet only indexes public files already in the source download. It does not
include private responses, publish feedback or contact a server. Digests identify
files; they are not signatures. Use the separate [source verification
instructions](https://github.com/knwvmbrr/aitrust-id/blob/main/docs/source-provenance.md) to authenticate a signed source download
before executing its code. An authenticated download can still contain failed,
stale or incomplete evidence; authentication does not make those checks pass.

[Versioned interoperability vectors](conformance-runner.md) test selected
protocol cases. Independent accuracy, human accessibility, physical-device use,
license review and outside-person acceptance keep their own open requirements.
