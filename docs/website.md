# Tag catalogue website

The static React site in `site/` implements the requested title, Person/Enterprise switch,
code-only tag grid, tag-detail dialogs, and a footer for reporting, assistance, townhall, teamwork,
company information, scope and licensing. It preserves the 198-record scope baseline.
No existing evaluator, extension, or protocol code was renamed to implement the website.

## Architecture and boundaries

`src/catalog.js` defines 14 personal records and six proposed organization offerings.
They are read by the UI, downloadable detail records, and generated no-script reference.
Organization display names do not become adopted protocol verdict codes. The UC/SC/BT
proposals remain proposals. Personal capabilities remain free; organization offerings
show proposed paid access without prices, checkout, or unimplemented purchase flows.

Each modal states the job, outcome, bounded claim, method, inputs/outputs, supported
scope, limitations, evidence, access, privacy, dependencies, failure behavior, outcome
owner and release requirements. Other scope capabilities remain visible in the footer.
Source references and JSON detail export provide further inspection; no catalogue badge
is evidence of an accurate or certified detector.

`src/main.jsx` uses Radix dialogs and tabs for focus containment, nested dialog behavior,
keyboard navigation and focus restoration. `src/styles.css` provides the responsive
layout and compact tag-shaped buttons. A native SVG logo is used in the header and
favicon; no raster generation service or remote font is involved. Light, Dark and
System appearance is supported. The only persistent browser storage is the selected
appearance preference; blocked storage does not break the controls. There are no
tracking scripts, accounts or intake endpoints. A static host serves the built
document, scripts and references.
`public/_headers` defines intended Cloudflare security headers; their production
application must be checked after deployment. Local Python static hosting does not apply them.

`src/model-tools.js` optionally exposes two read-only public catalogue tools when the
browser provides `document.modelContext.registerTool`. Unsupported browsers continue
normally. A mock registry exercised validation and lifecycle cleanup. The QA browser
has no native support, so native integration is unverified. Tools cannot evaluate text,
issue tags, read draft content, submit reports, or change catalogue state.

## Reporting and teamwork

Report, Assist and Townhall forms create validated JSON drafts with a selected tag,
report/contribution category and required description. A report can include an optional
tag record identifier. Downloading or copying is a local user action. Drafts explicitly
say `draft_not_submitted`; no server has received them. Reloading clears page memory.
There is no claim of persistence, delivery, moderation, response time or a functioning
shared team workspace. Clipboard denial offers download as the fallback.

GitHub issues/discussions and private vulnerability reporting are now enabled as
external, manually submitted development destinations. Site drafts are never
pre-filled into an external URL or sent automatically. This supersedes the earlier
destination-pending description below.

Public bug/contribution intake, moderated discussions and private security reports
have different disclosure needs. Private security reports must stay out of public
issues. A self-hosted live community and private research intake are still separate
application gates; exported drafts are not submissions.

## Privacy of the public build

`site/scripts/prepare.mjs` copies an explicit reference allowlist and projects scope
records to public fields. It does not publish the repository, history, attachments,
private coordination, local environment files or tokens. Tag/source/feature identifiers
and reference existence are validated at build time. A targeted scan of the completed
build found no selected private-path, portfolio, or secret-marker matches. This is a
bounded scan of the deployment artifact, not blanket historical privacy clearance.

## Verified locally on 2026-10-08

- Production build completed.
- All 20 tag/organization dialogs and eight footer dialogs executed.
- Person defaults to 14 records; Enterprise shows six organization offerings.
- Keyboard containment and Escape focus restoration, including nested reports.
- Required-description validation and correct tag binding in exported report JSON.
- Literal HTML in draft descriptions does not execute.
- Deep links, malformed fragments, 320-pixel width and 200% text enlargement.
- A native no-JavaScript reference for all 20 records and 198-record public scope file.
- Zero automated axe WCAG A/AA violations in checked states and no unexpected outbound requests.
- npm audit reported zero known advisories for the locked site dependency tree.

Evidence: `runs/2026-10-08-site-verification.json` and
`runs/2026-10-08-site-build.json`. A human screen-reader review remains outstanding.
Automated UI checks do not validate tag accuracy. Statistical release gates still fail
on the development regression corpus, and the site says so.

## Build, verify and publish

Use Node.js 22 or newer; Wrangler requires it. Install with `npm ci` in the root and
`npm ci --prefix site`. `npm run build:site` writes `site/dist`.
`npm run dev:site` serves the existing preview at `http://127.0.0.1:5173/`.

For production-artifact QA, start:

```sh
python3 -m http.server 5174 --bind 127.0.0.1 --directory site/dist
```

