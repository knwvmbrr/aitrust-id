# Actual HP uncertainty-preview integration controls

This is a new production-route verifier, separate from the source-stable
standalone fixture. It does not modify that fixture's historical proof or method.
Architecture: inspect the real HP modal using scoped semantic controls; obtain
three complete expected records from the unchanged canonical Python adapter;
verify explicit caller context, private details, intact refusal and cancellation;
then refuse each actual optional delivery path and exercise real numeric HP, PS
and MT checkers. No generic fixture buttons stand in for those neighbouring checks.

`verifyHPUncertaintySite(browser, base)` is exported from
`scripts/hp-uncertainty-site-controls.cjs`. `base` must be the root origin without
a trailing slash. The caller owns the browser; the helper owns/closes its contexts.
Its errors carry only a fixed stage name; callers should hash the error message
rather than publishing raw page content. Canonical control construction requires
the source checkout and the existing verification Python environment.

The standalone runner uses the reviewed random-loopback fixture with actual
`_headers`; it does not relax CSP or inject inline axe. Existing full-site
accessibility checks remain responsible for their separate axe/probe gates.
The narrow runner checks keyboard/error focus, 44px actions, 320px/200% reflow
and both themes. This is not physical-phone or human accessibility acceptance.

After PM mounts the HP-only slot, copies its guide and runs the normal build:

```sh
AITRUST_VERIFY_PYTHON=/path/to/existing/verification/python \
  node scripts/verify-hp-uncertainty-site.cjs
```

For a verifier checkout separate from the built source tree, set
`AITRUST_HP_UNCERTAINTY_SOURCE_ROOT` and `AITRUST_HP_UNCERTAINTY_BUILD` explicitly.
`AITRUST_HP_UNCERTAINTY_SITE_REPORT` selects the ignored evidence output path.
The runner binds its actual helper files, source inputs, guide, payload, notices,
all built JS/CSS assets and runtime bytes before/after sequential Chromium/WebKit.
Public-origin review can call the same exported helper without rebuilding.

At source handoff, syntax and side-effect-free import checks pass. Actual
integrated execution is pending PM's built fixture; no success is pre-recorded.
T-HP/F-018, independent accuracy, full release and public publication remain open.
