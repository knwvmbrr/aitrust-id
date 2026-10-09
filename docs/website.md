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
layout. There are no remote fonts, tracking scripts, accounts, browser storage, or
intake endpoints. A static host serves the built document, scripts and references.
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

Receiving reports and messages needs verified destinations. Public bug/contribution
intake, moderated discussions, and private security reports have different disclosure
needs. Do not publish an unverified inbox or route private security reports to public
issues. User preference for destinations is pending. This is a real integration gap,
not a reason to pretend an exported draft was submitted.

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

The public catalogue is now live on aitrustid.com and www.aitrustid.com; see
docs/live-launch-status.md and dated production checks. Existing limited Pages
authentication works. The original pre-deployment guidance below is historical: Reauthenticate with `site/node_modules/.bin/wrangler login`, verify the
account using `wrangler whoami`, and inspect its Pages projects before publishing.
The declared `npm run deploy:site` targets `aitrust-id`; this project is not yet
confirmed. If absent, create it only in the confirmed target account. Before attaching
the custom domain, inspect its current Pages/DNS configuration to avoid replacing an
unrelated deployment. Verify HTTPS, references, security headers and report disclosures
at the deployed URL. Recheck the custom domain after DNS propagation.

Do not claim the domain is live until a request to it returns this verified build.
No hosting deployment, domain change, report connection or registration filing has
been performed in this increment. Account and destination access are the current
external dependencies. Roll back by redeploying a verified prior Pages build.
