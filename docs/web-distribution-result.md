# Website JavaScript notice repair — implementation result

Implemented and locally evidenced on the isolated source branch. Protected
integration, the discoverable public link and live-origin byte checks belong to
the PM's combined publication step; this document does not claim they happened.

The normal site build now prepares its notice files before existing build steps.
The actual resulting artifact carries complete notice text for 34 observed npm
package records and one **separately pinned upstream project supplement**. Its
35-package index preserves exact archive digests, original notice bytes and their
bundle offsets. The selected-cohort SPDX JSON uses `NOASSERTION` concluded
licenses and validates against the existing pinned SPDX 2.3 schema.

The initial 35-complete assumption was wrong. One exact archive,
react-remove-scroll-bar 2.3.8, carries no matched license file. The publisher's MIT
declaration is real evidence; the separately pinned upstream MIT text is carried
without pretending its 2.3.7 source commit proves correspondence to 2.3.8. The bundle
itself says that relationship is UNVERIFIED. The original failed preparation and
later malformed-identity/direct-API counterexamples remain preserved.

Current evidence:

- 33 focused controls pass, including staged publication failure/rollback,
  changed/missing notices, unreviewed packages, malformed root and identity fields,
  fixed private diagnostics, complete byte ranges and independent PS admission.
- 35 exact cached tarballs pass SHA512 lock-integrity and observed SHA256 checks;
  every matched full archive notice is compared without package execution.
- Actual `npm run build:site` passes and executes mandatory preparation. The built
  notice files and carried project license match source-derived bytes.
- Actual `npm run reviewed-release --prefix site` exits 1 as required by the still
  blocked global web-checker policy. Actual independent PS source artifact
  verification still exits 0.
- Built notice directory is 755 and its three files are 644. No browser suite,
  installation, new network service or production change was performed.

[Current actual artifact proof](../runs/2026-11-21-web-js-current-built-artifact.json)
· [Root-shape correction](../runs/2026-11-21-web-js-root-shape-correction.json)
· [Earlier private-diagnostic correction](../runs/2026-11-21-web-js-malformed-identity-correction.json)
· [Initial refusal](../runs/2026-11-21-web-js-initial-refusal.json)
· [Instructions and limits](web-distribution.md).

F-057 and X-02 remain open. Carried attribution does not complete the embedded
runtime, native/build-tool graphs, source offers, the other 13 policy scopes or
eligible full release-artifact SBOM/signatures. No legal clearance, detector
accuracy, tag issuance, new original closure or whole-project percentage follows.

Independent review then found a resource-bound defect: the original final-size
check ran after notice retention and bundle construction. A small reduced-cap
counter reproduced it without allocating large data. The correction has eight
current affected resource/prepare/rollback controls passing; the earlier33-test
source proof remains historical. Retained source bytes, duplicate notice
occurrences, copies and headers are admitted before reading/appending. The
actual notice bundle text remains byte-identical. Updated source bindings and
artifact proof are recorded separately; no archive download or broad browser
suite is repeated for this correction.
