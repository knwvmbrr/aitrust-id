# First-push change-record baseline

The ready control PR's change-record job passed. Its separate push job failed:
`before` was all zeros, and the workflow converted that into the empty tree,
misclassifying the established repository and historical records as new work.
The intentional `no-egress` failure is separate and must remain a failure.

For a first push of a feature branch, compare the complete branch against its
merge base with the fetched default branch. Do not use only HEAD's parent: an
undocumented earlier commit in a multi-commit branch would escape that check.
Use GitHub's actual default-branch/event reference metadata. Missing/unrelated
history or invalid references must refuse verification; do not fetch arbitrary
remote references or guess an ancestor. A genuinely new default branch compares
against the empty tree. Ordinary pushes and PRs keep their supplied actual base.

Exercise real disposable Git histories for documented/undocumented branch work,
a missed earlier commit, explicit PR/push bases, missing/invalid default refs,
unrelated history and the initial default branch. Centralize resolution in the
same change-record core used by CLI/CI. Include the prebuild gate's actual source
dependencies in website revalidation. Do not weaken record coverage, immutable
history, protected-main rules or independent tag-release gates.
