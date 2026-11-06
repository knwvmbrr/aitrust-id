# Bound disposable browser CI installation

Architecture before code, November 6: the PR 83 site job spent over 45 minutes
fetching Ubuntu packages from azure.archive.ubuntu.com, including a retried GTK
package; browser tests had not started. Its matching exact-source site job passed
in 5m34s. The overlong run was stopped at the declared limit so its logs could be
examined. This is an observed package-download problem, not a detector failure.

On only the two disposable browser CI jobs, pin the observed Ubuntu 24.04 host
and prepare an explicit HTTPS canonical Ubuntu archive source. Accept only known
Ubuntu archive URIs or GitHub's exact mirror+file:/etc/apt/apt-mirrors.txt profile;
retain the original suites, components and Ubuntu archive signing key. Reject
unknown policy, trust overrides, unexpected OS/context and unsafe staging files.
Write a fresh owner-private staging file; the workflow installs it with the same
existing sudo authority used by the dependency installer. This is accidental-host
protection, not a sandbox against forged environment markers or compromised root.
No production or developer host is reconfigured. No signing bypass, new package,
browser/version upgrade, local Docker, test exclusion or release waiver is added.

Keep every existing browser test. Bound the install step to 15 minutes and the
browser jobs to 30 minutes; a timeout fails instead of claiming a pass. Exercise
known direct/mirror source formats, repeated transformation, trust/URI/suite
refusals and ordinary-host refusal before pushing. Actual clean GitHub-hosted
execution must prove compatibility and retained browser behavior before merge.
Do not claim a speed improvement from a local parser test or a changed URL.
Revalidate affected source receipts and the route review after this workflow
change. Conformance human/accuracy gates remain separate and unchanged.

Primary references read November 6:
- https://raw.githubusercontent.com/actions/runner-images/main/images/ubuntu/scripts/build/configure-apt-sources.sh
- https://ubuntu.com/server/docs/how-to/software/package-management/
- https://playwright.dev/docs/ci
- https://playwright.dev/docs/browsers

The current runner-images source is upstream evidence, not proof of a particular
image's deployed format; both exact observed/direct and documented mirror-file
forms are handled, and unknown configuration stops the job.
