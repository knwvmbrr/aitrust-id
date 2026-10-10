# Synthetic upstream fixture

Only for the disposable staging project. It uses the existing /healthz, /redact
and /signals contracts. No public port, auth token, telemetry or production data.
A read-only `/fixture/mode.json` file selects bounded faults. `slow` deliberately
holds an upstream connection for 15 seconds; cancelling gateway HTTP does not
kill work already admitted by this artificial upstream. Gateway capacity and
connection cleanup are tested separately. Never use this fixture as a detector.
