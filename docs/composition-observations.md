# Editing observations, without an authorship verdict

Run `python3 scripts/build-composition-tool.py`, then open
`output/composition/editor.html` in a browser. The generated file works offline
and can be copied to another device. The source is under `tools/composition/`.
No Docker, server, account, installation or browser extension is needed.

Choose your input method, select Start, and type your own **test** text in the box.
Select Pause to end observation. Expand the record to inspect it, or choose
Download this summary. Download your text creates a separate exact UTF-8 artifact
only when chosen. Reset and delete clears the field and measurements.
The page observes only its own editor. It does not follow you to other pages.

| Independent component job | Exact observation | Limit |
|---|---|---|
| F-026 / keystroke liveness | Coarse dwell and sequential flight coefficients of variation after at least three samples | No liveness, identity or human-authorship score. The historical name is not the output claim. |
| F-027 / revision churn | Deleted units plus replacement units, divided by final length; non-adjacent edit count | UTF-16 units, not linguistic characters; empty denominator is null. |
| F-028 / compose monotonicity | Shannon entropy over eight normalized caret bins, sampled at edits and selection events | Browser events and sampling frequency affect the result. No origin inference. |
| F-029b / attention shape | Visible focused duration, hidden duration, focus changes, visible edits and edit gaps of at least two seconds | A focused page does not establish attention or reading. |
| F-029c / paste burst | Explicit paste of at least 64 units without a trusted key-down in the preceding two seconds | Pasting can be entirely human. It does not establish AI use. |
| F-082 / assistive routing | Timing off by default; explicit assistive mode, IME/composition, replacement, uncertain or untrusted input suppresses timing and erases its samples | Cannot identify all assistive technology. No automatic IV, FA, PA or negative authorship verdict. |

These versioned method parameters are engineering definitions, **not adopted tag
confidence floors**. The six proposed provenance mappings remain unvalidated.
The editor emits `composition_observation` records with an empty `tags` list;
it is separate from assertion schema 0.1.0 and does not change it.

Timing processing is scalar-only at output: raw intervals and pending key codes
exist temporarily in a bounded session, never in storage or exported records.
Suppressing timing deletes them. Pause clears pending key associations. The
summary excludes words, key names, wall-clock timestamps and event sequences.
Coarse statistics and edit lengths can still link sessions; this is not an
anonymity or biometric-law exemption claim. Sharing remains a deliberate local
download. No remote training collection is implemented.

The session stops at 30 minutes or 10,000 events. The field is limited to 20,000
UTF-16 units. Unsupported or malformed input stops observation; reset before
starting another session. The reducer rejects impossible edit lengths and
backwards clocks before changing state. Content-security policy forbids network,
remote scripts, objects and forms; only hashed inline source and styles run.

Verification: `node --test tests/composition-observations.cjs` and
`node scripts/verify-composition-tool.cjs`. The latter builds twice, checks byte
identity, and exercises the actual editor in Chromium and WebKit. It records
native typing, rewrites, timing suppression, pause/reset/export, absence of
network/storage writes and automated accessibility results. Those are not
physical-phone, human accessibility or independently labeled accuracy tests.

## Literal repetition, separately

`python3 scripts/check-repetition.py < your-private-text.txt` prints a local
`repetition_observation`. Default: three exact, case-sensitive whitespace tokens,
at least three occurrences, with repeated tokens covering at least 20% of the
response. Configuration and source hash are included. Text is normalized with
the project's pinned Unicode 15 NFC; spans are Python scalar offsets in the
normalized subject. No raw text is echoed, though hashes and positions can still
reveal or link information. Keep the output private unless you choose to share it.

It refuses input above 20,000 scalars, invalid Unicode, invalid parameters or more
than 64 repeated groups. Poetry, repeated instructions and refrains legitimately
match. `sig.duplicate_loop.v1` describes repetition, not hallucination or falsity;
HP remains unavailable. Run `pytest tests/test_repetition_observation.py` for
span, normalization, benign-context, threshold and refusal controls.

## Development fixtures

`eval/datasets/tag_development/` contains 12 synthetic scenarios each for HP, MT
and FI. A versioned manifest binds every file and row count. They include quoted
claims, legitimate urgency, explicit fiction, changed dates, entity differences,
units and deliberate repetition. Scenario intent was authored by Codex; it is
not independent truth labeling or a frozen release holdout. No accuracy is
computed from these cases.

`python3 scripts/verify-tag-development.py` verifies bytes, unique IDs, declared
provenance and the real evaluator's non-emission of HP/MT/FI. Tampering, duplicate
fields, missing families or fabricated independent/holdout claims fail.
