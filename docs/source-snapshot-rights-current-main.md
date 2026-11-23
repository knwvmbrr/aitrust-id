# Check current protected source-copy bytes

The current finite V2 selection is protected source `6d752cd0ae127e7d1ebe93499ab6fd83f55dcafd`: 13,502 committed files and 142,114,658 raw bytes. Its source-copy table has 615 delta rows and 327 origin records, retaining the original protected baseline and every third-party grant category. The 34 new guides and factual records have individual named origins; 20 existing project files are updated. There are no missing old paths or changed third-party files in this selected transition. Future unknown files still refuse.

Use the checker from an independently trusted checkout containing this reviewed implementation:

```sh
python3 -I -S -B tools/source_release_policy_v2.py \
  --source-commit 6d752cd0ae127e7d1ebe93499ab6fd83f55dcafd

python3 -I -S -B tools/source_release_policy_v2.py \
  --source-commit 6d752cd0ae127e7d1ebe93499ab6fd83f55dcafd \
  --archive /your/private/source-6d752cd0.tar.gz
```

The second command composes two distinct checks. First, the fixed reviewed copy profile checks the independently selected commit and source obligations. Only then does captured, SHA-pinned archive-binding code compare the received archive with every trusted Git blob, mode and size. Archive labels cannot choose a commit, root, policy or verifier. Unknown rights refuse before archive interpretation. The binding runs in an isolated owned Python process; received source is never imported or extracted. Missing, malformed, coherently forged or changed archives return **Unavailable** with a fixed reason and no fabricated zero observations.

This is consumer-ready source-copy evidence, not an authenticity or release decision. Even a successful result keeps `signature_verified`, `source_archive_admitted`, `release_authorized`, `compiled_runtime_permission`, `legal_clearance`, `accuracy` and `complete_F057_X02` false. Obtain actual protected signature and independently selected roots, route authorization and managed-consumer evidence separately. Neither a valid Git hash nor project authorship metadata proves independent tag accuracy or grant applicability for a different artifact.

Existing V1 bytes and the original V2 helper/table are preserved unchanged; the latter are retained under digest-named `eval/dependencies/source-copy-v2-history/` files. Prior receipts continue to describe their exact earlier selected development tree. The current table truthfully records that this exact selected commit is protected; it does not turn that fact into professional approval.

One explicit marker transition is scoped to the reviewed replacement of `docs/legal/execution-packet.md` with a public notice. Its former Markdown “Copyright work” review paragraph was included by the old declaration heuristic. The fixed new blob has no such paragraph, and removes no third-party grant or copyright notice. No global marker rule is relaxed; all other current project changes retain their existing declarations. History and earlier licensed copies are not erased.

Limits remain decimal: 16,384 files, 32,000,000 bytes/file, 256,000,000 raw source bytes, 2,000,000 Git listing bytes, 12,000,000 policy bytes, 64,000,000 compressed archive bytes and 5,000,000 metadata bytes. Copy classification has its existing 30-second deadline; binding has at most 60 seconds in a composed 95-second envelope, including a bounded cleanup margin. No SDK, model, dependency install, account, network, paid service or signing is required. Keep at least 2 GiB disk reserve before building an archive.

This is one source-copy route increment. Full F-057 and X-02 retain all distribution scopes, applicable runtime/source/notice obligations and actual consumer requirements. No percentage or original requirement is closed here.

## Actual selected-source outcome

One actual archive was built and inspected for protected `6d752cd0`: 40,864,663 compressed bytes, SHA-256 `f3b69aed5339784e5d5700289c808832c8ed377316b8bcfa4c2ba95716524cfe`. The corrected composed consumer matched all 13,502 files and 142,114,658 raw bytes against that commit's Git tree. No archive member was extracted or executed. The private archive is not a public release or authenticated download.

The first composed check returned Unavailable before a binding child launched because it incorrectly used a neutral transport limited to 1,000,000 input bytes. That failure is retained. The corrected composition uses the already reviewed binding helper's streaming supervisor; shared helper bytes and limits are unchanged. The same archive passed after that source correction without rebuilding. Fourteen classification controls and eight initial composition controls passed before the transport finding; the nine affected corrected composition controls then passed, including a real 1,000,001-byte pipe and coherent forged-archive refusal. These are versioned execution observations, not independent accuracy or twenty-three newly replayed current controls.
