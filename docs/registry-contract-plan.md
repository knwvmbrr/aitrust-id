# Optional registry contract — acceptance alignment

F-044's preserved baseline is to **define approved fields, access, retention and
deletion before enabling storage**. It does not require secretly implementing the
legacy hash dashboard. The owner approved invited metadata-only submissions,
Michael as operator, 30-day active retention and 7-day encrypted backups, with
collection disabled until security/withdrawal/recovery tests pass. The historical
hash-only registry remains a proposal; hashes, spans and content are not accepted
by this pilot. N-011 and F-141 retain actual deployment, recovery and real-pilot
acceptance; F-045/F-161 retain their separate reporting/long-horizon jobs.

Before implementation: publish one machine-readable accepted policy and an offline
validator. Pin the exact owner decision receipt; validate the endpoint, operator,
closed field vocabulary, separate opt-in, account-free checking, role boundaries,
retention and required collection gates. Refuse collection_enabled=true rather
than letting a config toggle substitute for actual deployment evidence. The
current validator is deliberately a disabled-pilot contract check, not an upload
service or activation authority. Existing local preview/download must remain
independent and make no network calls.

Acceptance: validate the exact accepted contract, exercise wrong endpoint/purpose,
mandatory signup, extra content/hash/span/identifier fields, retention expansion,
missing withdrawal/recovery/privacy gates, enabled collection, ambiguous JSON,
changed owner receipt, links and oversized policy refusal. Execute current
metadata preview/download tests. Keep the source and decision pins stable, record
exact execution and preserve all 202 IDs. Completing the definition must not mark
participant recruitment, recovery, training or an operating registry complete.

Risks: a source owner can fabricate evidence, and a digest cannot authenticate a
human approval. This records the actual supplied approval and catches accidental
policy drift. A compromised host/provider or unauthorized alternate collector
cannot be ruled out by a policy validator; those deployment/security boundaries
remain open. No endpoint beyond the specifically approved path is added.
