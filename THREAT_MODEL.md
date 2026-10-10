# Threat model

The website runs the PS development preview in an on-device worker; it is not a
public server-side evaluator or research intake. The separate authenticated
local service and Chrome adapter have their own boundaries. Dedicated Linux
staging checks use synthetic input and do not activate remote user collection.

This is a maintainer assessment with ten current entries and named accountable
lanes. It is not independent security certification, a guarantee against host
compromise, or evidence that residual release work is complete. Hashes establish
identity, not truth or anonymity. Changing a control, route or source reopens its
verification. The full model-asset and normalization corrections are recorded
in the referenced execution evidence.

| Threat | Accountable owner / lane | Control and evidence | Residual risk / remaining release work |
|---|---|---|---|
| exfiltration | Michael / security | Local/device-only processing and internal service isolation. [runs/2026-10-10-frozen-service-conformance.json](runs/2026-10-10-frozen-service-conformance.json), [runs/2026-10-10-frozen-device-engines.json](runs/2026-10-10-frozen-device-engines.json) | Redaction misses, host compromise and untested covert channels remain possible |
| exposure | Michael / security | Loopback binding, bearer authentication and origin/body/concurrency rejection. [runs/2026-10-10-frozen-service-conformance.json](runs/2026-10-10-frozen-service-conformance.json), [runs/2026-10-10-service-resource-faults.json](runs/2026-10-10-service-resource-faults.json) | Stolen tokens and local malware can invoke the local gateway |
| credentials | Michael / security | No proxy/redirect credential forwarding in the manual checker. [tests/test_local_cli.py](tests/test_local_cli.py) | A compromised owner host can read its credentials |
| hostile_page | Michael / adapters | Escaped rendering, response identity and isolated content-script tests. [scripts/browser-acceptance.js](scripts/browser-acceptance.js), [scripts/live-dom-acceptance.js](scripts/live-dom-acceptance.js) | A vendor page can imitate or remove UI; shadow roots and unsigned records do not authenticate origin |
| supply_chain | Michael / source | Hash-locked packages and pre-load model asset verification. [runs/2026-10-10-model-image-integrity.json](runs/2026-10-10-model-image-integrity.json), [services/anonymizer/requirements.lock](services/anonymizer/requirements.lock) | Trusted-image compromise, floating base-image changes and incomplete SBOM/signing remain open |
| evasion | Michael / independent_review | Input handled as data; development command/use-mention regressions. [eval/datasets/unsafe_code/manifest.json](eval/datasets/unsafe_code/manifest.json), [runs/2026-10-10-frozen-device-engines.json](runs/2026-10-10-frozen-device-engines.json) | Development examples are not independent accuracy evidence; supported patterns are limited |
| collection | Michael / security | No default upload/persistence; minimal export with separate detailed consent. [runs/2026-10-10-frozen-device-engines.json](runs/2026-10-10-frozen-device-engines.json), [site/src/share-record.js](site/src/share-record.js) | Explicit detailed export can link input through hashes/positions; private corpus is deliberately owner-held persistent data |
| vendor_drift | Michael / adapters | Revision/race regression checks and unsupported-route visibility. [scripts/live-dom-acceptance.js](scripts/live-dom-acceptance.js), [docs/runtime-gap-plan.md](docs/runtime-gap-plan.md) | Broad live vendor changes/regeneration remain unverified; MAIN-world capture is inactive scope |
| accessibility | Michael / source | Polite compact controls, keyboard and automated accessibility checks. [runs/2026-10-10-frozen-site-local.json](runs/2026-10-10-frozen-site-local.json), [runs/2026-10-10-frozen-device-engines.json](runs/2026-10-10-frozen-device-engines.json) | Human screen-reader, physical-phone and independent usability acceptance remain open |
| delivery | Michael / operations | CSP, no-transform and exact public artifact comparison. [scripts/verify-publication.cjs](scripts/verify-publication.cjs), [runs/2026-10-10-frozen-site-public.json](runs/2026-10-10-frozen-site-public.json) | Hosting/DNS providers remain dependencies and receive connection metadata; hashes do not defeat a compromised trusted build |
