# Offline observation increment

Implement F-026, F-027, F-028, F-029b, F-029c and F-082 as an explicitly started,
standalone editor, separate from the extension and the tag evaluator. Its output
is an observation record, never PA, FA, IV, a liveness score or an identity claim.
The existing proposed tag mappings remain proposed.

Architecture: a bounded event reducer, a native-control editor and a reproducible
self-contained HTML builder. No backend endpoint, account, dependency, network
request, persistence or global keyboard listener. The editor holds text only in
its own field; the reducer receives lengths and positions, not content. Manual
export contains scalar summaries and the method identity, not text or event
streams. Pause ends observation and clears pending keys; reset deletes the field
and all measurements. Sessions are limited to 30 minutes, 10,000 events and
20,000 UTF-16 code units. Stop rather than silently sample after a limit.

Risks: focus is not attention; edits are not authorship; browser events are
forgeable; timing summaries can still link sessions. Default input mode suppresses
timing. Explicit physical-keyboard mode enables only coarse dwell/flight
coefficients of variation. IME, replacement, untrusted or unmatched keyboard input
irreversibly suppresses timing for that session and erases accumulated timings.
Self-declared assistive input is supported; invisible assistive technology cannot
be reliably detected. No classifier or human-negative inference is permitted.

Acceptance: numeric reference cases and malformed/bounds controls for each
measurement; actual Chromium and WebKit editor typing, rewriting, focus,
composition suppression, pause/reset/export; no network or storage writes;
keyboard controls, axe checks and a deterministic single-file build. Emulated
engines are engineering evidence, not human accessibility review or physical
phone acceptance. Keep those release jobs open.

Additional isolated work: F-017 gets a bounded literal n-gram repetition checker
with exact spans and method/configuration identity. Repetition is an observation,
not evidence that a statement is false. F-053 gets versioned HP/MT/FI development
fixtures with explicit synthetic authorship and no independent-label claim.
Neither component enters the production tag allowlist.
