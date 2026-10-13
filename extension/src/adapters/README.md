# Site adapters

The installed extension has one supported adapter: ChatGPT's rendered assistant
responses. Its interface supplies `responses`, `responseId`, `text`, `streaming`,
`anchor` and `site` to the user-invoked content bridge. It does not read prompts or
automatically intercept the vendor's network stream. Changed markup can make the
adapter unavailable; there is no guaranteed fallback.

`../main-world/stream-observer.mjs` is an inactive developer component. No manifest
entry or installed script imports it. It observes only an explicitly supplied
Response using a synthetic, closed assistant-text profile. It has no vendor URL
matcher, fetch patch, message broadcast or tag mapping. See
[the stream observer plan](../../../docs/stream-observer-plan.md) for its limits.
F-030 still needs a supported live vendor contract and workflow acceptance, or an
accepted decision replacing that capture route. A local stream test cannot close it.
