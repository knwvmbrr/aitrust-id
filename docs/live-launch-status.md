# Live launch status — 2026-10-08

The public development catalogue is live at https://aitrustid.com and
https://www.aitrustid.com. Both Pages domains are active; HTTPS responses match
the reviewed build. The provider address https://aitrust-id.pages.dev also works.
It contains 14 personal tag records, six organization offerings and the complete
198-record preserved scope. The production build and external checks pass: all
20 modals, eight footer modals, keyboard focus, nested report drafts, mobile and
200% text, no-JavaScript references, no unexpected outbound requests, and no axe
violations. A separate ordinary browser context verifies the production CSP and
working interaction without a CSP bypass. This is catalogue publication, not an
accuracy-certified tag release or a remotely hosted evaluation service.

Deployment: `5e75ffe7-a23f-4d13-b9c5-aa8ab4089e9b`; only the reviewed `site/dist`
assets were uploaded. Known SMTP, notification and recovery secret literals were
absent. The working tree is dirty and its implementation has not been pushed to
GitHub. Deployment metadata explicitly identifies that dirty state; the deployed
file hash manifest is the source of publication truth.

The iCloud test arrived in the owner’s inbox; separate primary email alerts are
now enabled alongside both HTTPS senders. Browser desktop notification permission
and storage of the reader login still await the previously requested confirmation.
An independent offline recovery copy, secret retrieval and a complete replacement
host drill are not verified. No real research collection is enabled.

The initial own-domain check found Cloudflare automatically injecting its Web
Analytics beacon. Publication verification failed on that external request.
`Cache-Control: public, max-age=0, must-revalidate, no-transform` now preserves
the reviewed response without proxy transformations. Full external checks pass
with zero unexpected requests; both domain response hashes match the build.
Cloudflare still receives ordinary hosting connection metadata. A Python default
user agent received its HTTP 1010 integrity rejection; browser verification and
an identified Mozilla-compatible verifier pass without disabling that protection.
See [Cloudflare automatic-injection documentation](https://developers.cloudflare.com/web-analytics/get-started/).

## Remaining product gates

| Gate | Owner | Required evidence |
|---|---|---|
| Public source publication | Engineering | Scoped tree and reachable-history privacy audit, reproducible checks, normal push; no mirror |
| Moderated public conversation | Engineering + owner | Accepted posting/privacy/moderation rules; authenticated posting, abuse limits, public messages, correction/retraction tests |
| Private reports and research intake | Engineering + owner | Accepted consent/retention, auth, quotas, separation, deletion and restore checks; sensitive reports stay restricted |
| PS accuracy | Independent labelers + owner | Frozen independent holdout, agreed sampling/calibration, confidence-bound gates; no relaxed release criterion |
| Accessibility | Independent users | Actual screen-reader and external install/removal review |
| DNS and mail hardening | Engineering + owner | DNSSEC/DS validation and staged DMARC alignment/enforcement; neither is claimed complete |
| Recovery | Owner + engineering | Offline custody, retrieval check, clean replacement-host drill; measured scope and timing |
| Name and incorporation | Owner + qualified counsel | Comprehensive clearance, current official status, reviewed final filing facts and articles/bylaws |

## Claude’s legal progress: evidence limits

Tumeryk’s own site confirms commercial use of “AI Trust Score” in AI risk
assessment. Third-party trademark records identify serial 98872636 and report
inconsistent dates/statuses; the official TSDR page did not yield a readable case
status in this check. This is a concrete clearance candidate, not an adjudicated
infringement or a conclusion that AI Trust ID is unavailable. USPTO guidance
requires assessing similarity of the marks and related goods/services; a shared
class alone does not settle that assessment. No incorporation or trademark filing
was submitted by this implementation pass.

The quoted claim of “nine of fourteen legal gaps closed” is Claude’s reported
progress. Its final articles, bylaws and KNOWN-GAPS document were not supplied
in this request and were not found in this checkout. Their cross-references,
volunteer-liability exceptions, consent delivery wording and tax-independence
language are not verified here. The Michigan statute website was unavailable to
the read-only retrieval attempt; no new legal clearance claim is made.

Sources: [Tumeryk’s own product description](https://www.tumeryk.com/aitrustscore-report),
[USPTO likelihood of confusion](https://www.uspto.gov/trademarks/search/likelihood-confusion),
[official case lookup](https://tsdr.uspto.gov/#caseNumber=98872636&caseSearchType=US_APPLICATION&caseType=DEFAULT).

Evidence: `runs/2026-10-08-site-public-domain-verification.json`,
`runs/2026-10-08-site-domain-association.json`,
`runs/2026-10-08-site-live-result.json`,
`runs/2026-10-08-public-site-publication-audit.json`,
`runs/2026-10-08-primary-email-receipt.json`.

## Deployment and reversal

Use Node 22 or newer. Build with `npm --prefix site run build`; then
`npm --prefix site run deploy`. The deploy script uploads `site/dist` only,
identifies main as the production branch and acknowledges the dirty checkout.
Before any later publication, review the asset manifest and execute the public
verification against the owned domain. Source control publication is separate.

Both website CNAMEs point to `aitrust-id.pages.dev`, proxied, Auto TTL. The
registrar parking page is disabled. Mail and private notification DNS records
were preserved. Restore a reviewed prior Pages deployment through deployment
history for a content rollback; to withdraw the catalogue, remove its website
aliases through the recoverable dashboard workflow and re-enable registrar
parking. Do not change MX, DKIM, SPF, Apple verification or notify records.
