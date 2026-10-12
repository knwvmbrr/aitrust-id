# Reference changes without misleading reuse

Architecture before implementation, 2026-10-12. This is a separate offline
reference-maintenance component for T-NF, F-020a and F-020b; it does not issue
NF/FI tags or change a production allowlist.

Capture the old and current private corpus, exact subject and prior lexical
observation once using the existing owner-only descriptor-based reader. Validate
both corpus envelopes. Recompute the prior selected observation with its exact
current supported method and parameters; altered findings, spans, method identity
or misleading truth flags must refuse before any reuse decision. Unsupported
historical methods remain unavailable, rather than reconstructed by guessing.

For each prior finding, compare its exact document identity/hash and NFC passage
span with the current document. A changed or removed document invalidates that
finding's reference context. Unrelated unchanged documents retain only their
pair context. Any corpus-manifest change invalidates the old global retrieval
ranking, even if a selected pair stays byte-identical: a newly added passage may
rank ahead of it. Report those two results separately. Never promote retained
pair context into a current NF/FI verdict or independently corroborated result.

Accept an optional strict, hash-bound, caller-declared review-window policy for
current documents. The caller supplies the evaluation time explicitly; unknown,
not-yet-open, within-window and elapsed states remain distinct. A timestamp does
not authenticate a source, establish its publication date or prove freshness or
truth. No network search, timestamp inference or automatic clock-dependent
reclassification. A source hash/policy mismatch refuses the policy rather than
borrowing another document's window.

Risks: hashes can link private content, declared dates can be wrong, and lexical
selection ignores semantics. Public stdout therefore contains counts and a short
next action only. Detailed source IDs/hashes/offsets require an explicit new
owner-private destination outside source control. No source text is exported.
The component accepts no URLs, auth credentials, model invocation, endpoint,
upload, user tracking or background retention. Bound file, document, result,
date and nested JSON input; reject duplicates, nonfinite values, unsafe files,
unknown fields and corrupted evidence. Failed checks return one constant private
input/contract diagnostic, never an exception containing text or a path.

Execute actual CLI and hostile controls on Mac and owned non-root network-denied
Linux staging. Preserve raw failure receipts privately and publish only safe
counts/source identities. Keep independent claim accuracy, human operation,
actual source authority/freshness and full tag integration open.
