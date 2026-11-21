# MT input-retention repair

An actual native browser insertion reproduced the defect:8001 emoji were silently
clipped to8000 by the HTML UTF16 `maxLength` attribute, then accepted for analysis.
The complete shortened canonical record matched that8000-character subject; the
method was not malfunctioning. The editor had changed the submitted input first.
The immutable [before record](../runs/2026-11-21-mt-input-clipping-before.json)
distinguishes reproduction success from product acceptance.

The only product change removes the HTML length clip and says that full text
remains unchanged. Existing8000-codepoint/32000-byte validation, raw/frozen-NFC
identity, canonical methods, fresh-worker behavior, payloads and tag boundaries
are unchanged. Invalid input remains in the editor, receives associated error
text and focus, and starts no worker. This does not impose a hard browser-memory
limit on arbitrarily large pastes.

The normal own-checkout build passes, including the exact5-runtime/3-source-artifact
postbuild gate. A focused Node group covers all six selection/shape refusals.
Actual Chromium and WebKit each prove:

- All8001 emoji and16001 ASCII characters remain intact under urgency, authority
  and curly-quotation selection; refusal happens before any new worker.
- Three ordinary whole canonical records match, including raw/frozen-NFC identity,
  with private evidence closed initially. The exact8000-emoji boundary still works.
- Edit, Clear and modal unmount terminate pending work; reopen is empty.
- No supplied canary appears in requests, storage or console;320px/200% layout
  and44px actions remain operable.
- A real MT-payload404 gives no result; actual PS and numeric HP still work.

[Source-bound result](../runs/2026-11-21-mt-input-retention-result.json) ·
[Actual corrected browser proof](../runs/2026-11-21-mt-input-retention-after.json).
No full unchanged quotation cohort was repeated for this editor repair.

## Normal verification hook and parent handoff

`verifyMTInputSite(browser, base)` in `scripts/mt-input-site-controls.cjs` is reusable
on the actual built or public MT modal. The existing
`scripts/verify-mt-mobile-site.cjs` now invokes it after all prior quotation controls
in each existing engine, recording its result separately. This adds no new required
command and drops no old check or deadline. The hook is syntax checked; parent will
execute the complete normal hook during integration, refresh exact-source inventories
for the two new verifier files and protect/publish the change. The exported affected
controls themselves have actually run in both engines.

For a focused repeat from a normal built checkout:

```sh
AITRUST_VERIFY_PYTHON=/path/to/existing/verification/python \
  node scripts/verify-mt-input.cjs
```

`AITRUST_MT_INPUT_SOURCE_ROOT`, `AITRUST_MT_INPUT_BUILD` and
`AITRUST_MT_INPUT_REPORT` permit explicit separate source/build/evidence locations.
The historical `--expect-before` mode is for an intentionally preserved old build;
it cannot pass against the repaired editor. Diagnostics retain fixed stages and
error digests rather than page content. The reviewer uses synthetic inputs only.

This repairs existing MT input integrity. It creates no new tag or method and
closes no full T-MT/F-019/F-142 acceptance. Independent contextual labels, physical
phones, human accessibility and protected/public delivery remain separate gates.
