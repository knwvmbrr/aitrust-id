# Tag development status — 18 November 2026

Checked by Codex PM against the current scope ledger, implementation state and live agent inventory. This corrects an operational impression, not tag accuracy.

**132 original requirements complete; 70 open. Zero full tag release gates completed.**

| Lane | Software delivered | Current staffing | Next complete outcome |
| --- | --- | --- | --- |
| PS | Working browser/native/local preview; 80% parent requirement | Codex integration; Michael coordinates independent humans | Frozen current-method independent labels and human acceptance |
| PII_REDACTED | Working authenticated local privacy preview; 80% parent | Codex integration, no dedicated running specialist | Measure missed entities and false masking independently on supported cohorts |
| MT | Published bounded evidence workflow; 20% parent | Candidate delivered, no running specialist | Context and quotation handling plus accepted independent decision rule |
| NF and FI | Caller-selected claim/reference comparison; 20% each | Candidate delivered, no running specialist | Full evidence mapping and independent validation |
| FA and PA | Active signed image declarations and trust/revocation distinctions; 20% each | Candidate delivered, no running specialist | Bound complete claims to trusted provenance and validate each tag |
| HP, IV, UNK, PII_OUTBOUND, UC, SC and BT | Defined/proposed jobs; 20% each | Queued | Complete each named method and its own integration; proposals need adoption |

The three specialist agents visible in this chat (SEO, Share debugger and web/image lane) have completed their assigned tasks. They are not continuously running a detector lab. Codex PM is active on API, communication and legal integration. No agent-per-tag staffing is claimed.

The new API exposes only PS and optional PII_REDACTED. Making a tag callable does not complete its detector or validation. The MCP adapter was tested with the real official client; clean Ubuntu 24.04/Python 3.12 SDK installation and twelve API/MCP controls passed in CI. Robot, IoT and agent-interaction safety profiles are retained as explicit proposals in `tag-safety-use-cases.json`, not working intent detectors.

Next tag work should remain separate from owner-only App Store and social login steps. Track one bounded method increment, its actual error controls and its next independent acceptance gap; do not raise a parent percentage for unrelated infrastructure work. A new staffing assignment must be explicit and actually running before this board calls it active.

## Live assignment update

After the inventory check above, the PM reactivated two existing specialists: NF/FI now implements explicit per-claim evaluated/not-evaluated coverage; MT implements a separate opt-in quoted-authority candidate. The debugger completed a read-only API pass and reported two reproducible defects; both were corrected and the twelve focused checks passed again. These are actual bounded assignments, not fourteen continuously active agents. Deliveries and full-tag acceptance remain pending.

## Candidate delivery update

Both bounded assignments are now delivered in isolated commits and integrated into the PM working branch. MT source: `30a5043b28cea009f638aa927025f176e55d5e16`; NF/FI source: `7523925fb11bc03dc766f83bd03c7ad9e32c1b33`. MT has 22 actual CLI controls and 114 focused tests; NF/FI has three actual CLI controls and 228 focused tests. The parent integration additionally passed 73 focused controls across the two new components. These overlapping test sets are not summed into an accuracy score. No production tag assertion or full parent closure was granted. Specialists have finished these assignments; PM owns integration, Linux CI and publication.

## Linux runtime verification update

The three tag lab lanes passed on hosted Linux after the PS lane received its existing hash-locked service test dependencies. The startup debugger identified a protocol-directory traversal defect; a fresh Docker build observed mode 0444 in all three images before explicit correction, then passed 26 service and 15 replay controls. The dedicated Podman clean-clone installation and all ten failure controls passed, restoring the original staging services unchanged. These are synthetic engineering checks, not independent accuracy. All specialist assignments are now finished; PM owns current source validation and protected publication.
