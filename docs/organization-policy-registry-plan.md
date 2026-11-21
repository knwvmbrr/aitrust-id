# Local organization policy governance — architecture before implementation

Base: `e8287050493f3f30b6c92967beed224a6c8b4dc3`. Owner: Codex
`/root/share_debugger`, isolated branch `codex/organization-boundary-audit`.
The existing owned worktree is reused to avoid another checkout/disk copy.
The PM owns shared scope, state, catalogue, inventories and publication.

## Original requirement and preserved acceptance

N-010 is the personal/team/enterprise/proprietary offering-boundary job. Its
remaining required acceptance is: "Accept organization namespaces and ownership
boundaries; implement per-tenant custom policy and validate each job separately.
No organization service is running or sold."

ORG-PRIVATE also requires that private rules cannot redefine public codes, that
no closed/paid dependency becomes mandatory in the free personal workflow, and
that actual custom scope, ownership and licensing are agreed **before sale**.
The historical private-policy result separately left real namespace adoption,
privacy/human operation and commercial conformance open. Do not edit that history
or claim those outside observations occurred. The PM has authorized adoption of
a local-only technical namespace/ownership contract; this is not acceptance of
customer terms, a real organization's identity, employee consent or a sale.
Final full-original closure remains a distinct PM/reviewer decision against all
retained criteria. If an unconditional human gate remains, recommend no closure.

## Existing mechanism and actual gap

`tools/private_policy.py` already supplies a bounded literal-term policy with
frozen NFC identity, qualified private codes, public-vocabulary collision refusal
and fixed nonverdict wording. Its namespace remains an unverified caller claim.
It has no enrolled tenant, authority, permission grant/revocation, immutable job
revision selection or governed export. Directory/SSO and PostgreSQL audit tools
have their own executed jobs; they do not currently authorize this policy tool.
Do not pretend their older evidence executes the new governance route.

## Proposed complete local profile

1. An operator initializes a new owner-private registry outside every Git
   checkout and explicitly accepts the versioned local technical contract.
   Filesystem ownership is measured, not supplied as a request field. The local
   administrator obtains an explicit private authority file. No account, remote
   endpoint, production key, paid dependency or global credential is created.
2. Register separate team/enterprise/proprietary tenants under unique qualified
   local namespaces. A registry UUID and immutable tenant UUID disambiguate equal
   names in different installations. Public codes/standard namespaces cannot be
   adopted. Personal checking remains free, unchanged and outside the registry.
3. Issue bounded tenant credentials with explicit view/check/export/configure
   permissions. Only the registry authority enrolls tenants or grants/revokes
   access. Store credential digests rather than plaintext secrets in the tenant
   store. Check current tenant, role, expiry and revocation on every operation;
   a caller-provided tenant label or policy is not authority.
4. Store immutable policy revisions and append-only metadata events in separate
   private stdlib SQLite tenant stores. Unique keys, fixed parameterized SQL,
   bounded histories and per-tenant locks enforce revision and isolation rules.
   A broken policy/store/worker in one tenant must not alter another tenant.
   Retention is explicit and bounded; capacity exhaustion is Unavailable.
5. Select an exact current job/revision against an explicit owner-held subject.
   Bind raw subject bytes, frozen NFC, registry/tenant/policy identity, current
   governance epoch, vocabulary and mechanism sources. Persist policy definitions
   only; never automatically persist the subject or a check result. A changed
   subject, policy, access epoch, method or vocabulary requires a new selection.
6. Execute each selected job in a fresh bounded stdlib process using the existing
   canonical literal observer. Never execute subject text, caller code, regex,
   templates or callbacks. Fixed worker input/output/time/resource caps and
   closed result validation preserve one-job failure independence. No sibling
   tag result, SSO provider, database service, network or account is required.
7. Brief default output excludes private text, identifiers, hashes and positions.
   A result export requires an independent current export permission and an
   explicit private destination. Descriptor-bound no-follow reads, atomic complete
   no-overwrite publication, exactly-once handle cleanup and honest
   `output_commit_uncertain` handling preserve known I/O corrections. Do not
   promise rollback or forensic deletion after a filesystem uncertainty.
8. Pause/revoke/replace/retire and remove the local registry explicitly. Old
   selection/credentials cannot revive a retired policy or tenant. An unavailable
   optional registry/check must leave personal PS and another independent tenant
   available. Do not activate an organization service or change public meanings.

## Ownership and files

Only new files are owned: `tools/organization_policy_registry.py`,
`tools/organization_policy_io.py`, `tools/organization_policy_worker.py`,
`scripts/organization-policy.py`, focused registry/CLI test modules, this plan,
the usage guide and fresh run records. Existing canonical policy, public tags,
directory/audit/fleet tools and shared CI/state/scope/catalogue remain unchanged.
The new I/O helper will adapt the audited descriptor primitive with attribution;
it will not import a sibling tag module. The PM coordinates the final change
event and integration inventory before source commit/publication.

## Success, failures and verification

Actual commands must initialize, enroll at least two namespaces, independently
grant permissions, register/version/select/check each job, explicitly export,
revoke/recover, retire and remove. Exercise cross-tenant/role denial, forged and
expired credentials, stale/raw-NFC-equivalent edits, changed policy/source,
public-code collision, worker failure/capacity and export overwrite/uncertainty.
Positive no-match is a measured zero; Unavailable has no measured count. Inspect
the actual private outcome and ensure console/errors have no private canary.
Prove another tenant and unchanged personal checker work after an optional fault.

Focused controls and actual Mac CLI cases precede source freeze and distinct
review. Use the existing authorized Linux/CI route only after PM confirms its
account-use boundary; no local Docker, SDK, new server or dependency installation.
Run current-source integration and supported install/use/removal before claiming
software completion. Tests do not prove organizational authority or accuracy.

## Risks and trust boundary

The operator, selected source checkout and OS owner/administrator remain trusted.
A same-account process with access to registry files can bypass a local CLI;
capability checks do not create OS account isolation or a remote service. Tenant
stores contain private policy definitions and access metadata; protect backups
and exports. SQLite WAL/journals and deleted files are not forensic-erased.
Per-tenant lock ownership must cover authorization through publication so revoke
cannot race an export; other tenants must not share that lock. Source selection
and private output publication need mutation/fd-close/uncertainty controls.
Do not call this global namespace registration, real-company verification,
employee consent, compliance, tag accuracy or commercial release acceptance.


## Implementation refinements before freeze

The new I/O helper reuses validated directory descriptors within one operation,
rechecking both held and named identities before reuse. This avoids multiplying
ancestor descriptors for every source file; the complete actual CLI sequence is
also exercised with a64-descriptor parent limit. A replaced cached parent refuses.
The child separately has64 descriptors and zero core/file-size allowance.

History review found that commit7c103f5e737c6684d6a4057c70cc5e9bbeb14b74
introduced the still-unconditional final privacy/human-operation wording. This
implementation will not recommend full N-010100 from software alone. Local
technical-contract adoption does not supersede that gate.
