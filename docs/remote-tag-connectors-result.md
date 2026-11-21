# Remote PS connector engineering result

Implementation lane: Codex `/root/web_camo`, isolated `codex/remote-tag-connectors` from e8287050493f3f30b6c92967beed224a6c8b4dc3. Root approved the exact four local code paths before implementation. No shared catalogue, stdio, tag methods, scope/state, endpoint deployment or AI-host account was changed.

The service actually runs: an ordinary JSON API and the installed official MCP2.3.0 Streamable HTTP transport offer the existing PS development check. Both modern2026-07-28 and legacy official clients discover and call it. Complete brief result records match the unchanged local canonical API for a positive and a no-finding example. Requested remote privacy stays explicitly Unavailable; no credential file or local gateway is used.

Current execution: `runs/2026-11-21-remote-tag-connectors-peer-corrected.json`, SHA256 `0df6aff4d47307178e6f83b62cd6078c3ea5880ff06b37ce4b142cbb7d8e730d`. Fourteen focused groups passed with unchanged source identities during execution. These are actual owned-loopback HTTP/official-client/process controls, not a deployed host, independent accuracy or physical-device claim.

The finite controls cover canonical parity; remote privacy isolation; exact Host/Origin and duplicate/framing/compression/UTF-8/size/refusal; a shared request/body deadline; real two-worker admission and one-client cancellation; ordinary/MCP socket disconnect; repeated cancellation and pending-spawn shutdown; wrong/oversized child output; health/catalogue availability during worker saturation; malformed request/string-ID recovery; no URL fetch; and actual CLI private-error/log/startup/shutdown behavior. The output contains only fixed explanations, selected methods and evidence counts, never the inspected text or its subject hash.

## Findings retained, then fixed

- An authored SDK test used the unsupported shorthand `modern`; the installed SDK requires its concrete2026-07-28 protocol date. Its failed receipt remains separate.
- An authored CLI test first compared text to binary logs, then assumed intentional SIGTERM must exit0. The installed pinned Uvicorn0.54.0 source re-raises its captured signal after lifecycle cleanup; the corrected assertion allows only0 or the intentionally sent SIGTERM. The no-input-log/no-fetch and independent worker-cleanup assertions remain.
- Distinct review reproduced a real ownership defect: repeated direct asyncio cancellation during spawn could escape an AnyIO shield, free admission and later leave a child alive. Pending launches are now tracked and cleanup is a separately owned task joined despite repeated caller cancellation; shutdown shares the exact same per-launch reaper. A first correction exposed duplicate concurrent reapers as a source risk; the shared task removes that duplicate kill path. The intermediate failure is retained without inventing its historical cause. Unexpected cleanup failure closes admission and preserves ownership rather than pretending cleanup succeeded.
- Root found integer-only IDs excluded normal clients. Bounded printable string IDs now work through actual MCP HTTP discovery and tool calls. An ID is echoed solely in the protocol envelope, never in the tool result/log/error prose. Ambiguous/overlong/control IDs refuse and a subsequent valid request recovers.

Distinct peer re-review passed at `runs/2026-11-21-remote-tag-connectors-independent-review.json` (SHA256 `f6e9367fa2fc6c6fbb3151f51e647c926a01c9d026d297fa160bd623a907db0d`): the original repeated-cancel countercase with and without concurrent shutdown retained ownership until actual reap, and the actual string-ID HTTP control passed. Root integration/publication remain separate gates; their evidence must bind the final source. Prior candidate and diagnosis records are immutable and must not be relabeled as passing current proof.

## Remaining operating gates

The operator still needs an approved HTTPS deployment/hostname, proxy and infrastructure logging/egress/resource review, current pinned dependency/source-notice acceptance and actual host-specific connection approval. No authentication or user data collection was activated. NoAuth counters are single-instance/global, so they limit work but do not guarantee service availability against distributed abuse. The calling AI host and operator receive selected input; this is not the website's on-device privacy route. No public account connection, licensed model, provider key or external API call is created.

Original scope remains unchanged. This new requested connector enhancement issues no new tag code, declares no independent accuracy, and closes none of the70 remaining original requirements. The existing local stdio and on-device tools continue independently of this optional service.
