# Agent tag API and MCP plugin

Owner request: let AI applications call individual tags as tools. The existing
agent-output recorder remains a separate capability: recording the origin of an
answer is different from checking its contents.

## Architecture

A small Python API will wrap the existing independent tag runner. A separate MCP
stdio adapter will expose discovery and a bounded check tool using the official
MCP Python SDK. No public listener, new HTTP endpoint, account, payment or research
submission is introduced. The existing authenticated gateway API remains usable
by applications which already operate it.

The initial supported checks are PS and optional PII_REDACTED. PS runs locally
without a gateway. PII_REDACTED uses only the already configured loopback service;
a missing or failing privacy service must leave PS usable. Planned tags are not
advertised as working tools. Every result preserves each tag's own state and method.

The default output is a brief structured summary with supported signal identifiers,
counts and method identity. It excludes submitted text, redacted text, subject
hashes, offsets, source URLs supplied by users and the original assertion. It
cannot certify an answer, establish authorship or turn development scores into
measured accuracy. Findings and tool availability are different concepts.

## Risks and controls

The connecting AI host already knows the text it submits. Local checking does not
control that host's retention or disclosure. Untrusted text is stdin data and never
executed, interpolated into a shell, or used as a path or destination. Tool arguments
cannot set service endpoints or select credential files. Input is bounded to 20,000
Unicode codepoints and 80,000 UTF-8 bytes. Worker deadlines/output budgets and a
nonblocking admission limit prevent unbounded concurrent checks. A canceled MCP
request must not free capacity while its worker is still running. Unexpected errors
must return fixed messages without argument echoes, stack traces or credentials.
SDK request validation and logging must be tested with deliberately private markers.

The SDK is optional and installed in a separate environment from the detector and
existing service locks. Pin it and its dependencies with package hashes. A missing
plugin dependency must not stop personal checking or the platform.

## Complete implementation acceptance

1. A real official SDK client connects to the stdio subprocess, negotiates, lists
   both tools, calls them, validates structured output and shuts down cleanly.
2. A real PS finding and negative control work without Docker or a token. Calling
   both tags with a missing privacy configuration gives a partial result with PS
   intact. No unsupported tag is silently substituted.
3. Invalid/unknown/oversized inputs, malformed worker output, worker timeouts,
   saturation and cancellation return bounded failures. An unavailable checker
   never becomes No finding. Private input markers are absent from outputs/logs.
4. Users get a runnable host configuration and an agent client example, installation
   and removal instructions, and the existing HTTP API's distinct setup boundary.
5. Record exact verification, attribution, scope and changelog. The plugin's
   implementation is separate from independent tag validation and the 202 existing
   scope records; it cannot close a tag by becoming callable.
