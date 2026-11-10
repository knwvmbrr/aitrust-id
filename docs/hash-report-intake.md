# Private hash-only reporting inbox

This free local operator tool accepts feedback **about** a PS or PII_REDACTED
check. It does not evaluate content, verify a complaint, establish a training
label or send anything to AI Trust ID. The proposed public registry, company
research intake and public moderation remain separate and disabled/unoperated
where their existing gates remain open.

Use an unprivileged macOS/Linux Python 3.12+ environment with SQLite support.
No account, network, container, signing authority or other tag service is needed.
Create an owner-held `0700` directory outside Git and sensitive system folders.
Keep the inbox on a local filesystem with working OS/SQLite locks.

## Preview first

The only accepted record fields are shown below. These are invented example
identifiers, not a real user report. A subject hash and method hash must each
contain exactly 64 lowercase hexadecimal characters. Hashes are linkable
metadata; they are not anonymous or proof that the named source was checked.

```json
{"format":"local-hash-feedback/v1","subject_sha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","method_sha256":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","code":"PS","category":"false_alarm"}
```

Codes are `PS` and `PII_REDACTED`. Categories are `false_alarm`, `missed_pattern`,
`unavailable` and `unclear`. Use the identifiers from your own chosen result,
not the invented identifiers above. Original/redacted text, free-form notes,
identity, credentials, URLs, evidence positions and training labels are refused.
The strict parser also refuses duplicate JSON fields and oversized input.

```sh
python scripts/hash-reports.py preview < /private/operator/report.json
python scripts/hash-reports.py preview --json < /private/operator/report.json
```

Preview writes nothing. `--json` explicitly displays the full hash metadata.
Do not paste this output into a public issue or community message if it could
identify sensitive text. A private report is not automatically a public dispute.

## Store only with consent

Choose an existing private parent directory. Initialization never replaces an
existing inbox. The storage flag is required for **every** intake; there is no
background observer or hidden forwarding destination.

```sh
python scripts/hash-reports.py init --root /private/operator/inbox --days 30
python scripts/hash-reports.py ingest --root /private/operator/inbox --consent-store-hashes < /private/operator/report.json
python scripts/hash-reports.py stats --root /private/operator/inbox
```

The returned ticket identifies local unverified feedback. Repeating the same
subject/method/code/category returns the same active ticket without extending
expiry. Different methods and categories remain distinct. Capacity is 10,000
active records; a full inbox refuses new distinct reports until expiry or an
explicit withdrawal frees space. This is an admission limit, not a throughput
or service promise.

## Expiry, withdrawal and export

Choose one to thirty days at initialization. Expired records are excluded and
pruned on the next operation or explicit `prune`. If the tool is not running,
expired bytes can remain on disk until that operation. Use an operator-managed
scheduler if your own policy needs wall-clock cleanup. No scheduler is installed
and this is not the future hosted registry's retention service.

```sh
python scripts/hash-reports.py prune --root /private/operator/inbox
python scripts/hash-reports.py withdraw --root /private/operator/inbox --ticket YOUR-TICKET-UUID
python scripts/hash-reports.py export --root /private/operator/inbox --output /private/operator/export.json
```

Export is explicit, owner-private, closed metadata with `verified: false` and no
training labels. It never overwrites a file. Withdrawal and expiry are logical
deletion: exported copies, filesystem snapshots and backups are not removed.
The operator owns disk encryption, backups and any separate sharing decision.
No claim of physical erasure or end-user identity authentication is made.

```sh
python scripts/hash-reports.py remove --root /private/operator/inbox --confirm-inbox-removal
```

Removal verifies the owned inbox and refuses foreign files or links. It removes
only this directory. It does not remove exports or alter the independent personal
checker. A damaged or unavailable inbox produces an explicit unavailable result,
never a successful report. Same-user malware and OS administrators remain trusted.
This utility grants no authority to issue tags, decide a dispute, train a model
on feedback, activate company collection or promise a moderator response.
