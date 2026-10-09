# Clear PS results and personal-tag availability

Architecture plan · 2026-10-09 · Codex

Show exactly which tag ran: PS only in the on-device checker. PII is a separate local-service route; the other twelve personal catalogue entries are planned or proposed. Preserve code-only tiles and each tag’s independent scope. Give each personal panel a visible availability sentence.

Present the result as what was checked, what was found and what to do next. For a finding, show plain explanations tied to the actual signal IDs and matched input spans. A completed negative check means no supported pattern, not safe or verified. Invalid states or evidence fail closed to unavailable.

Risks: do not infer scam, intent, authorship, truth or privacy; input excerpts may contain sensitive details and must stay on this page, excluded from default exports and logs. Escape text via React; do not execute or fetch any command. Validate Unicode positions using NFC code points, not UTF-16 offsets. Preserve cancellation and detail consent.

Acceptance: real worker results show mapped reasons and exact matched excerpts; negative, unsupported and failed results never produce safety clearance; unknown signals or invalid positions do not become findings; no injected input executes; all fourteen personal routes have explicit availability; phone emulation, keyboard, reflow, export and no-upload checks pass. Independent detector accuracy and human usability remain separate gates.

## Delivered and verified

Published from 28b66b8. The PS result names the bounded check, gives a reason for each supported signal, displays its matched text and explains the next step. The result is brought into view after checking. A no-finding result explicitly excludes truth, scam, authorship and general safety conclusions. Each personal panel states whether it is available here, requires the local service or is planned/proposed.

Six real worker result cases cover all five signal types plus no finding; seven invalid evidence/state variations are rejected. HTML input renders as text, NFC code-point excerpts are correct, default exports exclude matched text, and public no-upload checks pass. Both emulated phone engines execute 86 method-parity cases; no physical-device, human usability acceptance or independent accuracy completion is implied. Deployment and hash evidence: runs/2026-10-09-ps-results-deployment.json.
