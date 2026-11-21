# Govern a local organization's literal-policy jobs

This optional macOS/Linux CLI gives an operator separate local tenant namespaces,
credentials, policy revisions and private exports. It uses Python 3.12+ and the
standard library. There is no server, account, background agent, upload, model
download or paid dependency. Personal PS and other public methods stay separate.

The operator controls the private registry and its authority file. A tenant
credential authorizes only its named tenant and granted operations. This is local
technical control, **not** verification of a real organization, employee consent,
legal ownership, commercial terms or compliance. A literal match is not a policy
violation or an AI Trust ID public tag. No organization service is running or sold.

## Create an invented practice registry

Use a new private folder outside every Git checkout. Resolve the macOS temporary
directory link before passing paths to the tool. No existing destination is
overwritten:

```sh
policy_practice_dir="$(python3 -c 'import tempfile;from pathlib import Path;print(Path(tempfile.mkdtemp(prefix="aitrust-policy-")).resolve())')"
python3 scripts/organization-policy.py keygen --output "$policy_practice_dir/authority.json"
python3 scripts/organization-policy.py init --registry "$policy_practice_dir/registry" --authority "$policy_practice_dir/authority.json" --accept-local-contract
python3 scripts/organization-policy.py enroll --registry "$policy_practice_dir/registry" --namespace sample-team --offering team --authority "$policy_practice_dir/authority.json"
python3 scripts/organization-policy.py grant --registry "$policy_practice_dir/registry" --namespace sample-team --authority "$policy_practice_dir/authority.json" --roles view check export configure --seconds 3600 --output "$policy_practice_dir/team.cap"
```

`--accept-local-contract` adopts only `local-owner-organization-namespace/v1`.
The registry records its measured filesystem owner, a random registry identity
and the selected authority-file digest. Enrollment assigns an immutable tenant
identity and a unique local name. `team`, `enterprise` and `proprietary` identify
separate operator-selected offerings under the same local controls; they do not
imply a purchased subscription or different permission to redefine public tags.

Keep the authority file separately protected. It can enroll/remove tenants,
grant/revoke credentials and pause/restore a tenant. Do not edit a credential's
JSON: its exact bytes are bound to the current tenant grant. Ordinary credentials
cannot enroll another namespace or grant themselves permissions. All private
files must be regular, singly linked, current-owner mode0600 files beneath
mode0700 directories; symlinks and Git ancestors are refused.

## Review and register an exact policy

Write these invented values to two new mode0600 files inside the practice folder.
`policy.json`:

```json
{"format":"organization-literal-policy/v1","namespace":"sample-team","policy_id":"review","revision":1,"claim":"literal_term_occurrence_only","limits_visible":true,"receipts_optional":true,"personal_checks_separate":true,"rules":[{"code":"DRAFT_NOTE","terms":["confidential draft"]}]}
```

`subject.txt` can contain `Please review this confidential draft.` The policy is
an explicit operator-selected definition; the subject is never executed.
Use your normal editor and check its file permissions, then:

```sh
python3 scripts/organization-policy.py add-policy --registry "$policy_practice_dir/registry" --namespace sample-team --credential "$policy_practice_dir/team.cap" --policy "$policy_practice_dir/policy.json"
python3 scripts/organization-policy.py prepare --registry "$policy_practice_dir/registry" --namespace sample-team --credential "$policy_practice_dir/team.cap" --job review --revision 1 --subject "$policy_practice_dir/subject.txt" --output "$policy_practice_dir/selection.json"
python3 scripts/organization-policy.py check --registry "$policy_practice_dir/registry" --namespace sample-team --credential "$policy_practice_dir/team.cap" --selection "$policy_practice_dir/selection.json" --subject "$policy_practice_dir/subject.txt" --reviewed-policy
```

The last flag means that you deliberately reviewed this invocation. It is not
proof that an employee freely consented. The brief result gives the count of
selected literal occurrences, omitting text, namespace, fingerprints and positions.
A measured no-match is zero. An unavailable check has `literal_occurrences:null`,
never a fabricated zero or a compliance verdict.

The selection binds the tenant/registry identity, credential, current governance
epoch, exact policy revision, raw subject bytes, frozen NFC subject and current
mechanism/vocabulary sources. Even an NFC-equivalent raw edit requires a new
selection. Another tenant's policy change does not stale this tenant's selection.
Within a tenant, access/policy changes deliberately invalidate prior selections.

## Separate permissions and explicit private output

Permissions are independent:

| Permission | Authorized operation |
| --- | --- |
| `view` | Inspect the tenant's job-count summary. |
| `check` | Prepare/select and run an active exact job. |
| `export` | Save details in conjunction with the relevant view/check permission. |
| `configure` | Add the tenant's immutable policy revision or pause/restore its job. |

A check-only credential cannot save results or configure a policy. A view-only
credential cannot check. Every operation checks current tenant, capability digest,
expiry and revocation. The same checks are repeated before publishing a result.
An exclusive tenant mutation cannot race a shared check/export lock; other tenants
use separate stores and locks.

```sh
python3 scripts/organization-policy.py check --registry "$policy_practice_dir/registry" --namespace sample-team --credential "$policy_practice_dir/team.cap" --selection "$policy_practice_dir/selection.json" --subject "$policy_practice_dir/subject.txt" --reviewed-policy --output "$policy_practice_dir/result.json"
python3 scripts/organization-policy.py inspect --registry "$policy_practice_dir/registry" --namespace sample-team --credential "$policy_practice_dir/team.cap" --output "$policy_practice_dir/inventory.json"
```

