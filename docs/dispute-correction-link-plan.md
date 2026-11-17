# Private dispute correction link

The community workbench records a report's target and replacement as UUIDs.
An editorial correction retains the original assertion UUID and identifies its
immediate predecessor by the SHA-256 digest of that journal's exact bytes. It
has no separate UUID. Assign the correction a private reference for use with
the existing workbench and keep the two identities distinct.

- `prepare` reads an open wrong-result report from the selected synthetic SQLite
  workbench under the moderator's private role. It checks the existing editorial
  correction packet and its actual JSON output by reconstructing the validated
  editorial decision. It pins the current method, original assertion and subject,
  exact prior journal, correction packet selection, exact correction output,
  report target, selected moderator, and workbench file identity. The registry
  creates one immutable plan per report and assigns a fresh replacement UUID.
- The moderator enters that UUID in the usual `review_report` operation with
  `correction_referenced`.
- `link` checks those artifacts again. It requires the same workbench, unchanged
  report origin, the recorded moderator and disposition, and the assigned UUID.
  It makes a new owner-private link directory keyed by report ID. A second link
  for the same report in that registry refuses without overwriting the first.

Only a normal editorial correction with its source, normalized evaluated subject,
review selection, exact prior JSON, and actual correction JSON is accepted. The
correction must have a changed decision or reason, an exact predecessor digest,
and a recorded time between the selected prior journal and the current clock.
The new output holds references and digests. It contains no message or subject
body, contact details, raw tag signals, or filesystem paths. The database
identity includes stable filesystem identities of the workbench directory,
database file, and lock file. Copied or rebuilt stores require a new plan.

The local operator controls filesystem trust and synthetic role selection. This
is a selected single hop within one owner-private registry. It does not prove
identity, authenticity, a globally current correction or model accuracy. Unrelated
workbench state changes leave the report eligible. Altering the selected evidence,
pointing a report to another assertion, closing the report under another disposition,
or substituting another database or moderator refuses. A lost or damaged bridge
registry requires operator review. The link does not replace an assertion or modify
the community store. Any future production connection needs a separate contract.

Use existing private filesystem and editorial helpers. Own the bridge module,
CLI, focused tests, instructions and evidence. Global scope, website, native,
community core, database schema and workflow remain under separate review.
