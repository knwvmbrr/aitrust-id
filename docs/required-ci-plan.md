# Required engineering checks — implementation plan

F-054 still needs operating failure blocking, not merely a configured workflow.
F-152 separately requires branch protection, CODEOWNERS and Dependabot; do not
mark that entire record complete when only protection is operating.

Use the actual successful GitHub Actions check names and App identity from the
current commit. Require all eleven engineering contexts on main, with the branch
up to date, administrator enforcement, no force pushes and no branch deletion.
Require a pull request, with zero approving-review prerequisites while there is
only one operating human owner. This is source control, not independent scientific
review. Do not invent a second reviewer or operating foundation.

The separate `gates` context must continue to refuse a detector release without
independent accuracy and human accessibility evidence. Requiring it for every
source/document contribution would prevent improving this development preview;
it is not an engineering pass and is not removed, made advisory, or marked green.
The release process remains subject to those prerequisites.

Only enable a context after its actual hosted engineering run succeeds. Then
create a clearly labeled temporary test branch and ready pull request containing
one intentional failing Python control, with a proper changelog record. Confirm
the required check fails and the ready PR is blocked by protection, retain the
source/status evidence, and close it without merging. Never attempt a merge of
known failing source as a test. Validate API readback against the declared checks,
App identity and administrator/force/deletion/PR settings. A rule file alone or a
draft PR's inherent blocking state is not enforcement evidence.

Future verified changes use pull requests with those required contexts. Do not
weaken protection for faster deployment or proof bookkeeping. Controls and policy
updates remain reversible through the authenticated owner settings; check names
changing requires a reviewed update rather than an indefinitely pending gate.
No production credentials, raw user examples or model keys enter this evidence.

References: [GitHub protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches),
[branch protection API](https://docs.github.com/en/rest/branches/branch-protection).