Detailed results contain private hashes, positions, qualified local identifiers
and the complete canonical literal observation, with no full subject text. These
values can still link information. Inventory exports reveal private policy/access
metadata. Protect and share either deliberately. No export is automatic.

The local result wrapper identifies registry/tenant ownership control. The
unchanged canonical observer still labels real namespace ownership unverified;
the wrapper does not promote that field into company identity or public adoption.

## Revision, pause, revoke and recover

Register the next policy as a **new** file with the same job and revision2.
Revisions are immutable and contiguous. Old versions are retained as metadata,
but only the current enabled revision can execute. To reuse older terms, register
them as the next reviewed revision rather than silently rolling back a selection.
Changing mechanism or public-vocabulary source also requires a current revision.

```sh
python3 scripts/organization-policy.py job-enabled --registry "$policy_practice_dir/registry" --namespace sample-team --credential "$policy_practice_dir/team.cap" --job review --enabled false
python3 scripts/organization-policy.py job-enabled --registry "$policy_practice_dir/registry" --namespace sample-team --credential "$policy_practice_dir/team.cap" --job review --enabled true
python3 scripts/organization-policy.py revoke --registry "$policy_practice_dir/registry" --namespace sample-team --authority "$policy_practice_dir/authority.json" --credential "$policy_practice_dir/team.cap"
python3 scripts/organization-policy.py grant --registry "$policy_practice_dir/registry" --namespace sample-team --authority "$policy_practice_dir/authority.json" --roles check export --output "$policy_practice_dir/replacement.cap"
```

The revoked credential remains refused. Prepare a new selection with the
replacement credential before checking again; do not reuse an old selection.
`tenant-enabled --enabled false` with the authority pauses all tenant operations;
the authority can restore it with `true`. Restore does not undo an explicit
credential revocation, and old selections still need replacement.

## Remove without a background service

```sh
python3 scripts/organization-policy.py remove-tenant --registry "$policy_practice_dir/registry" --namespace sample-team --authority "$policy_practice_dir/authority.json"
python3 scripts/organization-policy.py remove-registry --registry "$policy_practice_dir/registry" --authority "$policy_practice_dir/authority.json"
```

Tenant removal checks its exact managed entries and takes its exclusive lock.
It does not remove another tenant. Registry removal requires no tenants remain.
The authority, credentials, subjects, selections and exports outside the registry
remain yours to inspect/delete separately. No account or daemon needs disabling.
Deletion is logical: no forensic-erasure, backup, provider-copy or OS-swap claim.

## Bounds and failure handling

There are at most8 tenants,8 jobs per tenant,8 revisions per job,16 lifetime
credential grants and256 metadata events per tenant. Each SQLite file uses4096-byte
pages and at most2048 pages (8MiB); its private rollback journal can temporarily
use another8MiB. At capacity, the affected operation is unavailable; export what
you need and explicitly retire/re-enroll a tenant rather than silently pruning
history. Re-enrollment has a new tenant identity and does not accept old credentials.

The existing canonical observer accepts20,000 input codepoints and bounded ASCII
literal phrases; it does not interpret meaning or infer a violation. The new
worker receives only the selected policy/text/context, not authority credentials.
Each job has a fresh isolated-stdlib process,3-second wall limit,2-second CPU limit,
64 descriptors, zero file-size/core allowance and262144-byte output cap. Linux
also limits the worker address space to128MiB. The parent checks the entire result
against bounded canonical replay, then rechecks permission and input identity.
This is not a general sandbox for arbitrary executable plugins; none are accepted.

Ordinary refusal exits2 with fixed diagnostics, no subject text or private path.
No new final export is created before the publication boundary. If a link,
directory synchronization, temporary cleanup or close fails after publication,
`output_commit_uncertain` reports `output_may_exist:true` and
`operation_may_have_applied:true`. A complete output or applied registry mutation
may exist. Inspect the requested destination and private registry **before retry**.
Private `.org-policy-*` temporaries can remain if cleanup itself fails. Do not
assume rollback, overwrite a destination or delete unknown files automatically.
Interrupted initialization/enrollment can leave a private incomplete directory;
it is not admitted until its final complete contract is published.

## Trust and full requirement limits

The OS owner/administrator, selected source checkout and local authority remain
trusted. Capability checks are not OS account separation. A same-account process
with file access can bypass this CLI or copy/restore a registry; no external
latest-state pin detects a deliberately restored old database. A restored copy
can restore its older revocation state. Protect backups as authority-bearing data.
No real employer identity, employee consent, anti-coercion, commercial terms or
global namespace ownership is established.

The N-010 historical final human-operation/commercial-conformance gate in
`docs/private-policy-result.md` and `docs/private-policy-plan.md` is preserved.
The PM's local technical-contract adoption authorizes this mechanism, not that
outside acceptance. Full N-010 completion is not claimed by this software.

Focused stdlib controls:

```sh
python3 -B -m unittest discover -s tests -p 'test_organization_policy_*.py' -v
```

They exercise actual CLI/worker use, independent tenant/job failures, current
permissions, raw/NFC bindings, private output/uncertainty, removal and unchanged
personal PS operation. Actual Mac/Linux receipts and distinct review are separate
from tests of real organization identity, employee/human operation or accuracy.
