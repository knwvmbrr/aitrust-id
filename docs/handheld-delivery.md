# Handheld delivery and faster validation

## Architecture

PS remains one bounded detector. Its current Python methods are projected into
an inspectable, standard-library-only device bundle at build time. A pinned,
self-hosted Python/WebAssembly runtime runs that bundle in a dedicated worker.
The HTTP evaluator is unchanged; no second JavaScript detector or public text
submission endpoint is introduced. The build fails on an unrecognized detector
structure. Cross-runtime tests compare full signals, spans and source identity.

The phone entry point is the PS modal: paste an answer, check on this device,
read the short result, and optionally download metadata. Input is data, never
Python source. Private text stays in volatile memory. The device result is a
distinct preview record; it does not pretend the gateway redacted the text,
that PII was detected, or that independent accuracy was established.

Home-screen installation uses a web manifest. Offline saving explicitly caches
only a release's public assets and runtime. No answer, label or result is cached.
The checker has bounded input, a worker deadline, clear cancellation and stale
result suppression. Clear/unmount terminates the worker and removes page state.

Reviewers get a separate blind form usable on a phone. It loads a prepared JSON
packet from their device and exports labels explicitly. It never starts the
detector or displays predictions. CLI comparison validates the frozen hashes,
unchanged items, completeness and disagreements. Independence still needs people.

## Risks and acceptance

- The initial runtime download and mobile memory cost must be measured and shown;
  older browsers may be unsupported. Do not describe emulation as physical testing.
- WebAssembly requires a specific CSP permission. JavaScript dynamic evaluation,
  third-party script loading and remote inference remain forbidden.
- Generated code and cache updates can drift. Pin runtime assets, bind detector
  hashes, compare every active regression across runtimes, and fail on mismatch.
- A frozen holdout must not be used while tuning. Faster automation improves
  engineering turnaround; it does not manufacture independent labels or accuracy.

## Delivery routes

| Route | Job | Acceptance |
| --- | --- | --- |
| Phone/device checker | Copy from any app, paste, inspect PS locally | Browser-engine parity, no text-bearing request/storage, mobile UX and actual device checks |
| Home-screen/offline app | Reopen and check after saving public assets | Offline reload and checking; failed downloads reported honestly |
| Browser extension | Small tags beneath supported desktop AI answers | Adapter identity, races, compact layout and installed-pipeline checks |
| CLI/download | Repeat checks and inspect structured records | Existing gateway, redactor, evaluator, schema and source binding |
| Native iPhone Share extension | Receive selected content from another app | Future native target, entitlement, signing and device review |
| Native Android sharing | Receive text through the OS share interface | Future native target and explicit permission/lifecycle review |
| Documents/images/audio | New subject and tag methods | Preserved scope, independent modality contracts and their own gates |

The current handheld increment targets both iPhone and Android. It provides no
cross-app overlay and does not claim a native share receiver. Those are separate
interfaces to the same tag standard, with operating-system constraints.

## Executed engineering baseline

The public-asset cache is about 15 MB. Cached releases keep their own method and
worker hashes; installation does not force activation over an open page. To
update, save again online, close all AI Trust ID tabs and reopen. Remove offline
files deletes only this app's registrations/cache namespace. No raw text enters
URLs, HTTP bodies, localStorage, IndexedDB or CacheStorage from this workflow.
Downloaded metadata contains a subject correlation hash, not anonymization.

Current automation compares 86 full findings (including spans and source hash)
in Chromium Android and WebKit iPhone emulations. It exercises invalid method
bytes, unsupported workers, cancellation, deadlines, export, blind labeling,
320px reflow, enlarged text, focus and axe. It does not establish physical-device
compatibility or screen-reader usability. WebKit's offline-emulation navigation
fails in [Playwright issue 42775](https://github.com/microsoft/playwright/issues/42775);
its offline reload test instead makes the origin unavailable and verifies the
cached app still checks. Chromium uses the browser offline toggle.

Run `make verify-ps` with your verification Python for the fast source/regression
loop; `make verify-device` builds and checks the two browser engines. Install
Playwright's Chromium/WebKit engines first. These commands fail on engineering
regressions; neither overrides the separate independent release gate.

Pyodide's [worker interface](https://pyodide.org/en/stable/usage/webworker.html)
and [self-hosting instructions](https://pyodide.org/en/stable/usage/downloading-and-deploying.html)
are the runtime basis. Pinned runtime license texts and source links accompany
the deployed assets. No runtime packages or third-party scripts load on demand.
