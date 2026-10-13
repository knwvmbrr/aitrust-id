# Try the Firefox developer preview

This adds a second browser build of the existing ChatGPT checker. The Chrome
extension keeps working independently. PS remains a research preview; this does
not release a validated tag. Firefox's live ChatGPT workflow and stable store
installation still need acceptance. The executed browser test used Firefox
153.4.0 on Linux with a synthetic assistant page and local service.

1. Download this repository. Run `python3 scripts/build-firefox-extension.py`.
   The package appears at `output/firefox/aitrust-id-preview.zip`. Building it
   needs no account, package installation or network. An existing different file
   is preserved; choose another destination with `--output` after a source update.
2. In Firefox, open `about:debugging`, choose **This Firefox**, then **Load
   Temporary Add-on** and select that ZIP file. This developer installation
   disappears when Firefox exits. It is not a signed store release.
3. Open the extension's settings. Save your existing local gateway token and
   choose its public-key JSON file. Confirm the key fingerprint with your
   gateway operator. Saving either one does not enable checks.
4. Choose **Enable checks on ChatGPT**. If Firefox asks for site permission,
   review and allow the request only if you want this route. Declining keeps
   checks paused. The browser grant covers ChatGPT and HTTP ports on
   `127.0.0.1`; the request code connects only to your authenticated local
   service at `127.0.0.1:8787`. It refuses redirects and untrusted result keys.
5. On a supported completed assistant response, the small tag sits below the
   text. Open it for a brief explanation. A missing service or bad signature
   gives an unavailable result, not a PS finding. Your prompts are not captured.
6. Uncheck **Enable checks** to pause. **Reset local settings** removes consent,
   token and selected public key from this profile. Remove the add-on in
   `about:debugging` to end this temporary route. Your conversation and
   user-owned exports remain yours to protect or delete.

Source checks: `python3 -m pytest tests/test_firefox_package.py
 tests/test_firefox_driver_protocol.py -q` and `node --test
 tests/firefox-permissions.cjs`. Run the commands on one line each.
The [actual Linux integration receipt](../runs/2026-10-13-firefox-linux-integration.json)
records temporary installation, paused defaults, assistant-only capture,
authenticated compact tags, refusal of unsigned/altered responses, pause/reset,
uninstall and unchanged source. It does not claim a real vendor test, phone,
human review, store signature or independent accuracy.

Developers can execute `python3 scripts/verify-firefox-extension.py --firefox
/path/to/firefox` with Python 3.12+, OpenSSL and Firefox installed. Use an isolated
Linux environment: the test owns a private profile, generated fixture certificates,
a local TLS proxy and a synthetic service on port 8787. An occupied port refuses
startup; it never stops your real service. The Mac headless startup attempt was
unsuccessful, so Mac support is not inferred from the Linux pass. The isolated
Linux execution disabled networking, dropped capabilities and used a read-only
root; TLS verification stayed enabled. No user browser profile or real credential
was used.
