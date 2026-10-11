# Authenticate results before displaying tags

Owner direction, 2026-10-11: reduce the verified open queue from 91 to 50.
The baseline is 111 complete and 202 preserved records. Forty-one additional
full named jobs are needed. This supersedes the earlier queue target of 25;
neither planning nor a component implementation counts as completion.

## Architecture before implementation — F-036

Keep the existing assertion v0.1 JSON and `/v1/evaluate` endpoint. Add a
separate, versioned loopback transport profile using ECDSA P-256/SHA-256.
The gateway uses the maintained Python cryptography library; Chrome uses
native Web Crypto. A user chooses the gateway's public key in local settings.
There is no key-discovery endpoint, trust-on-first-use, additional host
permission, telemetry, or automatic upload.

Each extension request has a new random 256-bit nonce. The signature covers
the profile, nonce, SHA-256 of the exact request bytes and exact response bytes.
The worker bounds the response, authenticates it, then parses and validates
the assertion. Only an authenticated result may reach a verdict badge through
the isolated extension message channel. Wrong keys, replay, altered request or
response bytes, unsupported profiles and missing signatures fail closed.

The private key stays outside source control in an operator-selected, private
regular file. Invalid configured keys prevent startup. Existing unsigned CLI
calls remain compatible; they do not qualify for authenticated extension
display. A signed request to an unconfigured gateway fails before evaluation.
Explicit key replacement cancels pending checks and removes old results.

## Risks and limits

A signature authenticates bytes from the selected key. It does not establish
detector accuracy, human authorship, certification, or safety of a command.
A compromised computer, gateway or chosen key can still sign false results.
Key selection must use a separate trusted operator handoff; receiving a key
from the same untrusted response proves nothing. Rotation requires selecting
the replacement public key explicitly. This bounded profile does not claim
global revocation or transparency-log coverage. Saved replay JSON is not a
portable signed receipt unless its verification context is retained separately.

New dependencies require exact pins, artifact hashes and a real gateway image
build. Preserve existing dependency pins. Check Python-to-browser interoperation,
actual extension rendering, cancellation races, private-file rejection,
negative signature controls, schema compatibility and remote Linux runtime.
Refresh source-bound receipts only after executing changed routes. Publish
scope completion only after its full acceptance is verified, with changelog,
state and run attribution. Human device, independent accuracy, outside-user
and legal acceptance stay open until their own evidence exists.

Author and implementation owner: Codex. Product owner: Michael.
