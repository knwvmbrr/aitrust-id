# Independent MT evidence workflow — implementation plan

2026-11-17 · Codex PM · T-MT, F-019a, F-019b, F-019c.

The next deliverable is one runnable private research workflow for urgency,
authority wording and explicitly selected two-choice context. It does not activate
MT in the production allowlist or convert literal matches into accusations.

Architecture: a bounded UTF-8 input is frozen with the existing Unicode 15 NFC
implementation. Each explicitly selected component runs in a separate, isolated
Python child with the existing bounded pipe supervisor: no shell, stderr capture,
content files, third-party dependency or network call. Choice alone reads a
caller-selected private corpus/context packet; that optional dependency is loaded
inside its worker. A malformed choice packet, crash, output flood or timeout must
leave other selected observations usable. A complete/partial/unavailable envelope
retains every requested component, source identity and actual method version.

The default terminal view is brief and contains no submitted text, hash, spans or
private paths. Detailed evidence requires an explicit new owner-private output
folder outside the checkout; existing files are never overwritten. There is no
collection, account or production endpoint. The bounded worker is process fault
containment, not an operating-system network or malicious-host sandbox.

Risks: urgency can be legitimate; authority can be sourced elsewhere; a chosen
third passage may be irrelevant; related lexical checks share causes. Therefore
there is no combined confidence, vote, intent finding or MT assertion. Unsupported
language/input is refused. A missing choice packet is unavailable for choice,
never an automatic selection. No selection request triggers the other checks.

Verification: actual complete and partial CLI paths, exact subject/context
binding, no supported pattern, malformed/unsupported input, private no-overwrite
export, worker crash/timeout/flood/malformed output, recovery and a concurrent PS
check. Tests must inspect effects and retained outcomes, not merely mirror code.
Remaining MT acceptance is context/use-mention interpretation, accepted annotation
and sampling/error policy, independent human agreement and route accessibility.
