# Optional notifications

Owner direction, November 10, 2026: preserve future push notifications for
business updates and communication. This is planned delivery enhancement
**ENH-PUSH**, associated with native delivery N-013, community F-136 and support
F-163. No notification service, device registration, permission prompt or Apple
push credential has been created. It is not a prerequisite for the current
offline checker or an independently functioning tag.

## Job and outcome

Let a person choose useful updates without continuously watching the app. Offer
separate choices for product/business announcements, subscribed public community
replies and an explicitly selected organization's operational updates. Announcements
are not automatically enabled when someone asks for a reply or security alert.
Notification delivery is optional; the underlying public message or business
workflow remains independently accessible if push is unavailable.

## Data and control boundary

- Ask in context, after the person chooses a category. Respect denied permission;
  provide pause, category changes and complete unsubscribe/removal. Do not use
  provisional authorization as a substitute for that explicit product choice.
- Checking remains account-free and offline. Do not require registration, push
  permission, membership or an organization role to use personal checks.
- Keep lock-screen payloads generic. Do not include selected text, tag excerpts,
  hashes, case details, private organization names or personal information.
- Treat device tokens, topic subscriptions and delivery logs as private data.
  Restrict publisher roles, validate destinations, protect registration changes,
  and set bounded retention and backup expiry before collecting any tokens.
- Business enrollment cannot silently opt an author into company announcements,
  text capture, receipts, training or evaluation. Employer settings cannot weaken
  personal consent or tag validation.
- A notification is a pointer to an existing authorized workflow, not evidence
  for a tag verdict. Opening it must recheck access and reject unsafe/deleted
  destinations. No new endpoint or deep-link namespace is assigned by this plan.
- Notification outages, expiry, duplicates or permission withdrawal cannot
  disable checks, the app, community reading or unrelated tags.

## Platform and operating limits

Keep application and server code inspectable and exportable. iOS remote push
would use Apple's platform delivery service; open-source app/server code does
not make that service self-hosted or independent of Apple. Document provider
handling and actual platform requirements before activation. Evaluate web and
Android delivery separately; do not promise identical support without tests.
Add the required Apple capability and owner-created provider credential only
when the implemented feature is ready for its security and privacy review.
Today's distribution signing remains separate.

## Acceptance before activation

Exercise allow/deny, per-category consent, unsubscribe, token rotation, lost or
replaced devices, wrong-user/organization delivery refusal, rate limits, retries,
deduplication, expiry and provider outage. Inspect payloads and logs for private
markers. Validate access again on opening a notification and verify that expired
links fail safely. Test real iPhone and Android behavior, accessibility and
notification settings with people. Publish the data inventory, retention,
deletion/recovery tests and operator instructions before accepting real tokens.

These are future acceptance conditions, not completed checks or a response-time
promise. The existing 202 requirement records and their completion counts stay
unchanged; this enhancement has its own open entry in the completion ledger.

Apple's current [notification permission guidance](https://developer.apple.com/documentation/usernotifications/asking-permission-to-use-notifications)
was read on November 10, 2026. It supports contextual permission requests and
checking current user settings. The stronger category-consent and privacy
conditions above are our proposed product contract, not claims of Apple certification.
