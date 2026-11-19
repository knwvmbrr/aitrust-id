# Built-site header parity in verification

CI's catalogue server previously used Python's plain static server, which does
not implement Cloudflare `_headers`. The actual HP integration correctly
requires the response CSP, so it failed against that policy-free fixture even
though the local current-build controller served reviewed headers. The HP
assertion and accessibility probes remain unchanged.

Both callers now use `scripts/site-fixture-server.cjs`. It serves only the chosen
built directory and parses that build's `_headers` through the existing reviewed
`static-headers.cjs` subset. It applies global security headers and exact-path
overrides to real HTTP responses; no CSP bypass is introduced. This is a
loopback test fixture, not a production web-server or complete Cloudflare emulator.

```sh
node scripts/site-fixture-server.cjs --directory site/dist --port 5174
node --test tests/site-fixture-server.cjs
```

The CLI binds only 127.0.0.1, validates its exact arguments and prints a fixed
readiness line. Unknown/malformed targets refuse with 404; only GET/HEAD are
accepted, with other methods returning 405. HEAD sends the same reviewed headers
without a body. Raw dot traversal, NUL/backslash paths, root changes, symlinked
files/ancestors/root and nonregular files refuse. The policy file is bounded and
must be a regular non-symlink path. File descriptors are closed for HEAD and handed
to a destroying stream for GET. The root and opened file identities are checked;
the fixture assumes a frozen build controlled by the verifier and does not claim
to withstand every concurrent filesystem mutation by a privileged local actor.

`startSiteFixture({directory, port:0})` supplies an owned ephemeral loopback URL
and an idempotent cleanup method to the current-build controller. CI runs the
focused HTTP tests, starts the same CLI, verifies startup/readiness, then runs
its original catalogue, theme, performance, accessibility and workflow checks.
Local phase order remains unchanged; the existing first control phase includes
the fixture's focused tests before building. No full suite or tag accuracy gate
is skipped or weakened.

The plain-server search found one static `python3 -m http.server` occurrence in
CI, now replaced. Firefox extension verification has separate synthetic proxy
and gateway `http.server` classes; those are not catalogue hosting and remain
unchanged. Production deployment and source-binding inventory updates stay with
the PM.
