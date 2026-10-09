# Site adapters

Each adapter declares, for one AI surface:

* `endpointMatchers` — URL patterns whose response bodies carry model output
* `extract(raw)` — parse that vendor's SSE / JSON-lines into plain text
* `containerSelector` — where the rendered response lives, for the DOM fallback
* `mountSelector` — where the label bar is appended, for the badge

Adapters are the only vendor-specific code in the project. When a vendor changes their
API, exactly one file needs to change and the DOM fallback covers the gap in the meantime.