In another terminal, run `npm run verify:site`. The site CI job uses this workflow and
fails on errors. It does not override the separate statistical evaluation gates.

The public catalogue is live on aitrustid.com and www.aitrustid.com. The existing
limited Pages-write grant deploys `site/dist` through `npm run deploy:site`, targeting
the confirmed `aitrust-id` project. No broader OAuth grant is needed. Review the
publication asset manifest and execute the external verification after each deploy.
The production checks verify CSP, frame denial, nosniff, no-transform and interaction.
Roll back through the reviewed prior Pages deployment; preserve all mail and notify DNS.

## Crawlable content and accurate metadata

The architecture retains React for the catalogue and Radix dialogs. Crawlable content
is generated from the same catalogue without moving tag details or changing detector
contracts. `scripts/seo.mjs` supplies canonical URLs, titles, descriptions, Open Graph,
Twitter and JSON-LD. `scripts/prepare.mjs` builds the no-script home reference,
robots.txt, sitemap.xml and the reproducible 1200×630 social preview using the declared
Sharp dependency. `scripts/render-reference.mjs` runs after Vite and produces the tag
index and all 20 standalone tag/organization pages, sharing the fingerprinted CSS.

All references contain their actual status, limits and release requirements. Proposed
enterprise offerings are not advertised as shipped products. Structured data uses
WebSite, CollectionPage/WebPage and DefinedTerm; no invented ratings, certifications,
prices or incorporated-company status. Invalid tag paths return a real 404 with noindex.
There are 22 canonical sitemap URLs: home, tag index and 20 detail pages.

`public/theme.js` is an early same-origin script compatible with the existing CSP.
It validates the saved appearance enum and synchronizes system and cross-tab changes.
Without JavaScript the system color scheme and full static references remain usable.
Native switch controls are hidden on static pages until their behavior is initialized.

Production evidence: `runs/2026-10-08-site-redesign-public.json`,
`runs/2026-10-08-site-redesign-result.json` and the publication asset audit. Tests
cover all modals, both themes, system changes, blocked storage, mobile/reflow, forced
colors, keyboard behavior, static no-script content, unique metadata, canonical URLs,
JSON-LD parsing and known types, social image dimensions, security headers and zero
unexpected outbound requests. Automated axe reports zero violations in checked states.
Human screen-reader review and Google Rich Results validation remain unverified.

This makes the site crawlable; it does not establish actual Google indexing or rank.
Search Console ownership and sitemap submission remain unverified. After verifying
`aitrustid.com`, submit `https://aitrustid.com/sitemap.xml`, inspect the home and PS
URLs, and monitor indexing reports. See [Google's Search Console guidance](https://developers.google.com/search/docs/monitor-debug/search-console-start)
and [recrawl guidance](https://developers.google.com/search/docs/crawling-indexing/ask-google-to-recrawl).
The user's pasted search results describe other services and are not indexing evidence
for this owned domain. No third-party biometric or certification claims are reused.

## Friendly tag detail presentation

The catalogue keeps code-only tiles. Each detail dialog opens at its natural content
height, bounded by the viewport. The initial view shows a plain-language job, a
specific limitation and the validation status. Three native keyboard-operable
`details` sections contain the method, complete testing/evidence information and
privacy/access/features. All catalogue fields and scope features remain available;
the JSON export retains the full record. Evidence reproducibility and signature
validity are explicitly distinguished from finding correctness.

`src/presentation.js` supplies concise introductions for all 20 records. The build
fails if a record lacks its introduction. Static reference pages use the same brief
and keep the complete catalogue details crawlable.

The native checkbox has `role="switch"` and accessible name “Dark mode.” Space toggles
it; Auto follows the device theme. `public/theme.js` owns a single preference store,
synchronizes catalogue and static controls, and notifies React subscribers and other
same-origin tabs. Storage failure leaves the control usable. There is no motion,
remote storage, extra dependency or analytics. Evidence for this revision:
`runs/2026-10-08-site-friendly-local.json` and, after deployment,
`runs/2026-10-08-site-friendly-public.json`.


## Per-tag use and typography

`site/src/usage.js` supplies the modal, static reference and no-JS use section.
PS and PII share one local installation. Four setup steps have individually
copyable commands, explicit Linux/macOS prerequisites, an optional unpacked
Chrome path, result meanings and a stop command. The remaining 18 records state
unavailability instead of providing a misleading install action. Detail exports
also include the use contract.

Nunito Sans is served from this site in five WOFF2 subsets (107,432 bytes total).
The browser loads only applicable subsets. Its SIL OFL license and pinned asset
hashes are in `site/public/fonts/`; no Google font request is made by the page.
Code snippets remain monospaced; the visible tag letters and prose use Nunito Sans.
