# Bounded research invitations

Architecture before implementation: extend the existing synthetic-only metadata database with a separately applied invitation-capacity profile. Keep the base prototype and its controls runnable independently. The extension must revoke the intake role’s unmetered insert function and grant only an invited wrapper; no legacy bypass after application.

Store only 32-byte invitation and withdrawal digests plus bounded quota/expiry bookkeeping. Accept only the existing fixed PS metadata envelope, never prompts, examples, contact details, IP addresses or free-form comments. Digests can correlate records; this is not an anonymity claim. A separate maintenance role issues and revokes invented invitations; intake cannot issue invitations or inspect private tables. Review retains the existing minimum-five aggregate.

Serialize each invitation’s submissions with a row lock. Bind a withdrawal digest to one invitation and one feedback ID. A valid duplicate must not consume another slot or change the record. Conflicting/invalid requests must roll back completely. Withdrawal must not restore lifetime capacity or allow the deleted feedback to reappear. Unknown, expired and revoked invitations refuse before insertion. Use bounded lifetime, capacity and retained invitation count; expire bookkeeping with its declared development purpose.

Risks: privileged database administrators remain trusted; locks can wait, so the verifier needs lock, statement and process deadlines. Definer functions require restricted grants, a fixed search path and fully qualified private tables. Invitation retirement must not silently remove deletion protection for a still-valid invitation. This prototype does not mint any live authentication credential, introduce an endpoint or adopt a participant/retention policy.

The executable component must test actual PostgreSQL insert/idempotence, role and legacy-function refusal, quota rollback, duplicate/cross-invitation binding, expiry/revocation, concurrent oversubscription, withdrawal/replay and bounded pruning. Use an ordinary Linux user, a newly owned private socket-only PostgreSQL 18 cluster and invented records; verify shutdown and cleanup. CI must repeat it. Current browser feedback still downloads locally and submits nothing automatically.

Full N-011 remains open for owner policy/endpoint acceptance, provider handling, backup expiry, replacement-host recovery and a consenting human pilot. Component controls are separate from these requirements and from tag accuracy.

References: [PostgreSQL 18 function security](https://www.postgresql.org/docs/18/sql-createfunction.html) and [row locking](https://www.postgresql.org/docs/18/explicit-locking.html). Explicit grants and a restricted search path protect definer calls; row locks serialize the selected capacity decisions. Actual database tests must confirm this application’s behavior.
