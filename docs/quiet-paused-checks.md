# Paused means no check

When extension checks are paused, AI Trust ID leaves the page quiet. There is
no tag, unsupported-result badge or retained screen-reader announcement. Your
answer has not been evaluated. Pausing does not remove the conversation from
ChatGPT or revoke a separately issued local-service credential.

Use the existing extension settings to enable or pause checks. In Chrome, open
Extensions, choose AITrust-ID, then Extension options. Saving a token or a public
key does not enable checks. Enabling assistant-response checks is a separate
choice, restricted to ChatGPT and your authenticated local service.

The actual unpacked-extension check exercises a fresh paused installation,
explicit enablement, authenticated results, pause during an in-flight request,
late-result refusal, reset and reload. Pausing removes the page controls and
live announcement; resuming requires a fresh evaluation. The new assertion also
fails on the previous implementation, demonstrating the observed defect.

The existing six evaluation result states, tag methods, thresholds, permissions
and destinations are unchanged. Synthetic browser controls are not live vendor
compatibility, human screen-reader acceptance or independent tag validation.
Physical phones and the existing full F-035 acceptance remain open.

Evidence: [current browser controls](../runs/2026-10-15-quiet-paused-privacy.json)
and [previous-behavior regression](../runs/2026-10-15-quiet-paused-regression.json).
