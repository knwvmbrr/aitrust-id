# Personal pipeline startup diagnostics

Record the failed anonymizer startup before the disposable CI containers are
removed. The November 19 log reports unhealthy about 1.5 seconds after start,
while the configured health grace period is 20 seconds. It contains no process
exit state, OOM observation, health probe output or startup stderr. Earlier
service sources passed on Ubuntu 24.04, and this run used Ubuntu 26.04.
Those observations establish the diagnostic gap.

Read the existing private disposable credential before capturing anything.
Refuse collection when the token is unavailable. Use a filtered Docker inspect
request for the fixed container name, verify the project/service labels and
exact name, then capture bounded startup logs through its immutable ID.
Capture only state, health, resource configuration and numeric tool versions.
Scrub the token before serializing any captured output. Avoid full Docker
configuration, environment inventories or unrelated containers.

Use the existing worker supervisor with a ten-second timeout and 64 KiB output
limit per command. Merge stderr through a fixed Python exec wrapper. A malformed,
oversized or failed diagnostic is unavailable and cannot accept service health.
Only the CI failure path invokes this collector, before upload and cleanup.
The original failed job remains failed.

Fixture controls cover exact ownership, missing tokens, malformed records,
credential redaction, unavailable commands and the real supervisor’s timeout
and output limits. No local Docker, model execution, resource change, timing
change or deployment is needed to verify these capture controls. The next
hosted failure must supply the runtime facts before a service fix is chosen.
