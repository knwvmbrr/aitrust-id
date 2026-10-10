# Optional independent timestamp architecture

F-124 is a retained research requirement. This increment implements a bounded
RFC 3161 development component; it does not adopt RFC-0002, issue an authorship
tag, operate a time authority, or change the existing receipt format.

The owner chooses a local artifact (including a signed receipt). An explicit
`--send-digest` operation sends only its SHA-256 digest and a fresh OpenSSL nonce
to the documented independent FreeTSA HTTPS service. The authority can observe
the requester IP and correlate the digest; hashes of predictable content are not
anonymous. No automatic timestamping, retry, raw input upload or new AI Trust ID
endpoint is introduced. Existing personal checks operate without this service.

Verification runs offline against separately obtained, hash-pinned public root
and TSA certificates. OpenSSL validates the RFC request/response nonce and imprint,
then the original artifact digest separately. A CMS check with `-nointern` pins
the actual signing certificate rather than trusting a co-delivered signer. The
result reports the authority's signed time, artifact binding, unchecked revocation,
unknown authorship and no certified validity independently. Missing prerequisites,
changed content, substituted trust, invalid signatures and malformed/oversized
inputs refuse. No response or archive executes code.

Trust risks: authority/CA compromise, requester clock and IP exposure, digest
correlation, certificate rotation and future revocation. The provider's current
CRL interval is too broad to call status fresh; this component therefore cannot
issue a VALID verdict. Revocation/freshness and long-term preservation are still
F-125/F-126. No automatic trust update is permitted. Scope acceptance remains
open where composition interpretation or RFC adoption is unresolved.

Checks will include a real independently issued token for synthetic public
content, offline replay, altered artifact/query/token and wrong trust. Synthetic
local authority fixtures test parsing/failure controls only, not independence.
Published results must distinguish actual authority execution from mocks.

Sources: [RFC 3161](https://www.rfc-editor.org/rfc/rfc3161.html),
[FreeTSA endpoint and current certificate hashes](https://www.freetsa.org/index_en.php),
[OpenSSL timestamp verification](https://docs.openssl.org/3.6/man1/openssl-ts/).
Author: Codex. No production key or private user example is needed.
