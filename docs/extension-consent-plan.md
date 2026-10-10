# Consent and capture controls — ChatGPT only

New and upgraded installations start paused unless the local browser setting
`checks_enabled` is explicitly true. Saving a token does not opt someone into
capture. Settings name the one supported site, assistant-response boundary and
authenticated loopback destination. A native checkbox enables or pauses checks.
Reset removes the token and consent from this browser profile; it does not revoke
the server credential or delete the conversation owned by ChatGPT.

Keep the existing permissions and endpoint. Read only the consent flag in the
content script. While paused, do not read assistant response text, mount response
tags or dispatch evaluations. A compact page-level settings prompt explains the
paused state without inventing a wire result state. Settings can be opened only
by an extension message from the supported page. No prompt, keystroke, document,
other-site or background capture is added.

On pause/reset/token change, the service worker cancels active requests and its
generation guard refuses late results. The bridge invalidates pending revisions,
removes its tags and references, and clears pending timers. A storage read failure
fails closed. Resume creates new evaluations; it does not revive old results.
Neither cancellation nor dropping JavaScript references proves physical erasure
or cancels work an upstream already received. The local service has its separate
disconnect/cancellation boundary. User-initiated downloads remain user-owned.

Risks: upgrades will pause the previous installation until the owner opts in;
this is intentional and explained in settings. Storage races must not cause
silent re-enablement, and another tab changing settings must invalidate results.
Tests must use explicit synthetic consent, and must separately demonstrate the
default-off, blocked-storage, pause-during-request, reset and resume paths with
actual extension scripts. Browser/OS administrators can access browser-profile
storage; local storage is not encryption or protection against a compromised OS.
