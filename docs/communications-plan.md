# Release communication architecture

Codex implementation plan, 2026-11-18. Brand requested by Michael: AITRUSTID.

A checked-in public release brief carries version, independent use cases, limits,
and exact evidence paths. CI turns each brief into review artifacts on every
brief, source, policy or changelog update. Drafts carry a digest of their exact
text, destination and current evidence bytes. They are never a release gate or
an accuracy claim. Failures in communication do not stop a tag check.

Michael approves the exact message and destination after reading it. A changed
message, account, evidence file or expired approval invalidates the handoff.
The local approval file is an audit record, not cryptographic identity proof;
its access depends on the operator's filesystem and review process. Neither CI
nor an agent should create an owner approval without an actual owner instruction.
The export command refuses inactive destinations. It prepares an approved
handoff, not a network send, and never asks for a social password.

No social accounts exist or are connected at this implementation's start.
AITRUSTID is a requested handle, not a reserved or checked handle. Account
creation, MFA and platform terms remain owner steps. Connection and a real
approved post must be verified before claiming automatic social publication.
No paid platform, tracking service, automatic direct message or personal/THT
account is used. The current announcement generator is independent of Metricool.
