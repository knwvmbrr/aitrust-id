# Test metadata storage without collecting people’s data

The website still downloads feedback locally. There is no connected intake,
participant signup or training database. This runnable development component
tests the storage rules using synthetic records only, alongside the
[proposed pilot contract](metadata-pilot-contract.md). That contract still needs
owner approval before implementation of its endpoint or real collection.

On Linux with PostgreSQL 18 installed, from your source checkout:

```sh
python3 scripts/metadata-store-sandbox.py
```

Use an ordinary user. No Docker, administrator credential, live database address
or external service is used. The helper creates its own private temporary cluster,
uses a Unix socket with TCP disabled, executes the controls, confirms shutdown and
removes the cluster. Only then does it write
`output/verification/metadata-store.json`. If shutdown cannot be confirmed, it
keeps the private directory and reports failure. It never deletes an active
cluster or touches the existing application database. It does not install
PostgreSQL or change your system service configuration.

## What it stores in the test

Only a supported method version and the three listed result/failure/usability
answers, plus synthetic permission, a random record ID, a separate withdrawal
digest and private server receipt/expiry times. The source export’s PS tag,
schema and purpose are fixed during validation. No prompt, answer, example,
subject fingerprint, span, IP address, device identity, participant identifier,
client timestamp or free-text field is accepted. Hashes used for withdrawal are
not content hashes. The local download marker does not become research consent.

Every input must use `metadata-storage-development/v1`, `synthetic: true` and
`synthetic_test_only`. A participant format is explicitly refused. These markers
do not magically determine whether data originated with a person; the test
harness supplies known synthetic records, and no production entry point exists.
The component is intentionally unsuitable for silently activating real intake.

## Roles and failure behavior

The non-login owner holds the schema. Intake can execute record/withdrawal
functions; it cannot read or change tables directly. Review can see grouped
enum counts with at least five records, without IDs or withdrawal digests.
Maintenance can expire rows and apply pending withdrawal instructions without
reading feedback. Other roles receive neither schema access nor public function
execution. Temporary-table shadowing cannot redirect the fixed-schema functions.

The parser rejects missing/extra/duplicate keys, including escaped duplicate
keys, wrong types, unsupported methods, wrong sharing/permission markers and
oversized input. Invalid escaped Unicode diagnostics cannot reflect the supplied
canary. Conflicting retries cannot overwrite a prior answer. A wrong withdrawal
digest does not remove another row or create an arbitrary retained instruction.

Withdrawal removes the row and retains a deletion instruction. Restored fixture
rows are hidden from review and removed by maintenance before use. Expired rows
are also hidden and deleted. The synthetic 30-day/7-day parameters illustrate the
proposed contract; they are not adopted terms or evidence of actual backup expiry.
The row-copy test is not a complete backup or replacement-host recovery test.

## Current evidence and remaining work

[39 actual Linux controls](../runs/2026-10-11-metadata-store-unicode-linux.json)
include all 80 supported answer combinations. The disposable helper runs as an
ordinary Linux user and records successful shutdown/removal before publication.
The source, database guards and [boundary controls](../tests/test_metadata_store.py)
are inspectable. A separate CI workflow is defined to execute the actual PostgreSQL
controls; its hosted run is a separate acceptance step.
Synthetic usability answers do not measure detector accuracy or reviewer agreement.

Before real collection: approve the endpoint, purpose, roles, active/backup
retention and withdrawal contract; implement invitations and quotas; inspect
proxy/provider logging; demonstrate encrypted backup expiry and complete
replacement-host recovery; update the effective notice; then have the owner
operate it. No requirement for a running pilot, enterprise audit service or
training/anomaly pipeline is completed by this storage component.
