# Additional browser route — architecture and acceptance

Codex, 2026-10-13. F-156 retains its full additional-browser/site integration job.
Create a separate Firefox MV3 package from the existing ChatGPT adapter,
compact UI, consent settings and authenticated loopback transport. Chrome source
and permissions stay unchanged. Firefox uses a non-persistent background script;
the package loads the two shared scripts explicitly instead of Chrome's module
service worker. Require an exact recognized import prefix, an explicit file
allowlist, regular source files, deterministic archive members and hashes.

Default installation remains paused. Only assistant responses on chatgpt.com may
reach the owner's authenticated loopback gateway after enabling checks. Do not add
remote collection, broader origins, telemetry, new endpoints or new tag codes.
Any unavailable browser/permission/service affects this route alone.

Execute package reproducibility, missing/changed source, path/link/import rejection,
actual temporary Firefox installation, settings/consent, authenticated synthetic
findings, paused/revoked consent, unsupported sender, credential reset and uninstall.
Use an owned isolated browser profile and a synthetic vendor fixture; identify it
as synthetic. Never bypass TLS or copy the owner's browser sessions or secrets.
No store submission, signature or persistent end-user installation is implied.

Risks: Firefox and Chrome background lifecycles differ; Firefox may require host
permission grants. Temporary extensions are removed on browser exit and are not
an approachable stable distribution channel. Synthetic vendor success cannot
establish current live vendor compatibility, human acceptance or independent PS
accuracy. F-156 can close only when its full supported-platform installation,
use/removal and compatibility acceptance is evidenced; do not turn a package build
into 100%. The remaining site-adapter job is retained, not dropped.

References: [Mozilla MV3 migration](https://extensionworkshop.com/documentation/develop/manifest-v3-migration-guide/),
[Firefox background entries](https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/manifest.json/background),
[temporary installations](https://firefox-source-docs.mozilla.org/devtools-user/about_colon_debugging/index.html).

## Executed permission correction

Mozilla documents that Firefox does not support a port in a match pattern. The
first actual package's loopback permission was absent, despite successful install.
Firefox's explicit permission is therefore `http://127.0.0.1/*`; it covers ports
at the browser-grant level. The unchanged request implementation still fixes the
only destination to `http://127.0.0.1:8787/v1/evaluate`, refuses redirects, requires
local consent/token and a separately selected signing key, and ignores
assertion-supplied destinations. This distinction must be visible in installation
instructions; do not claim the Firefox browser grant itself restricts ports.
The ChatGPT origin grant is explicit; no additional vendor is introduced.
[Mozilla match-pattern contract](https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/Match_patterns).

## Full service acceptance

Extend the existing owned Linux fixture to start the exact currently observed
staging gateway, redactor and evaluator source/dependency sets in separate Python
import roots. Copy only their image application/package trees into an owned test
image, never container environment/configuration or user data. Verify every copied
application source against the checkout before starting it. Generate a new test
token/signing key; no real credential is read. Use internal loopback ports only,
with the same 8787 browser destination supplied by a fixture proxy to the real
gateway on another private loopback port. Forward request nonce/body unchanged;
negative cases strip a signature or alter signed bytes after the real response.
Keep the network-disabled, read-only, non-root, capability-dropped boundary and
record the exact application sources and service mode in the resulting receipt.
Services must pass readiness before the browser runs and stop before test cleanup.
This is real service/browser integration with synthetic text, not a live vendor,
independent accuracy study or accepted browser-store release.

The isolated host rejects peer-process signals even between the fixture's owned
processes. Use an inherited, private stdin pipe for each test service: a one-byte
request or EOF sets Uvicorn's own `should_exit` flag. This adds no endpoint or
privilege and leaves application source unchanged. A process that does not exit
within eight seconds fails cleanup; container removal remains a separate external
witness. Browser shutdown continues through its existing driver IPC session.
