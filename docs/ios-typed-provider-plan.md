# Supported typed text delivery

Replace the Share extension's deprecated `loadItem` call with Apple's supported
`loadObject(ofClass:completionHandler:)` for `NSString`, only if actual native
Share operation succeeds. The iOS 27.2 Foundation SDK names that replacement;
the official documentation confirms availability since iOS 11. This is a
compatibility repair, not a tag release or full N-013 completion.

Protect the selection boundary: one item/provider, supported text type, explicit
Check, no URL/file opening, existing 20,000-scalar/80,000-byte bounds, late-delivery
refusal, timeout and background/cancel clearing. Request only the text class;
never broaden decoding to arbitrary archives or fall back to an external app.
Provider allocation remains outside our memory bound.

The earlier modern-object attempt did not demonstrate a working handoff. Treat
that as a regression risk, not proof that changing one API fixes the issue. First
exercise the exact typed loader with Foundation's actual string provider, then
run all five existing UI workflows on an owned simulator and inspect the unsigned
registered-ID device archive. Preserve a failing attempt; revert the product
change if the real Share source cannot deliver through this supported API.

No signing identity, certificate, profile, device-security change or Apple upload
is created by these checks. Keep the physical-phone, VoiceOver, real source-app,
independent accuracy and distribution acceptance open. Bind new software evidence
to source identities before updating current evidence references, scope and state.

## Observed result — November 10

The actual Foundation string provider passed, and the app compiled with the
supported loader. The actual native run passed standalone checking, edit
invalidation and background clearing, but failed both Share workflows: the
selection never arrived and the UI reported that the provider could not supply
text. The underlying provider error remains undiagnosed. The attempted runtime
and test changes were reverted; the existing working compatibility path is
unchanged. Private patch, full result bundle and logs are retained, with the
bounded [rejected-attempt record](../runs/2026-11-10-native-typed-provider-rejected.json).
No supported-loader repair, future SDK compatibility or full closure is claimed.
