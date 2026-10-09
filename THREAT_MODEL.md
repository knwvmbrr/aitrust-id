# Threat Model

This table distinguishes implemented boundaries from future controls. It is not
an independent security assessment. The default processing service is local;
the public website is a static catalogue, not a public evaluator or research API.

| Threat | Current control and evidence | Residual / release work |
|---|---|---|
| Response exfiltration | Redaction precedes evaluation; anonymizer/evaluator use an internal Docker network. Bounded IPv4 TCP probes fail | Gateway necessarily receives original text. Redaction misses and compromised hosts remain risks; no universal no-egress claim |
| Backend exposure | Gateway binds 127.0.0.1, requires bearer token and rejects browser-page origins; body/concurrency limits tested | Local malware or a stolen token can call it; never publish this gateway to the Internet |
| Credential forwarding | Manual CLI disables proxies and redirects, bounds responses, validates schema and spans | Host compromise can still read local credentials; exclusive owner-only configuration is not a hardware vault |
| Hostile page / badge spoofing | Isolated extension content scripts, safe text rendering, correct response binding and closed shadow root tested | Closed shadow roots are not a security boundary; the page can imitate or remove UI. Assertions are unsigned; signatures cannot establish claim truth |
| Supply chain / tampered model | Runtime dependency/model downloads are hash-locked; evaluator source hash is recorded | No completed SBOM/signing release process or independent OS/application review. A hash establishes identity only |
| Crafted text evades a rule | Evaluator treats input as data; it neither fetches nor executes commands | Regex and use/mention errors are possible. Independent accuracy and adversarial review remain open |
| Excess collection | Default pipeline has no persistence/upload. Public issue forms request synthetic examples and warn about disclosure | Subject hashes/offsets are metadata. Optional registry is an unconnected prototype, with no implemented 30-day retention; not enabled by default |
| Vendor DOM change / stale result | Synthetic identity/revision/race tests and one live Homebrew response pass | Broader live completion, regeneration and navigation compatibility remain unverified; MAIN-world tap is retained inactive scope |
| Screen-reader disruption | Compact controls after output, polite status, keyboard/zoom/forced-color and axe tests pass | Human screen-reader and independent install/removal review remain required |
| Provider modifies public assets | Strict script CSP and no-transform preserve the reviewed build; custom-domain hashes and outbound traffic checked | Hosting provider receives IP/connection metadata and remains a delivery dependency |
