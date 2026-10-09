# Public communication and protected research data

Owner direction, 2026-10-08: the website is the public front door; community
messages should be live and visible to everyone. Security and user privacy remain
requirements. This is an accepted product direction, not an implemented forum.
Existing scope records F-136, F-137 and N-011 carry this work; no tag is removed.

## Architecture before implementation

The catalogue provides short paths into public discussion, tag challenges and
research contributions. The remote application validates each action and uses
local PostgreSQL sockets. Browsers never receive database credentials or direct
SQL access. The installed extension continues to evaluate locally; contributing
data is optional and a site outage must not block local tags.

Public community publication and research submission are different actions with
different audiences. They must have distinct application permissions and storage
boundaries. Separate schemas alone are insufficient: every write, read, live
event and moderator action must enforce its audience and actor permissions.
The public live stream can read only approved public records, through a public
projection that explicitly lists allowed fields. It cannot broadcast internal
database rows or general change events. Research intake and the public stream
must have separate runtime database roles; the current foundational intake role
is not a production authorization design for both services.

| Information | Visibility and purpose |
|---|---|
| Community discussions, public tag challenges, official replies | Public reading without an account; posting notice says public before submission |
| Product decisions, methods, release evidence, policy changes | Public versioned explanations with dates and responsible roles |
| Moderation actions | Public reason category, timestamp, appeal route and record ID; publish no removed personal information |
| Submitted research metadata and optional examples | Restricted review/analysis access with purpose-specific consent; predictions remain separate from independent labels |
| Vulnerability reports, harassment evidence, deletion requests | Private intake; publish a safe summary when appropriate, without exposing reporters or an unfixed exploit |
| Credentials, session tokens, backup encryption keys, private contact details | Restricted operational access; never in public posts, streams, exports or logs |

Public discussion does not consent to model training. Research contribution does
not consent to public publication. Neither is silently inferred from using a tag.
The owner must still select collection, retention and dataset-release policy.

## Security requirements and failure thresholds

- Serve authenticated actions and public updates over HTTPS. Verify sessions,
  object ownership and moderator roles server-side; protect cookie-authenticated
  writes against CSRF. Require MFA for privileged administration.
- Treat every post as hostile input. Render text safely, disallow executable HTML,
  use a restrictive content policy and reject oversized or malformed payloads.
  Uploaded files and embedded third-party resources remain disabled for the first
  community increment unless a separate safe processing contract is accepted.
- Bound posting, connections, pagination, event buffers, retries and database
  queries. A disconnected reader catches up from public event IDs; duplicate
  submissions do not create duplicate posts. A queue cannot grow without limit.
- Check publication eligibility before persistence, serialization and streaming.
  Personal-information detection is fallible. Suspected leaks can be withheld
  for review; accidental secrets can be removed from public access promptly.
- Display edited timestamps and public moderation tombstones. Do not retain
  removed secrets in publicly accessible edit history, search, cached pages or
  replay events. Private audit access is limited and retention is explicit.
- A moderation restriction must also apply to the live stream. Retraction events
  tell connected clients to remove content; the server cannot recall copies
  already saved by third parties. State that limit before public posting.
- Separate production and synthetic staging, credentials and backup namespaces.
  Keep SQL permissions minimal. No shared administrator token in browser code.
- Encrypt independent backups and prove restoration. Disk encryption at rest is
  not configured on the current VPS and must not be advertised as implemented.
  Before sensitive text storage, select the at-rest protection and key-recovery
  boundary. Provider/root access remains part of the hosting threat model.
- Avoid logging post bodies, research examples, authorization headers and secrets.
  Log security-relevant state changes with bounded identifiers and outcomes.
- Disable the affected submission/publication function on confirmed unauthorized
  disclosure; preserve local tag evaluation. Publish a safe incident account.

Transparency covers decisions and public communication; it is not a promise of
perfect detection, automatic publication of private reports, or permanent public
retention of an accidental leak. Security cannot be established by configuration
alone or described as an absolute guarantee.

## Delivery order and acceptance evidence

1. **Host foundation:** deployed private PostgreSQL, key-only SSH, dual-stack
   firewall and actual role checks. Independent backup, MFA/VPN, alerts and
   application authorization remain separate gates.
2. **Private synthetic intake:** accepted record/audience/retention contract,
   authenticated writes, deduplication, quotas, deletion, failure isolation and
   fresh-host restore. No real submissions during this verification.
3. **Public community:** safe text posting, public history, moderation, appeal
   routing and bounded live updates. Publication acceptance requires two distinct
   users plus moderator tests: unauthorized access denied; research/private
   markers absent from public responses, replay, logs and exports; XSS strings
   inert; CSRF rejected; throttling/outage/reconnect/retraction exercised.
4. **Real onboarding:** reviewed permissions and threat boundaries, usable
   reporting, tested operational alerts, backup recovery and clear public-post
   and research-consent notices. The owner accepts the actual tested result.

No route name or public endpoint is selected by this document. A concrete
application contract precedes implementation. Public community and training are
not yet live. Codex owns implementation and verification; the owner chooses
collection/retention, administrators and launch acceptance. Independent reviewers
review the boundary and evidence; they do not substitute for executed checks.
