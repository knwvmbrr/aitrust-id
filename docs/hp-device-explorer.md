# Explore literal details on your phone or computer

Paste English text and choose **Find details**. The explorer counts supported
number and date-shaped spans and separates those with a source marker in the
same literal sentence unit from those without one. A source marker is a URL or
numbered reference. It is not a checked source, and nearby placement does not
establish that it supports a claim. A date-shaped span is not a valid calendar
date. This is a method preview: no HP tag, truth judgment, probability or
independently validated accuracy is issued.

The canonical method remains `literal-quantitative-observations/1.0.1`, unchanged.
ASCII signs, grouped/decimal numbers, percentages and YYYY-MM-DD shapes retain
their existing token boundaries. Non-ASCII or overlong candidate tokens may be
skipped. Quotes, code, negation, endorsement and semantic relationships are not
interpreted. The short result states these limits. Unavailable means that a valid
complete result could not be obtained; it never becomes zero findings.

## Use and privacy

On the website, this component needs no account, Docker, Python or extension.
It starts no analysis until **Find details**. The first run needs network access
to download public source and the pinned Python runtime; this increment does not
provide or promise an installed offline cache. Once loaded, the observation runs
on your device. No input upload, input storage, telemetry, model download or
server-analysis endpoint is added. Text and results remain in page memory until
edited, cleared or unmounted. Browser/OS input features are outside this code's
control.

**Method and exact positions** is optional and private. It shows the entire
canonical record and adapter identity, not pasted text. Hashes and positions can
link information, so no automatic export or sharing action is provided. The
result must pass closed schema, exact source, raw UTF-8 input and frozen-NFC
subject validation before either the brief result or details can render.

Each run owns a fresh HP worker and Python runtime, terminated on completion,
failure or cancellation. Editing, Clear or unmount cancels the old run; late
messages cannot attach results to new text. HP imports no PS or MT client, worker,
result adapter or method runtime. The exact language helper source supplies the
canonical method's existing sentence-unit/source-marker helpers; it does not
invoke MT analysis. Public static runtime delivery remains shared infrastructure,
so this is not a promise against every platform-wide outage.

## Limits

- At most 8,000 raw and normalized Unicode characters and 32,000 UTF-8 bytes.
- The canonical 48-character token and 256-detail limits remain unchanged.
- The canonical private-record cap is 131,072 serialized bytes; the full adapter
  envelope is capped at 262,144 bytes. A larger record is refused in full, never
  clipped into a misleading smaller result.
- Runtime loading has a 45-second deadline. Observation plus record validation
  has a six-second deadline.
- The new envelope is `hp-literal-detail-explorer/1.0.0`; the underlying method
  meaning and version are unchanged.

## Integration contract

This branch provides the completed standalone component and unpublished fixture.
Shared production mounting and final production validation belong to the PM.

1. Keep existing pinned static runtime preparation. Then run
   `python3 scripts/build-hp-device.py` before Vite. It generates only the HP
   exact-source bundle, manifest and notices; it does not install dependencies.
2. In the shared modal renderer, import `{HPExplorerSlot}` from
   `./HPExplorerSlot.jsx` and mount it in the HP modal. Use the slot rather than a
   direct component import: it contains lazy-import, missing-chunk and render
   failures locally, with a 15-second import deadline and fixed fallback.
3. Keep the existing HP planned/release status. This explorer is a usable literal
   method preview; it is not an HP assertion or full T-HP/F-015 closure.
4. Keep the existing brand stylesheet and demonstrate in the final production
   build that the component's Tailwind utilities are discovered. The ignored
   fixture root explicitly includes both HP component files.
5. Preserve exact project LICENSE and NOTICE, Unicode attribution and the
   existing runtime notices. Source/byte verification is not license clearance.
6. Do not change another tag's worker or error boundary. The standalone fixture
   proves its generic adjacent-tool probe survives HP faults; it does not itself
   retest production PS/MT or their shared integration.

The builder reads every selected source/notice through held no-follow,
nonblocking regular-file descriptors, with a 200,000-byte cap before reading. It
binds parent/root identities and rechecks all inputs and staged files before any
public replacement. Source refusal preserves prior outputs. A failure during or
after publication reports fixed `output_may_exist: true` uncertainty, rather than
promising rollback. No captured source is executed by the builder.

## Reproduce from a clean clone

The repository's public clone is:

```sh
git clone https://github.com/knwvmbrr/aitrust-id.git
cd aitrust-id
```

For the canonical command-line observation, only Python 3.10+ and the repository
are required. Supply a private UTF-8 input file; this command reads it and prints
the canonical brief result. The new browser adapter is importable as
`tools.hp_device.inspect_hp_device` for an existing Python caller.

```sh
python3 scripts/quantitative-observations.py --help
printf '%s\n' 'The total is 12 [1].' | python3 scripts/quantitative-observations.py --language en
```

For developer/browser checks, use Node 22.12+ and Python 3.10+. Install the pinned
site dependencies separately from the root verification dependencies. A clean
machine also needs the Playwright engines. These are development steps, not
requirements for people using the mounted explorer.

```sh
npm ci --prefix site
npm ci
npx playwright install chromium webkit
python3 -m venv .venv
.venv/bin/python -m pip install -r eval/requirements.lock
python3 scripts/build-hp-device.py
.venv/bin/python -m pytest -q tests/test_hp_device.py tests/test_quantitative_observations.py
node --test tests/hp-device-client.mjs
node scripts/build-hp-device-fixture.mjs
node scripts/verify-hp-device.cjs
```

The fixture lives only under ignored `output/`; it adds no published page or
production route. Its verifier owns a random-port loopback server and runs
Chromium then WebKit sequentially, terminating its own workers and server. It
compares whole native-Python and browser records, including refusal cases and
Unicode witnesses. Results/snapshots are engineering evidence, not independent
accuracy, physical iPhone 14 Plus, human VoiceOver or real-person acceptance.
