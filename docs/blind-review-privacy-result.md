# Private blind-review workflow — executed 2026-10-11

Codex hardened the existing offline packet and phone review form without adding a tag, endpoint, collector or prediction. The tool uses descriptor-pinned private directories, bounded no-follow regular-file reads, exclusive private writes, readback verification and cleanup restricted to newly created owned inodes. It rejects public permissions, links, duplicate fields, malformed scalar text, forged validation flags, changed frozen fields, invalid CSV shapes and excessive sizes or reasons. The phone import uses strict UTF-8 and the same declared form limits.

62 focused Python controls and 34 Node parser controls pass on macOS. The isolated Linux run passes 56 security controls and 18 actual CLI controls; macOS also passes 18 CLI controls. Owned synthetic source/packet sandboxes were removed. No production service or participant data was touched.

In actual Chromium and WebKit phone viewports, four theme/engine flows froze real synthetic packets, downloaded eight completed forms and passed four private CLI comparisons. Original text and frozen hashes stayed exact. Disagreements/ambiguity remained visible, malformed imports were refused and no review marker appeared in requests, console or browser storage. The complete device regression also passes with seven invalid import cases per engine. These are browser engines on development hardware, not physical phones or humans.

N-015 advances from 60% to 80% for demonstrated selected integration. F-108 remains 60%; real independently sampled and labeled holdout material is not supplied by this tool. The complete ledger remains 114 complete and 88 open of 202. The target of 50 is not achieved, and no requirement was dropped or renamed to reduce it.

All five source-bound capability checks pass. The device receipt is bound to 11 files recoverable from the implementation commit, and the current route inventory covers 513 files. The full Python suite passes 1,923 tests with one upstream TestClient warning in 50.29 seconds. Protected merge and publication remain pending; these checks grant no independent accuracy or release acceptance.

Command syntax errors now use a fixed private message instead of echoing an argument or path. Actual updated Mac/Linux CLI checks and the browser/CLI round trip were rerun against that corrected source. Earlier source-specific diagnostics remain historical evidence.

Protected PR #38 passed all 22 required exact-head checks and merged with both implementation commits retained. The deployed preview, apex and www each match all 244 build files (732 matches), with the declared index security headers present. The original 12 unrelated untracked files remain byte-identical. This is publication evidence for the selected workflow, with no new accuracy or human acceptance claim.
