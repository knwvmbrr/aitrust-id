# Account and private history delivery

## Architecture recorded before feature code

ROOT approved this isolated implementation on November24,2026 under the owner's instruction to make signup and optional paid personal history work. Branch codex/account-history-delivery starts at1b6c91ed; no scope branch or provider configuration is merged. The separate accepted planning commit5adcb87a, docs/personal-tag-history-plan.md, selects paid history and free checking/community participation. It is a written contract, not an operating account service.

Existing tools/community_core.py has six fixed synthetic principals and no credential authentication. Its SQLite/PostgreSQL adapters are practice software, not production account stores. tools/remote_tag_server.py intentionally serves account-free /v1/check,/v1/tags,/healthz and rejects cookies; gateway installation tokens and disabled research /v1/feedback do not identify users. These implementations and their contracts remain unchanged. Relevant community/API source files are byte-identical to origin/main898dc254.

The first deliverable is a functioning isolated account API with durable local transactions: two real generated test accounts can sign up, log out/in, maintain distinct private histories, exercise server-owned active/inactive entitlements, export/delete after expiry, and delete their account. It is not a fake checkout or a claim of live public deployment. SQLite is explicitly development/review only; the owner's operational database choice remains PostgreSQL. No real participant data, credentials, payment provider, DNS or production collection is activated by this source work.

## Separate trust boundaries

| Boundary | Authority and audience |
| --- | --- |
| Account/session | Canonical UUIDv4 owner, pseudonymous unique username and password; opaque server session; no verified email, real-world identity or recovery claim |
| Public forum identity | A future member mapping may expose the chosen handle; never credential/session, private history, billing identity or research data. Current synthetic moderators are not promoted to authenticated roles |
| Private history | Only the authenticated owner; explicit enablement, fixed metadata, independent retention and deletion |
| Entitlement | ROOT's separately owned operator ledger assesses account UUID; a client cannot grant itself history access. Initial operator grant is not verified payment |
| Research | Existing independent permission/store; signup, history enablement and payment confer no research/training/publication consent |

## Approved HTTP contract

All new routes live only in the new account app:

- POST /v1/account/signup and POST /v1/account/sessions: exactly username/password.
- GET /v1/account/session: bootstrap/session state and CSRF; DELETE same route logs out.
- GET /v1/account/entitlements: server-owned assessment; no HTTP grant route.
- GET /v1/account/history: bounded owner list; POST accepts enable/disable/append; DELETE removes all owned history and disables recording.
- DELETE /v1/account/history/{event_id}: canonical owned UUIDv4 only.
- GET /v1/account/history/export: fixed JSON metadata download, no payment requirement.
- DELETE /v1/account: password reauthentication and transactional account/session/history removal.

ROOT additionally approved exactly GET /account/,/account/app.js,/account/style.css from the trusted site/account directory. Missing assets refuse; no caller-selected filesystem path, listing or upload exists. All account/static responses are no-store/nosniff/frame-denied/no-referrer/noindex; the page uses self-only script/style/connect CSP. ROOT owns those UI files.

Existing free checker routes are neither wrapped nor gated. A missing/broken entitlement engine refuses enable/append only. History reads, disablement, export, deletion, logout and account deletion do not invoke it. Expired subscription data remains accessible within the independently disclosed30-day retention period.

ROOT supplies tools.history_entitlements.HistoryEntitlements(directory).assess(account_id,now). The exact callback result is {format:account-history-entitlement/v1,account_id,state:ACTIVE|INACTIVE|UNAVAILABLE,valid_until:integer|null,revision:integer}; only trusted app construction supplies the callable. Invalid/unavailable assessments fail closed for writes. No client-paid flag, receipt, redirect or external URL is accepted.

## Session and storage design

Use the existing approved verification interpreter's FastAPI0.143.0/Starlette1.7.0/Uvicorn0.34.0; install no dependency. Domain/storage remain standard-library testable. Owned paths are services/accounts/*,tools/account_*,tests/test_account_*, this guide and fresh own run/event/CHANGELOG entry. ROOT owns entitlement code and web UI; shared policy/registry/state/scope files are untouched.

The trusted factory also accepts asset_directory for combining ROOT's separately owned account UI with this backend during review. That configuration is never request-controlled; only the three fixed asset names can be read. Review requests allow at most16 simultaneous body readers,16KiB/32-level JSON and5 seconds per body; at most two owned blocking operations run at once. Cancellation/timeout does not release a worker's slot until its thread actually finishes. An uncertain/disconnected response is not a promise of rollback: refresh before retrying, and history event UUIDs make identical append retries idempotent.

Passwords are15–128 characters/at most512 UTF8 bytes, preserved without silent normalization; scrypt N32768/r8/p3/dklen32 with random16-byte salt and64MB KDF allocation ceiling. At most two admitted password operations; unknown-user login performs the same KDF and generic refusal. No plaintext password or session/CSRF token is stored or logged. Usernames are canonical lowercase ASCII3–32 characters. Signup/login have bounded per-peer and per-username security rate state; diagnostics contain fixed outcomes only.

