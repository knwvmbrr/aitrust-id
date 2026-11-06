# Sign in to your organization's private audit records

This optional tool controls who may view, export or leave feedback on your team's
retained tag records. Signing in never makes a finding more accurate. Personal
checking stays free and account-free, including when the directory is unavailable.

**Current status:** implemented locally; actual provider acceptance is in progress.
No identity provider is connected to the public website and no managed SSO service
is offered. The supported operator profile uses self-hosted Keycloak 26.8.2,
OpenID Connect device authorization, Python 3.12+ and the existing PostgreSQL 18
[audit store](organization-audit.md). Other providers and SAML are not claimed.

## What the operator needs

Use an organization-owned Linux host and a dedicated Keycloak realm. Keep database
and provider credentials on that trusted host; never distribute the broker's
configuration to a member's device. The callable broker and command line add no
web listener. Connect an existing controlled operator transport separately before
remote use; this is not a public login endpoint or a deployment service.

The provider needs a confidential `aitrust-broker` client, device authorization
and service accounts enabled, the standard `roles` client scope enabled, direct password grants disabled, and an audience
mapper including that client in access tokens. Its service identity needs the
realm's **view-users** role to inspect current enabled users and effective client
roles. It does not need user/client write permissions. Assign the built-in `kc-admin-api` optional client scope; the broker requests it only for its service identity. Keycloak 26.8 checks the Admin API audience and scope. See the [provider administration guide](https://www.keycloak.org/docs/latest/server_admin/index.html). Use HTTPS with a trusted
certificate. A private CA is an explicit operator choice; verification is never
disabled. The HTTP development option accepts only literal `127.0.0.1`.

Create four client roles and assign them to the people who need each job:

| Client role | Job |
| --- | --- |
| `aitrust-view` | View private retained records |
| `aitrust-export` | Export your team's retained metadata and history |
| `aitrust-review` | Record organization feedback: agree, disagree or uncertain |
| `aitrust-configure` | Locally revoke or restore a pre-enrolled member |

These permissions do not imply each other. Configuration access cannot undo an
owner's compromised-identity fence. Feedback never becomes an IV tag, independent
review status, certification or an authorship receipt. Nobody is required to issue
a receipt to use a personal checker.

## Prepare the private operator configuration

First follow the audit-store guide to create a dedicated tenant and separate
least-privilege database identities. A member with review access also needs the
store's read capability to inspect its tenant-bound header. Database credentials
remain server-only. The provider's immutable subject UUID is explicitly bound to
one existing database profile; directory display names and email are not keys.

Create a mode-0700 directory **outside every Git checkout**. Save the configuration
below as a mode-0600 `broker.json`; replace each placeholder privately. Obtain the
client UUID and immutable user subject UUID from your own provider. Never paste a
real client secret or a session token into chat, a Git issue or the source tree.

```json
{
  "format": "organization-directory/v1",
  "tenant": "YOUR_AUDIT_TENANT_UUID",
  "issuer": "https://YOUR_PROVIDER/realms/YOUR_REALM",
  "realm": "YOUR_REALM",
  "client_id": "aitrust-broker",
  "directory_client_uuid": "YOUR_PROVIDER_CLIENT_UUID",
  "client_secret": "YOUR_PRIVATE_CLIENT_SECRET",
  "bindings": {
    "YOUR_USER_SUBJECT_UUID": {
      "service": "YOUR_DATABASE_SERVICE",
      "service_file": "/PRIVATE_PATH/services.conf",
      "pass_file": null,
      "principal": "your_database_principal"
    }
  },
  "state_file": "/PRIVATE_PATH/access.sqlite",
  "event_days": 7,
  "allow_loopback_http": false,
  "ca_file": null
}
```

Select 1–30 days for operational access events. `ca_file` is null for normal system
trust, or an owner-private PEM trust file. Initialize once; existing state is never
overwritten:

```sh
python3 scripts/organization-directory.py --config /PRIVATE_PATH/broker.json initialize
```

## Sign in without giving this tool your password

Run on the trusted operator host with private output directories:

```sh
python3 scripts/organization-directory.py --config /PRIVATE_PATH/broker.json begin \
  --output /PRIVATE_PATH/sign-in
```

Open the displayed provider address, enter the displayed short-lived code, and
sign in **at your provider**. After approving the device, finish:

```sh
python3 scripts/organization-directory.py --config /PRIVATE_PATH/broker.json finish \
  --pending /PRIVATE_PATH/sign-in/pending.json --output /PRIVATE_PATH/session
```

The session is saved privately. If approval has not finished or expires, the
command returns Unavailable; approve and retry while pending is valid, or begin a
new sign-in with a fresh output directory. Tokens are not printed. The supported
private operation window is at most 15 minutes from token issuance; sign in again
rather than silently extending a session.

## Use a private operation

The server-side `Broker.dispatch()` accepts exactly `tenant`, `operation`, `token`
and `arguments`. Supply the access token through a private request on standard
input to `call --output /PRIVATE_PATH/result`. Never put it on the command line.
An existing operator transport must protect the request and its destination.
`view` and `export` take empty arguments. `review` takes a source-record hash,
`agree` / `disagree` / `uncertain`, and a supported reason. `configure` takes a
pre-enrolled subject UUID and `revoke` / `restore`. Output is saved as a private
`result.json`; it is not sent to this company or a research database.

Each action checks the live token, enabled user, current directory roles, local
revocation and recovery fence, then the actual database principal and tenant.
Removing a provider role applies to the next action even if the older token still
contains that role. Database and provider administrators remain trusted; this is
not protection against an administrator reading their own database directly.

## Sign out and recover

```sh
python3 scripts/organization-directory.py --config /PRIVATE_PATH/broker.json logout \
  --session /PRIVATE_PATH/session/session.json
```

Local access is blocked even when provider revocation is unavailable. The result
states whether provider revocation completed. This does not sign out every browser
at your provider; use its account console for that. Remove private pending/session
and output folders when you no longer need them, including separately saved copies.

Before an incident, separately enroll a replacement operator with configure
permission. On the trusted host, the owner can use its valid session to recover:

```sh
python3 scripts/organization-directory.py --config /PRIVATE_PATH/broker.json recover \
  --compromised-subject COMPROMISED_SUBJECT_UUID \
  --replacement-session /PRIVATE_PATH/replacement/session.json
```

This blocks the compromised subject and fences every older token, including the
replacement's. Sign in again after the recovery second has passed. Ordinary
configure permission cannot remove the compromise fence. If the provider is down,
private access stays unavailable until it is repaired; personal checks continue.
Restoring old local control state can restore old permissions. Preserve the latest
state with your controlled host recovery and re-fence after a restore before
opening access; this tool does not make stale backups current.

Access-event pseudonyms and token hashes are linkable metadata, not anonymization.
No token, directory name, email, answer text or arbitrary notes go into the event
journal. Event expiry is local and bounded; separately held backups and exports
need the operator's retention policy. No training collection is enabled.
