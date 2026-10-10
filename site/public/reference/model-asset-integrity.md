# Model asset integrity

Architecture: after the hash-locked English model wheel installs, the image build
seals every installed model file into a sorted SHA-256 manifest. Startup verifies
the complete file set and bytes against that manifest before importing the model
package or loading its weights. A missing, extra or changed asset stops startup;
the gateway must consequently refuse evaluation rather than bypass redaction.
The existing redactor health response exposes only model/version/manifest identity
and asset count. It exposes no source document or model file contents.

The manifest and its digest are held in the trusted, read-only image. This detects
changed assets relative to that image; it is not secure boot, a signed release,
accuracy validation or protection from an administrator replacing both the image
and its trusted manifest. Dependency hashes establish the build inputs. The
model-file manifest establishes the selected installed assets before load.

Risks and bounds: verification adds startup disk reads, capped at 256 MiB and
10,000 assets. Symlinks, special files, malformed manifests and unsupported model
versions fail. Startup never downloads weights or rewrites/reseals its manifest.
Bytecode files installed by the model wheel are included; runtime bytecode
creation is disabled. Missing trust material requires rebuilding the image.

Acceptance includes positive startup, corrupt/missing/extra asset rejection,
symlink and malformed-manifest rejection, real image verification and a real
tampered model mount that cannot start. Container checks remain engineering
evidence; PII recognition coverage and independent security review remain separate.

For an already-built local image, run `python3 scripts/verify-model-image.py
--engine podman --image localhost/aitrust-staging_anonymizer:latest
--output eval/model-integrity-report.json`. It never pulls an image, binds a
public port or changes a running service. The Docker engine option requires an
already-running owner-selected engine. Run it only on your development host.
