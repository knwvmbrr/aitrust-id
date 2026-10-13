# Follow-up: bounded build stage diagnosis

Architecture before refactor, 2026-10-12. The aggregate website command lost
its failing browser phase, so a source-stable repeat could not diagnose that
original failure. Add structured phase bookkeeping around the existing child
commands, without changing any command, criterion, fixture or environment.
Keep raw child output out of the structured record. Record a closed phase name,
start/end timestamps, elapsed time, integer exit code or bounded signal, and
fixed startup-failure category. Write with the existing guarded report writer
after the owned server has closed. Failed execution is a failed record, never
a passing partial result. The public schema contains no paths, URLs, input text,
credentials, exception strings or child output.

Risks: bookkeeping that masks the original failure, hangs after process failure,
creates a new upload path, leaks stderr, or changes passing behavior. Tests must
exercise success, ordinary nonzero exit, termination signal, startup refusal,
unsafe stage name, and incomplete stage sequence with real disposable children.
No browser launch, production change, new endpoint or fake accessibility claim
is needed by those unit tests. Bind the runner and tests in source fingerprints;
run the full original website command after integration before promotion.

# Controller interruption follow-up, architecture before correction

The guarded scratch writer currently runs only after completion. A hard parent
termination can therefore leave a prior passing scratch record. Before the first
child, overwrite the owned scratch destination with a fresh incomplete record.
Writer refusal must prevent any child from starting. Keep the original commands,
criteria, environments and owned server cleanup unchanged. Final success still
requires all eight real phases. This does not guarantee every operating-system
termination executes a finalizer or that child output is private when shown in a
terminal; the structured record excludes input, URLs, paths and arguments.

Execute the copied actual controller in disposable fixtures: a real failing
first child records its failure; a symlink destination stops execution before the
first child; terminate an owned isolated process group during a hanging first
child and verify the preceding passing scratch was replaced by incomplete false.
Use only invented fixtures and clean only the owned temporary tree/process group.
Then repeat all source-bound checks and retain prior receipts as historical.
