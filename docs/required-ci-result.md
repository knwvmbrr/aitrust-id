# Required CI — actual acceptance

F-054 is complete. Main requires eleven engineering checks from the actual GitHub
Actions app, with up-to-date branches and administrator enforcement. Force pushes
and deletion are disabled. A ready control PR intentionally failed the required
Python check, was blocked, and was closed without merging. Its other ten required
checks passed. The failing test never entered main.

The normal repair then passed all eleven required contexts on both its first
push and pull request, and merged through normal protection without an admin
bypass. Real Git/CLI tests cover the whole first-push range, including an earlier
undocumented commit that a parent-only comparison would miss. Missing or
unrelated default history fails closed. Ordinary PR/push bases remain unchanged.

[Negative control](../runs/2026-10-10-required-ci-failure-blocking.json),
[positive hosted acceptance and merge](../runs/2026-10-10-required-ci-positive-acceptance.json),
[991 Python checks and current route bindings](../runs/2026-10-10-required-ci-complete-python.json).
The separate release gate still fails for missing independent tag accuracy and
human acceptance; it was neither removed nor marked green. Zero required human
approvals reflects one operating owner, not independent review.

This closes one full requirement: **104 complete, 98 open, all 202 retained**.
F-152 remains open until CODEOWNERS and Dependabot are accepted and actually
operate. Its offline controls do not complete that combined requirement.
Research collection remains disabled; physical-phone and human accessibility
acceptance remain outstanding. A later workflow/check-name change needs fresh
verification and protection readback.
