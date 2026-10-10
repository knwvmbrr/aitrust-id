# State evidence chronology — review correction

PR 11 identified a real audit inconsistency: both state timestamps preceded the
fresh website receipt referenced by the same snapshot. Refresh both timestamps
after recording referenced evidence, and enforce this in the existing required
accountability check.

Walk only explicit repository-relative JSON run references in state. Require
existing bounded regular files with no traversal or symlinks. Parse timezone-aware
captured_at or recorded_at fields where present, reject future dates, and require
the matching state timestamps to be at least as recent as every referenced timed
receipt. Date-only historical records remain untimed; their absence of an exact
execution timestamp is counted, not invented. This does not authenticate receipt
contents or convert an engineering observation into independent validation.

Risk: a state snapshot can reference many historical records. Preserve them and
update the fixture from the actual reference set; do not ignore missing receipts
or relax the time check to make stale state pass. Test stale, mismatched, invalid,
naive and future timestamps, missing references, traversal and receipt links.
