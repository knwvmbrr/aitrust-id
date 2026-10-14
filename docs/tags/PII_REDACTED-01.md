
## Independent operation — owner direction, 2026-10-14

The explicit privacy mode may not require a PS verdict, evaluator availability or
PS admission slot. It has one reserved gateway slot; full-pipeline traffic cannot
borrow it. `aitrust.py doctor --privacy` checks only this selected route. The
redactor remains a required dependency of this procedural tag. Failed redaction
withholds this tag and never forwards raw input to another service.

Acceptance includes actual checks while the evaluator is stopped or saturated,
refusal when redaction fails, release of reserved capacity after cancellation and
failure, and recovery. The separate standalone PS command remains usable without
this redactor. Recognition accuracy and human acceptance remain separate open gates.
See [architecture and current tests](../tag-failure-isolation-plan.md).
