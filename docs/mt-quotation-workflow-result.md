# Selected MT quotation workflow result

2026-11-19 · Implemented and executed by Codex MT lane · T-MT/F-019c.

Delivered a separately selected `--check authority-quotation` route through the
existing bounded framing CLI. It preserves the complete unchanged canonical
quotation record, raw and frozen-NFC identities, and exact sources. Closed
validation is followed by actual full-record canonical replay in a second child;
both executions share one six-second budget. An unsupported context, damaged
optional module, malformed/forged result, output limit or replay failure affects
only this selected component. No sibling check or production tag is activated.

The committed baseline rejected this new option. The delivered route reports the
quoted phrase in `The training example says "Experts agree".` separately, while
the explicitly selected legacy authority check keeps its older contract. This is
literal quotation placement, not an inference about endorsement, intent or truth.
Selections using the new option have a separate context-evidence profile; legacy
selections retain their previous profile and row shapes.

Final source-stable evidence:

- `runs/2026-11-19-mt-quotation-workflow-tests-final.json`: 82 affected Python
  controls passed; canonical quotation/language/choice/device source bytes match
  the original base. Includes coherent forged omission, altered context, raw/NFC
  replay, child failure, shared deadline and maximum-size request controls.
- `runs/2026-11-19-mt-quotation-workflow-cli-frozen.json`: 15 actual CLI controls,
  including baseline comparison, quote/marker context, all four explicit checks,
  partial failure and complete private export with no overwrite.
- `runs/2026-11-19-mt-quotation-legacy-cli-frozen.json`: 11 existing combined CLI
  controls pass with the current workflow sources.

Earlier execution records remain historical. The first affected test run had one
incorrect authored expectation about the existing urgency density threshold;
`runs/2026-11-19-mt-quotation-workflow-candidate-1.json` preserves that failure.
The test was corrected; the original urgency method was not changed. The frozen
receipts above identify the final source, not the prior documentation/serializer
snapshots.

The optional engineering verifier additionally uses Git history at base
`eb7873ddc861bfadf921d50d338ab2d2607e0d8b` to demonstrate the previously absent
option. The checker itself works from the source ZIP and standard Python without
Git or third-party packages. Pytest belongs only to the existing development test
setup. Guide links use the existing public source repository, so no new website
route or prepared-reference asset is required by this change.

No scope percentage or global state was changed. Same-method replay is not
independent corroboration or accuracy. Full MT still needs broader context and
negation/endorsement interpretation, accepted error/annotation policy, blinded
human labels/agreement and human route acceptance. No T-MT or F-019c completion,
physical-device testing, OS network sandbox, ML accuracy or deployment is claimed.
The PM owns integration/source-bound inventory review and release acceptance.
