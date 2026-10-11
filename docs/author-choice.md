# A receipt is your choice

You can use the personal checkers, write in the offline editor, pause, reset and
leave without creating a receipt, generating a key or sharing a file. Receipt
creation and group endorsement are separate commands you choose. The editor
never creates a signed receipt or uploads an editing summary automatically.

`protocol/author-choice.cjs` defines `author-choice/1.0.0`. Its conforming policy
requires `receipt_required: false`, `ordinary_use_without_receipt: true`,
`automatic_receipt: false` and `automatic_upload: false`. No extra policy fields
or truthy string replacements are accepted. Unknown versions fail closed.
`authorize` allows ordinary use and observation without a receipt. Export,
issue and endorse require an explicit affirmative author choice. The editor
uses this control before observation and chosen local exports; the receipt
command checks it before writing a new receipt. Future organization integrations
must call the same control before proceeding with their workflow.

A policy that demands a receipt to use the tool is rejected. An organization's
policy cannot override this by changing a public tag or silently adding fields.
This is an enforced reference-implementation conformance rule (F-128). It cannot
detect a manager's demand outside the software, prohibit an employer by law or
prove a consent was freely given. No organization or identity service is running.
Group records continue to report coercion `not_assessed`; no change makes a
signature proof of voluntary human authorship.

Run `node --test tests/author-choice.cjs` and
`node scripts/verify-composition-tool.cjs`. The browser checks include ordinary
writing and reset with no download, no network and no storage. Human
comprehension, real-device accessibility and external organizational acceptance
remain separate scope requirements.
