# Explore wording on a phone or computer

The MT phrase explorer runs two separately selected English observations on the
user's device: **Instructions + time words** and **Authority wording**. These are
method previews, not an MT tag, a judgment of a writer or independently measured
accuracy. No selection is made by default and no analysis begins until Run.

The short result explains what matched and what remains unknown. Quoted authority
phrases remain separate from outside phrases; quoted URLs cannot supply an
outside source marker. The urgency method retains its existing sentence-unit
and density rules and does not interpret quotations. A refusal is Unavailable,
not zero findings. Context, endorsement, truth and intent remain unclassified.

The form accepts at most 8,000 Unicode characters and 32,000 UTF-8 bytes. It never
executes pasted code. No account, upload, input storage, telemetry or server
analysis endpoint is added. Input and result stay in page memory until edited,
cleared or the component unmounts. Optional **Method and exact positions** shows
private hashes and normalized Unicode-codepoint positions without copying input.
There is no automatic download or sharing action.

Each run creates its own MT worker/runtime instance and terminates it at success,
failure or cancellation. The loading deadline is 45 seconds and evaluation
deadline is six seconds. Editing, choosing another method, Clear and unmount
cancel the old run. A late message cannot attach a result to changed text. The
new code imports no PS worker/client or method state. The existing pinned static
runtime assets are shared infrastructure, so their delivery is still a common
prerequisite; no whole-platform outage immunity is claimed.

## PM integration contract

This branch supplies a working component and private test fixture. It does not
change shared catalogue availability, production mounting or release status.

1. After the existing pinned runtime preparation, run
   `python3 scripts/build-mt-device.py` before the Vite build. This produces the
   deterministic MT manifest, exact-source bundle and original notice bundle.
   It does not install dependencies or copy/change the shared runtime.
2. Import `{MTExplorerSlot}` from `./MTExplorerSlot.jsx` into the existing modal
   renderer and render it for MT inside the MT modal body. Keep the tag's planned
   status and release gate unchanged. Do not render it as an asserted tag result.
3. Use the **slot**, not a direct `MTExplorer` import. The slot lazily imports its
   child with a 15-second import bound and a local React error boundary. A child
   chunk/import/render failure displays only the fixed MT fallback. Its local
   failure must not replace the app root, PS or other tag panels.
4. Keep the existing brand stylesheet and Tailwind source discovery. The actual
   production build must demonstrate that MT component utilities are included;
   the unpublished test fixture explicitly includes both MT sources because its
   build root is an ignored output directory.
5. Preserve the linked original project LICENSE/NOTICE, Unicode attribution and
   existing third-party runtime notices. Evidence and byte integrity are not
   dependency license clearance.

The MT source files run unmodified in an ephemeral in-memory Python filesystem.
The bundle and each embedded file are SHA-256 checked before use. The adapter
preserves the entire canonical Python method record, normalized subject identity,
source identities and exact method versions. The UI validates selected method,
result state, identities, counts and no-tag/no-intent flags before rendering.

## Reproduce engineering checks

With the repository's existing Python and installed website verification tools:

```sh
python3 scripts/build-mt-device.py
python3 -m pytest -q tests/test_mt_device.py
node --test tests/mt-device-client.mjs
node scripts/build-mt-device-fixture.mjs
node scripts/verify-mt-device.cjs
```

The fixture builds only under `output/`; it creates no public page or production
endpoint. Its verifier owns a random-port loopback server and launches Chromium
then WebKit sequentially, cleaning up its own server/workers/browser contexts.
Native-Python authored controls are compared to full browser records, not just
headings. Rendering checks use 390px and 320px/enlarged text. Safari-style full
control navigation uses Option+Tab, respecting native browser behavior.

This is desktop-hosted browser evidence. It does not substitute for the owner's
physical iPhone 14 Plus, human VoiceOver or independent annotation/accuracy
acceptance. No MT production assertion or full requirement closure is implied.
