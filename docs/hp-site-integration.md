# HP browser preview integration

The HP modal now mounts the existing `HPExplorerSlot` independently of PS and MT.
The literal-detail explorer accepts explicit user input, retains its exact
canonical quantitative method, and issues no HP tag. The display name is **Claim details**; the formal name remains **Hallucination
possible**, shown under How it works. The tile stays **Coming Soon** for the full
HP claim. Availability text distinguishes the usable method
preview from that future release. Static HP reference pages link its complete
use/privacy guide.

Website preparation invokes `scripts/build-hp-device.py` after the existing
runtime preparation and publishes `docs/hp-device-explorer.md`. Root npm aliases
provide `build:hp-device`, `test:hp-device` and `verify:hp-site`. The component,
client, worker, validator and canonical sources are unchanged from the reviewed
standalone increment. No upload, account, local storage, offline-cache promise,
new endpoint or independent accuracy claim is added.

The primary integration risks are accidentally promoting the full tag, loading
or sharing a worker implicitly, letting an optional chunk failure affect the
React root, stale evidence reaching edited input, and narrow enlarged-text
layout. `scripts/hp-site-controls.cjs` checks the built site under ordinary CSP,
compares complete native-Python records, checks details only after opt-in,
cancels on edit/Clear/unmount, inspects requests/storage, verifies 320px at 200% reflow
and minimum action sizes, and refuses the actual HP child chunk before running
actual PS and MT checks in the same browser context. It binds source and served
JS/CSS/HP artifacts before/after its execution. Chromium and WebKit run
sequentially on its own random loopback port; only its own resources are closed.

The shared site verifier invokes the same HP control and understands HP's
additional private-details disclosure and preview availability. It does not
reclassify HP as a released working tag or remove existing PS/MT controls.

The PM separately requested the NF offline guide link and accurate caller-selected
literal/cosine wording in the shared catalogue/use copy. NF stays planned; this
is not a website NF checker. The NF source/guide and its prepared public copy are
integrated by the PM before publication. This branch does not modify NF methods
or claim that its currently absent public guide has been published.

## Reproduce after the ordinary site setup

Use the per-module dependency/setup instructions in
[the HP explorer guide](hp-device-explorer.md). With those pinned dependencies
already installed and the existing verification virtualenv on PATH:

```sh
npm run build:site
npm run verify:hp-site
```

The targeted verifier builds no files and must run against a fresh `site/dist`.
It writes its report to `output/verification/hp-production-site.json`; set
`AITRUST_HP_SITE_REPORT` to a new `runs/*.json` path to preserve a public immutable
execution record. Screenshots are in ignored `output/playwright/`.

A passing run is software integration evidence, not physical iPhone, human
screen-reader acceptance, independent contextual accuracy, HP release validation
or a completed parent requirement. Deployment, global source-bound route review,
scope/state and final publication remain PM-owned.