Sessions use random256-bit opaque tokens; only domain-separated SHA256 digests are persisted. Cookie is HttpOnly,SameSiteStrict,Path=/v1/account,Secure for HTTPS. Explicit loopback development alone may disable Secure. GET/session can create a10-minute anonymous bootstrap; all writes require its/session's CSRF and exact Origin. CSRF is an HMAC of the validated opaque session secret with a fixed purpose, never a credential stored in browser storage. Signup/login rotate the session atomically. Authenticated sessions expire after24hours or1hour idle; session/object ownership is checked centrally. No installation/research bearer token or arbitrary forwarded header is trusted.

Account deletion atomically removes account/session/history data and queues the UUID for ROOT's optional server-owned entitlement-forget callback. A callback outage leaves a durable private pending-cleanup row and an honest pending response; it never restores the account or its history. A bounded operator retry drains those rows. Active accounts plus pending erasures share the4096 capacity, so erasure cannot exhaust a separate queue. Export/history deletion never calls assessment or forget. SQLite deletion is logical and makes no backup/physical-erasure guarantee.

SQLite uses an owner-private0700 directory and0600 single-link regular database outside every Git ancestor, strict fixed schema, parameterized SQL, foreign keys, DELETE journaling, memory-only temp data, short locks and directory/file identity checks. Initial creation is exclusive; existing stores are never silently initialized or overwritten. Review runtime bounds are4096 accounts,8192 sessions,1024 bootstrap sessions,4096 rate buckets and512MB database. These are engineering caps, not production capacity claims. No physical-erasure/encryption/backup claim is made; production PostgreSQL/at-rest/key/recovery acceptance remains required before collection.

History defaults off. Each account has independent1000-entry/5,000,000-byte/30-day bounds. Expiry is checked on reads/writes; persisted clock rollback refuses. No silent quota eviction. An append is a client-declared record of display, not a verified assertion: UUIDv4 event, local display time, fixed adapter, tag/state and bounded method identity. Fixed source label and explanation derive from adapter/state. No raw text, pixels, excerpt, URL, title, subject fingerprint, arbitrary explanation, account selector or training flag is accepted. Server receipt time controls retention. Corrections are future separate linked records, not silent mutation of history.

ROOT approved a fixed summary-import adapter before its code addition. The first UI imports an actual existing ai-trust-id-share-summary/v1 PS download and sends only the six history fields. Its label is Imported summary; display time means untrusted client import time, and original viewing time is unknown. This is not a claimed automatic screen observation. The client checks the actual current method identity/context-v6 and never sends the source file body, filename, original text or subject hash. Automatic web/extension/native adapters remain separate integration work.

## Verification and risk gates

Apply the security-best-practices skill and its FastAPI/general-JS guidance: central auth/object checks, explicit response projection, CSRF plus strict origin/host/CORS, bounded JSON/body/time/concurrency, no secret web storage, no untrusted HTML, no debug/access logs or dynamic outbound requests. TLS/proxy production configuration cannot be proved by a local test.

Execute domain/store controls and the actual FastAPI application with the approved interpreter: two-user signup/login/session rotation/revocation, absent-user KDF, CSRF/origin/host/ownership, entitlement inactive/active/expired/outage, enable/append/revisit/export/delete, quota/retention/clock/corrupt storage, no leaked password/token/input fields and account deletion. Also run real loopback HTTP server calls using generated fixture credentials only; retain source hashes and failed controls. ROOT integrates its real operator entitlement engine and web UI separately, then performs distinct review. No original requirement closes from these software proofs, no source profile admission/production availability/payment verification is inferred.

Initial source controls executed19 groups:18 passed and one configuration-refusal assertion errored. A non-IP hostname in explicit HTTP development configuration raised ipaddress.ValueError rather than the fixed account refusal; no request was admitted. Preserve that first log/source capture. Before correction, convert invalid IP configuration to the existing fixed refusal, without enabling any non-loopback HTTP configuration or changing routes/authentication.

ROOT's pre-freeze review required two further corrections, recorded before code. The current official OWASP Password Storage Cheat Sheet lists N32768/r8/p3 for its32MiB scrypt alternative; replace the initial p1 with p3 while retaining64MB allocation/two KDF slots. Fresh private stores use schema version2 and an explicit KDF identity; version1 stores refuse rather than silently reinterpret existing hashes. All earlier control phases are retained as p1/review-source evidence only. Also purge globally expired history at every successful transaction and startup maintenance, with a bounded60-second maintenance task using the same two operation slots. This reaches cold accounts without owner access; API eligibility always expires at30 days. Expiry/deletion remain logical and do not claim exact physical or backup erasure. Primary source: https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html .


## Transaction-time correction approved before code

An isolated real-store counter confirmed that a request timestamp captured before authentication could become stale when a different maintenance transaction committed a later time before the route's second transaction. This caused a false clock-unavailable refusal despite a nondecreasing server clock. It is independent of the unresolved first WebKit attempt. The frozen earlier source and actual two-user HTTP evidence remain historical.

Carry only the trusted server clock callable across the app/store boundary, resolve it after each successful BEGIN IMMEDIATE, and use that one selected integer throughout that transaction. Direct integer fixture times retain the same strict persisted rollback comparison. Multi-phase account erasure/entitlement forget preserves the original callable and samples again after each later lock. No max/clamp, clock reset, session/CSRF/rate/KDF/retention change or HTTP clock override. Invalid or actually decreasing clocks still fail closed and roll back. The same schema-2 development database is retained on coordinated service restart.
