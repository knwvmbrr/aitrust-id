# Device and accessibility increment — verified result

Recorded 2026-10-09T20:08:55.069091+00:00 by Codex. Source 81fc621cfb0dc76ae7862a3e0f4c5c1f87bd6979 is committed,
pushed and deployed at https://aitrustid.com and
https://9805ae71.aitrust-id.pages.dev.

## Implemented and exercised

- Device builder normalizes only AST tuple targets, checks semantic identity,
  writes atomically, preserves unchanged file timestamps and blocks publication
  on failed stale-bundle cleanup. Tests run in fresh temporary output directories.
- Four actual installed Python builders (3.10.15, 3.11.10, 3.12.14, 3.13.0)
  produce the same bundle/manifest. The initial comparison used a generated
  manifest; the subsequent clean-checkout correction uses the committed
  docs/device-build-reference.json. PS method and
  bundle hashes remain unchanged. No future-version guarantee is made.
- PS empty/oversized input errors are associated with the answer field; focus
  returns to it, editing clears the error, and busy state is announced.
- Actual site accessibility probes cover 62 screens across light/dark at 320px:
  772 focus controls, 780 target measurements and 156 keyboard disclosures.
  Six injected probe defects are caught. This is not a completed VPAT/ACR.
- The Legal workflow links the bounded downloadable accessibility test record.
- 301 reviewed Python tests pass. Android Chromium and iPhone WebKit each match
  all 86 development cases locally and publicly. Local offline checks pass on
  both engines; public offline reload is exercised on Chromium only. Actual
  phones and human screen-reader usability remain unverified.
- 134 published artifacts match on the domain, www and deployment origin:
  402 SHA checks. All declared response headers match; no injected analytics
  was observed. Initial urllib fetches returned HTTP 403 and provided no proof;
  the completed Node fetch check supplies the artifact evidence.

## Scope and remaining acceptance

All 202 scope IDs, 39 work packages and 117 subtasks are preserved. Evidence,
UTC timestamps and contributor credit were added to the affected records.
No existing acceptance percentage was inflated and no additional tag was
asserted live. Claude's initial builder/fixture drafts were reviewed and saved;
Codex's repaired implementation and actual-site probes are this increment.
Unrelated adjudication drafts remain in the owner checkout, outside this release.

PS remains a development preview pending frozen independent ground truth,
reviewer adjudication, calibration and accepted release gates. Full accessibility
acceptance still needs real people/devices. GitHub Actions run 37984760446 starts
zero steps because the account is locked for billing; configured CI is not
claimed to have run. These findings retain owners and next fixes in scope.

See runs/2026-10-09-device-a11y-deployment.json and the individual public reports.
The live changelog and accessibility download reflect the deployed source
snapshot. This subsequent publication record is in Git and state; it is not
retroactively included in the earlier deployment artifact.
