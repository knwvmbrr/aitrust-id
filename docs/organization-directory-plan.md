# Organization directory integration — architecture before implementation

F-162 binds current organization identity and roles to private audit operations.
The supported software profile is an operator-owned command-line broker, a
self-hosted Keycloak OpenID Connect provider and the existing dedicated PostgreSQL
18 audit store. It adds no public web listener or production collection. An
operator can call the broker over an existing controlled transport; an arbitrary
client must never receive its private configuration or database credentials.
Production transport deployment and managed-service activation stay separate.

Use the documented OAuth device grant so the application never receives a user's
password. Tokens and pending device codes are private owner-only files outside
Git. The operator pins issuer, realm, confidential client and directory client ID.
Validate provider discovery against that issuer; deny redirects, environment
proxies and cross-origin endpoints. Require verified HTTPS, with an explicit
127.0.0.1-only development mode for the disposable integration lab. Fail closed
on unavailable identity or directory checks; no fallback to unchecked JWT claims.

Every private operation freshly introspects the token and queries current enabled
user and client-role membership through a read-only provider service identity.
Bind subject, tenant, issuer, audience, client, expiry and issue time. Do not use
roles copied into an older token after a directory role has been removed. Map only
explicit local subject bindings to existing least-privilege database profiles.
The database's tenant and capability checks remain effective behind the broker.
Configuration, viewing, feedback-review and export permissions are separate.
Organization review is feedback, never independent verification or an IV tag.

A private SQLite access-control journal stores local logout/revocation, an owner
recovery fence and bounded operational events. Do not store tokens, directory
names, answers, record text or arbitrary exception messages there. Hash identities
with an installation-local random salt; these pseudonyms are still linkable
metadata. Expire events under a separately explicit retention choice. Operators
remain responsible for backup/export retention; no automatic research submission.

Logout blocks the local token even if provider revocation is unavailable. Owner
recovery disables a compromised administrator, fences pre-recovery tokens and
requires a separately pre-enrolled replacement with a current configure role.
Directory configure permission cannot undo an owner compromise fence. Each action
checks the fence again before opening the database; failures cannot alter public
tag evidence or stop the independent personal checker. The OS/database/provider
administrators remain trusted; this is not protection against their compromise.

Before any completion, execute real device login and directory changes against a
pinned disposable Keycloak and real PostgreSQL, using only invented identities and
metadata. Exercise all permissions, current role removal, user disable, wrong
issuer/client/tenant, local/provider logout, compromised-admin recovery, unavailable
provider, private-file boundaries and bounded error/log behavior. Do not substitute
a mocked token response for the provider integration. Preserve all original scope
acceptance and the separate human, institutional and detector-validation gates.

The integration lab must also exercise real HTTPS using a generated private test
CA and explicit operator-selected trust file. A wrong CA and the untrusted default
store must refuse that server. Browser automation pins the disposable server's
certificate public key; it does not install a global CA or bypass deployed TLS.
