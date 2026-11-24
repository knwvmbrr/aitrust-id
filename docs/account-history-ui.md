# Account and private history — working review service

Implemented November 24, 2026 by Codex /root (browser and access integration)
and /root/seo (account API/storage), with separate source reviews. This is a
working isolated development service, not public signup or a paid subscription.
The account API architecture and fixed routes are in
[account-history-delivery.md](account-history-delivery.md).

## Run the isolated review

From the repository root, activate a Python environment already provisioned with
this repository's hashed `services/gateway/requirements.lock` dependencies.
These commands do not install packages, run Docker or activate production. Use a
new private directory outside Git; initialization refuses an existing store.

```sh
AITRUST_REVIEW_DIR="$HOME/.local/share/aitrust-id-account-review"
install -d -m 700 "$AITRUST_REVIEW_DIR"
python -B scripts/history-entitlements.py init --directory "$AITRUST_REVIEW_DIR/entitlements"
python -B -m services.accounts --store "$AITRUST_REVIEW_DIR/accounts" --init --origin http://127.0.0.1:8791 --port 8791 --dev-http --entitlements "$AITRUST_REVIEW_DIR/entitlements" --asset-directory "$PWD/site/account"
```

Open `http://127.0.0.1:8791/account/`. On restart, omit `--init`; preserve the
existing store and ledger. Stop the foreground service with Control-C. The
explicit `--dev-http` exception is limited to loopback HTTP. Never expose this
review command through a public proxy. The access CLI's `grant --account`,
`--event` and `--until` flags are documented in its `--help`: the operator uses
the authenticated session's account UUID, a fresh random UUIDv4 event, and a
Unix expiry within 31 days. No payment or client-supplied paid flag is involved.
Run `npm run verify:account-ui` for the dependency-free private-view regression;
CI also runs the account API/store/access lifecycle with its locked Python stack.

## Use it

Start the account service with its documented operator-only store, entitlement
ledger and trusted `site/account` asset directory, then visit `/account/` on that
service. Its three assets are served with the account service's strict headers;
they are not published by the catalogue build. Use a generated review identity,
not production credentials. The service has no password-recovery channel yet.

1. Create an account with a username and a passphrase. History starts off.
2. The operator may issue a bounded private access grant using the separate
   history-entitlements CLI. This grants access; it does not charge a customer.
3. Refresh, choose to save summaries, and save that preference.
4. Run a free PS check and choose **Download summary**. Select that JSON file
   here, review its short description, then choose **Save summary**.
5. Revisit, export, delete a summary, delete all history, or remove the account.
   Export and deletion remain available when access expires or is revoked.

The file stays on the device until the explicit save. Only the allowlisted tag,
result, public method identity, random event ID and import time are submitted.
Original viewing time and location are unknown. Imported summaries are client
claims, not verified assertions, independent accuracy evidence or actual
extension/native display bindings. No answer text, screenshots, subject hashes
or browsing URLs are saved. Signup/history opt-in never grants training consent.
The reviewed store retains at most 1,000 summaries/5 MB per account for 30 days.
Logical deletion does not promise erasure from backup media.

## Verified behavior and limits

The actual loopback service, real private entitlement engine and real browser UI
complete signup, opt-in, PS-summary import, revisit, sign-out/sign-in, revoked
access export/deletion and account removal. Chromium checks at widths 320, 390,
428, 768 and 1280 observe no horizontal overflow; WebKit completes sign-in and
history management. Light/dark persistence and the selected automated WCAG rules
pass. These are emulated browser checks, not an iPhone or human VoiceOver result.

An earlier WebKit attempt was refused because `mode: same-origin` combined with
`no-referrer` serialized an unsafe request's Origin as `null`. The corrected
fixed-relative-URL request uses `mode: cors`, retaining same-origin credentials,
no-referrer, redirect refusal, strict server Origin/CSRF checks and self-only CSP.
The actual corrected WebKit request carries the exact service Origin and passes.
The strict server never accepts `null` as an Origin.

A different source reviewer also reproduced a cross-account display failure: a
new session with an unavailable history request could retain old rendered rows.
The browser now clears private rows, pagination, import state and principal
labels before starting each session refresh. Original successful browser results
remain attributed to their earlier source. Four focused regressions and a fresh
complete Chromium/WebKit workflow pass on the corrected source; automated reflow,
network and axe observations are from Chromium, with sign-in and history
management additionally exercised in WebKit.

The trusted entitlement clock is selected under the owned ledger lock; the
account clock is selected after its database writer transaction starts. This
prevents earlier request timestamps from looking like clock rollback after a
newer transaction. Actual clock rollback still refuses; neither clock clamps.

Before public activation: qualify self-hosted PostgreSQL, HTTPS and proxy trust,
service/operator privilege separation, abuse controls, operational retention and
backup/recovery/deletion, account recovery, production deployment and applicable
policies. Real subscription checkout, provider verification, prices and commercial
terms are separate. The free checker has no account-service import or dependency.

## Result filtering increment — architecture before implementation

November 24, 2026. Keep the existing GET `/v1/account/history` route; add only an
optional `state` drawn from the existing four result states. The store validates
all retained payloads before filtering, then paginates the selected owner's
matching records. Cursors from another filter or owner refuse. `total_entries`
keeps its previous meaning (all retained owner records); `matching_entries`
reports this filter's count. The separate export route always exports all
retained owner records and never depends on access/payment assessment.

The browser offers a labeled native select, a readable count, and a clear empty
filter message. Session changes reset the filter with all other private state.
Changing filters fetches the first page rather than mixing old cursor/results.
A failed filter request clears the rendered list and shows unavailable with a
retry action; it does not show stale records as new results. The stored public
method can be expanded using native details, with explicit imported-summary
limits and no invented input or original viewing time. No raw text, new subject
fingerprint, training consent, payment authority or public activation is added.

Verify actual mixed-state pagination, cursor/owner refusal and inactive export;
then run the actual page with the existing private service and focused browser
observations. Database production deployment remains separately qualified.

A read started in a different signed-in tab must not silently display the new
account under the old tab's identity. Before editing the guard: the browser will
send its known session CSRF binding on account reads as well as writes. The
server will validate any supplied binding on GET too. Legacy authenticated GET
clients without this optional header keep their existing contract; the web UI
always supplies it after bootstrap. A stale cookie/header pair refuses before
history/export is read. Session bootstrap remains the explicit fresh-identity
operation. Verify with two real authenticated clients whose cookies and binding
are deliberately crossed; no new credential, route or client identity claim.
