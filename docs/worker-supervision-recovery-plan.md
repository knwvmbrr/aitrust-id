# Recover optional workers without signaling an unrelated process

Before code: preserve the existing `run_worker` arguments, bounded input/output,
return values, timeout and no-shell/no-stderr behavior. This is a small ownership
fix, not a caller or detector refactor.

The review reproduced two failure windows. Selector construction currently occurs
after spawning but before the cleanup guard, so a selector startup failure can
leave the owned child. Separately, an exception after `wait()` reaps the child but
before the success flag can cause cleanup to signal a process-group identifier
that is no longer reserved by that child.

Allocate buffers and obtain the deadline before spawn, then move selector
construction into the child ownership guard. The wall budget includes startup;
an initial clock/allocation failure must not create a child. On failure, signal only
an unreaped child (`returncode is None`), then wait for that owned child. Never
poll/reap before signaling a failed group. Close the selector and both pipes in
nested cleanup guards so a close failure cannot skip later owned handles.

Risks: failed jobs must not leak descendants, output or file descriptors; cleanup
must not signal a released/reused process-group ID. Preserve normal successful
and nonzero outputs exactly. Fault controls must use owned child processes and
intercept any attempted signal after reaping; never test by signaling strangers.

Acceptance: real pipe/timeout/flood/descendant controls plus owned selector-start,
post-reap and selector-close failures; separate review; update actual PS source
policy binding and current source-bound receipts where this shared helper is an
input. No tag accuracy, new original closure or platform guarantee is inferred.
