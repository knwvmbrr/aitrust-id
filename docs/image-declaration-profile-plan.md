# Attached PNG action declarations — plan before implementation

Owner: Codex image-evidence lane. PM: Codex integration lead. 2026-11-16.
Base: `85b885f`; the prior readable-inspection increment is preserved unchanged.

## Normative primary-source review

Sources retrieved on 2026-11-16, not inferred from competing products:

- [C2PA 2.5, Actions](https://spec.c2pa.org/specifications/specifications/2.5/specs/C2PA_Specification.html#_actions),
  sections 16.4.1.1–16.4.1.4: an action describes a recorded operation. Creation
  alone does not identify AI. Array order generally does not establish chronology.
- [Digital Source Type](https://spec.c2pa.org/specifications/specifications/2.5/specs/C2PA_Specification.html#_digital_source_type)
  and [normative actions schema](https://spec.c2pa.org/specifications/specifications/2.5/specs/C2PA_Specification.html#cddl_annex_actions):
  `digitalSourceType` belongs to an action, not an automatic whole-image verdict.
- [IPTC trainedAlgorithmicMedia](https://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia)
  defines creation using a trained generative model. Its canonical identifier is
  `http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia`.
- [IPTC compositeWithTrainedAlgorithmicMedia](https://cv.iptc.org/newscodes/digitalsourcetype/compositeWithTrainedAlgorithmicMedia)
  defines generative augmentation/correction/enhancement. Its canonical identifier
  is `http://cv.iptc.org/newscodes/digitalsourcetype/compositeWithTrainedAlgorithmicMedia`.
  IPTC NewsCodes are CC BY 4.0; these terms are attributed to IPTC.
- [Templates](https://spec.c2pa.org/specifications/specifications/2.5/specs/C2PA_Specification.html#_action_templates)
  can supply inherited values; [Changes](https://spec.c2pa.org/specifications/specifications/2.5/specs/C2PA_Specification.html#_changes)
  can scope operations to regions. This first narrow profile does not resolve
  either form and must not silently treat them as whole-asset declarations.
  [Assertion metadata region of interest](https://spec.c2pa.org/specifications/specifications/2.5/specs/C2PA_Specification.html#_region_of_interest),
  section16.9.1.5, can also scope an assertion to part of an asset. This profile
  refuses that scope and unresolved action `parameters.relatedAssertions`.
- [Active manifest](https://spec.c2pa.org/specifications/specifications/2.5/specs/C2PA_Specification.html#_active_manifest)
  and assertion/claim validation separate current asset binding, signed claim and
  referenced-assertion hashing. A matching assertion hash must name the specific
  active actions assertion; an ingredient's success cannot stand in for it.
- [Pinned c2pa 0.91.0 ManifestAssertion source](https://docs.rs/c2pa/0.91.0/src/c2pa/manifest_assertion.rs.html#36-77)
  defines a label, optional instance number and separate created/gathered flag.
  An instance above zero adds `__<number>` to its JUMBF label. Attribution is not
  inferred from a producer-supplied display name.

The attempted C2PA 2.5 AI/ML guidance URL returned404. The rules above rely on
the successfully retrieved normative specification and authoritative IPTC terms,
not on that unavailable page. No claim of full C2PA 2.5 validator conformance is made.

## Architecture

Add a separate opt-in `--profile action-declarations-v1` to the existing inspector.
Default inspection JSON, text wording, exit codes, SDK pins/settings and parser
resource/egress boundaries remain unchanged. The new profile has its own version
and source identity and invokes the existing file inspector exactly once.

Read only the ACTIVE manifest's own bounded actions assertions. Recognize two
explicit pairs: `c2pa.created` with canonical `trainedAlgorithmicMedia`, and
`c2pa.edited` with canonical `compositeWithTrainedAlgorithmicMedia`. These mean
only that the record declares generative AI use in that action. They never mean
full automation, absence of human involvement, a human rework sequence, FA or PA.
Unknown/custom source types, `softwareImage`, `compositeSynthetic`, capture and
human-edit claims cannot supply a positive AI declaration. Ingredient-only data
does not supply a declaration about this active asset.

Before a declaration can be reported as bound, require current image-binding and
record-signature matches plus exact active-signature and actions-assertion
validation URIs. Missing or adverse binding is unknown. Unknown signer trust and
skipped revocation remain separate, visible observations, not hidden approvals.
No producer name or trusted-looking free text grants authority.

Reject malformed/oversized structures. Unsupported templates, regional/related
actions and ambiguous attribution stay explicitly unsupported or unknown. Do not
infer sequence from array position or claim completeness from missing events.
Multiple inception actions are an unsupported record structure, not contradictory
AI declarations; generation
followed by an AI editing declaration is compatible and is not a contradiction.

The result contains only fixed vocabulary, bounded action references, selected
asset/method identity and separated validation axes. Human text omits hashes,
paths, names, URLs, locations, descriptions, software names and raw assertions.
AI origin and content truth remain unestablished; `tags` stays empty. Explicit
private full-report export retains its existing separate permission and file rules.

## Risks and validation gates

1. Signed producer statements can be false. Test fixtures are hand-built pixels
   carrying authored declarations, not AI-origin ground truth or training labels.
2. Unlisted or ingredient assertions could be misattributed. Require specific
   active-assertion hash success and never borrow another manifest's success.
3. Templates, regions or imprecise values could exaggerate scope. Refuse those
   forms in this version and publish that coverage limit.
4. Do not hide adverse signature, asset-binding, trust or revocation observations
   behind an overall validity badge. There is no overall authenticity verdict.
5. Preserve the old CLI byte output and exit behavior. Add an isolated profile;
   malformed input/worker misuse cannot activate new interpretation accidentally.

After PM validation scheduling, execute focused semantic/privacy/refusal tests,
the existing parser controls and actual pinned-SDK positive/negative authored
fixtures. Include altered/unsigned input, exact URI/instance binding, unknown
values, ingredient-only claims, unsupported inception structures, malformed/oversized data and default
compatibility. No local Docker, browser/native build, model download, real issuer,
public endpoint, tag adoption or independent accuracy claim is part of this work.
All original requirement percentages remain unchanged.
