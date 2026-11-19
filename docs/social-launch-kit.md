# AI Trust ID social launch kit

Prepared by Codex for Michael, 2026-11-18. No account is created, connected or
reserved. Use **AI Trust ID** as the display name and request **AITRUSTID** as
the handle everywhere; each platform must confirm availability. A domain handle
such as `aitrustid.com` is a fallback only if Michael approves it.

## Profile copy

Short bio: **Free, open-source checks for AI output. Small tags. Clear reasons.
Explore the preview and help test what comes next. aitrustid.com**

Long bio: **AI Trust ID builds independent tags for specific questions about AI
output. Start with the free PS command-risk preview. Inspect the source, read the
limits, and contribute to tag-by-tag validation. A finding is not a safety
clearance. Account-free checking at https://aitrustid.com.**

Use the existing `site/public/tag-logo.svg` and existing seasonal colors. Do not
claim certification, independently validated accuracy, an approved App Store
release, all-format detection, or that every planned tag works today. Do not use
personal or THT accounts as this brand.

## Account setup and security

Start with the channels Michael will actually maintain: LinkedIn organization
page for development updates; Bluesky for public discussion; Instagram and
YouTube for short phone demonstrations. X is optional. These are proposed
channels, not created accounts. A platform may require a real administrator
account; keep its personal credentials separate from the public brand.

Michael creates each account, accepts its terms, chooses a dedicated project
inbox, enables the strongest available MFA and stores recovery codes privately.
Record the actual platform, handle, profile URL and administrator privately.
Never put credentials, recovery codes or private administrator identity into the
public repository. Only add a public connected destination to
`communications/accounts.json` after verifying control and its integration.
No paid social/API subscription is authorized by this kit.

## Release communication workflow

1. Add or update a public brief in `communications/releases/` with version,
   exact use case, limitations, public URL and repository evidence.
2. Run `python3 scripts/release-announcements.py`. CI also prepares this queue
   when briefs, changelog, policy, source or tool files change. Download the
   `ai-trust-id-release-review-queue` artifact from the workflow.
3. Michael reads the exact draft, checks its evidence and chooses a verified
   destination. Do not announce a PR draft as a shipped release.
4. Record the actual approval in a private JSON file. Required fields:
   `draft_sha256`, `platform`, `handle`, `approved_by` equal to `Michael`,
   `approved_at`, and `expires_at`. Both times are timezone-aware ISO timestamps;
   approval expires within seven days. An agent records approval only after
   Michael actually gives it. The file is an audit record, not a digital signature.
5. Run `python3 scripts/release-announcements.py --approval /private/approval.json`.
   This refuses disconnected accounts, stale copy/evidence, expired approvals
   and other approvers. It exports an exact handoff; **it does not publish**.
6. After accounts exist, connect the chosen publishing tool and verify one
   explicitly approved post. Record the returned platform post ID and URL.
   Use the handoff's idempotency key; uncertain delivery requires checking the
   destination before retrying. Do not report a successful network post from an
   exported JSON file. Adapt/split long copy per platform and obtain a new exact
   approval after every edit. The current queue intentionally does not truncate
   evidence limits to fit a short-post character cap.

## Transparency and boundaries

The changelog remains the complete engineering audit. Social briefs are a small,
reviewed public explanation with a use case and limits. Security reports,
credentials, private examples, embargoed vulnerabilities and participant data
never belong in a social brief. Public community discussion is not research
consent or permission to train a model.

Existing evergreen drafts remain available through
`python3 scripts/build-social-drafts.py`; they verify current public page copy.
Automatic account creation, connected publishing, platform moderation staffing,
and analytics are **not complete**. No signup or social follow is required to
use the personal checker.
