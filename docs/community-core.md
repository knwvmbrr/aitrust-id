# Practice the community workflow

This is working **synthetic development software**, not the live AI Trust ID
community. It runs no server, sends no messages and accepts no real participant
data. GitHub remains the current public discussion/report path. Personal tags,
research intake, the website and native app are unchanged.

The core runs without a framework, network or third-party Python dependency.
It supports two invented users, an official account, two moderators and a local
administrator. Choosing `--actor` means a trusted local operator is rehearsing a
role. It does **not** authenticate that person or create a credential.

## Run an invented local example

On Linux or macOS with Python3.12+ and SQLite, create a private practice folder
outside Git. SQLite is only this synthetic workbench. The owner-selected real
data platform remains separate remote PostgreSQL; do not put user data here.

```sh
AITRUST_COMMUNITY_PRACTICE="$HOME/AITrust-community-practice"
install -d -m 700 "$AITRUST_COMMUNITY_PRACTICE"
python3 scripts/community-workbench.py init --root "$AITRUST_COMMUNITY_PRACTICE/store" --synthetic-only
```

Send this invented question through standard input. It is queued, not published:

```sh
python3 scripts/community-workbench.py apply --root "$AITRUST_COMMUNITY_PRACTICE/store" --actor user-one <<'JSON'
{"format":"community-workbench-request/v1","synthetic_only":true,"request_id":"11111111-1111-4111-8111-111111111111","operation":"submit","data":{"body":"Invented question: how can I challenge a PS finding?","consent_public":true}}
JSON
python3 scripts/community-workbench.py public --root "$AITRUST_COMMUNITY_PRACTICE/store"
```

Have the separate synthetic moderator approve revision1:

```sh
python3 scripts/community-workbench.py apply --root "$AITRUST_COMMUNITY_PRACTICE/store" --actor mod-one <<'JSON'
{"format":"community-workbench-request/v1","synthetic_only":true,"request_id":"22222222-2222-4222-8222-222222222222","operation":"approve","data":{"post_id":"11111111-1111-4111-8111-111111111111","version":1}}
JSON
python3 scripts/community-workbench.py public --root "$AITRUST_COMMUNITY_PRACTICE/store"
python3 scripts/community-workbench.py replay --root "$AITRUST_COMMUNITY_PRACTICE/store" --after 0
python3 scripts/community-workbench.py export --root "$AITRUST_COMMUNITY_PRACTICE/store" --output "$AITRUST_COMMUNITY_PRACTICE/public.html" --html
```

Open the private HTML file. It is an offline snapshot with escaped text, no scripts
and no embedded network resources. A saved snapshot cannot be remotely recalled.
New exports use current eligible content and never overwrite an existing file.

Use a new canonical UUIDv4 request ID for a new action. The bounded recent request
cache returns the same result for an identical retry; a conflicting retry refuses.
Old creates cannot duplicate an existing post after cache eviction. Retraction
and edits retire associated cached input digests, preventing old text from being
restored by replaying those requests. A subject or method hash is not collected.

## Independent actions and their exact fields

All actions use the same closed request envelope shown above. Every unknown field
is refused. No real-data or production mode exists.

| Action | `data` fields and result |
| --- | --- |
| `submit` | `body`, `consent_public:true`; creates a queued public-intended message |
| `reply` | `post_id`, current `version`, `body`, `consent_public:true`; links to an already-public message, and needs its own review |
| `edit` | Same fields as reply, author only; withdraws the old public view until fresh review |
| `approve` | `post_id`, `version`; moderator only; official replies also require review |
| `supersede` | `post_id`, `version`, `body`, `consent_public:true`; a queued correction; approval scrubs old text and links the replacement |
| `retract` | `post_id`, `version`, `reason`; author or moderator; removes text from current state, replay and new exports |
| `warn`, `restrict`, `suspend` | `post_id`, `version`, `reason`; moderator only; restrictions apply to the affected synthetic member |
| `report` | `target_id` UUID, `category`, `consent_private_metadata:true`; private fixed metadata, never a private text body |
| `review_report` | `report_id`, `disposition`, `replacement_record_id`; a different moderator records a separate disposition |
| `appeal` | Removed `post_id`, `version`; its owner requests review of that moderation action |
| `resolve_appeal` | `appeal_id`, `decision`; a different moderator may uphold or reopen review; scrubbed text never republishes automatically |
| `pause` | `paused` boolean; synthetic administrator only; stops new posting while reads and retractions remain available |

Reasons are `privacy`, `conduct`, `off_scope`, `incorrect`, `author_request`.
Report categories are `wrong_result`, `privacy`, `conduct`, `security`.
Dispositions are `needs_evidence`, `no_change`, `correction_referenced`; only the
last accepts a new, distinct `replacement_record_id`, otherwise use JSON null.
Appeal decisions are `upheld`, `reconsider`.

A report's target and replacement IDs are **unverified references**. Recording a
moderator disposition does not authenticate either assertion, change a tag,
establish ground truth or issue a corrected tag. Public posting is not training
consent; private metadata consent is not public posting permission.

```sh
python3 scripts/community-workbench.py private --root "$AITRUST_COMMUNITY_PRACTICE/store" --actor user-one
python3 scripts/community-workbench.py audit --root "$AITRUST_COMMUNITY_PRACTICE/store" --actor mod-two
```

Members see only their own queue/reports/appeals. Moderators see the synthetic
review queue. Audit requires a moderator or administrator and contains bounded
IDs, actors, fixed reasons and local timestamps, never message bodies. These
private command outputs are deliberate operator access, not public responses.

## Replay and future web/mobile clients

The `community-public-projection/v1` read contract exposes only approved current
text or a safe tombstone: ID, revision, state, official-reply marker, replacement/
reply links, coarse reason, local update time and a private-appeal instruction.
IDs and timestamps can correlate activity; no anonymity guarantee is made.
There is no selected HTTP route or streaming transport.

A future client must render `body` as text; the supplied HTML renderer escapes it.
Use no-store responses, maintain the public sequence, apply contiguous replay
through `update_cache`, and replace old body fields with tombstones/review-pending
items. A replay gap explicitly requires discarding the old cache and fetching all
current pages at one unchanged sequence before resuming. Do not preserve removed
bodies in a separate client history or analytics store. Browser/native integration,
CSRF, TLS, session authentication and moderator MFA remain unimplemented gates.

Public replay stores no body history: each event resolves to the record's current
eligible projection. An old sequence cannot recover removed text. Existing
saved pages, outside copies and manually quoted separate posts cannot be recalled;
moderators must review other affected posts separately. No automatic leak detector
or automatic redaction is claimed.

## Bounds, storage and recovery limits

The engine caps256 posts,128 private metadata reports,128 appeals,128 replay
events,256 cached requests and4096 audit actions. Eight ordinary write attempts
per actor per60 trusted-clock seconds are admitted. Requests are at most16KiB;
message bodies are at most2000 characters and reject unsafe control/bidi text.
Reads use1–20 items. The last 257 audit slots are reserved for retraction and one emergency pause.
Clock rollback, stale revisions, corrupt state, unavailable
storage, held locks and capacity exhaustion refuse explicitly. These are software
bounds, not a service SLA or internet-level denial-of-service protection.

Synthetic SQLite uses private owner-held0700/0600 files, fixed schema, no links,
exclusive nonblocking locks and atomic transactions. PostgreSQL uses its own
private socket-only test cluster, separate schema/roles and a256KiB JSONB state
cap. The database reserves 1 KiB for each removable message and one more for
pausing posts. Ordinary writes can therefore reach the byte limit before the
engine reaches its count limit. The adapter retries a conflicting update at most
six times. No raw user text is placed
in process arguments or PostgreSQL diagnostics. Database and OS administrators
remain trusted; the runtime role is a trusted application role, not a participant.
Its CAS function can submit replacement synthetic state: it is not SQL-enforced
participant/role authorization. Do not give that role or its function to browsers
or users. Python enforces operation/actor permissions inside the trusted core.
Public SQL also masks queued/retracted bodies and unexpected projection values;
a compromised trusted runtime can still fabricate plausible approved state.
Those boundaries do not establish production authentication or signed posting.

Retraction is logical deletion in the current document. Neither SQLite pages,
PostgreSQL MVCC/WAL, backups, existing exports nor provider copies are physically
erased by that operation. There is no background retention or backup service for
this synthetic workbench. Real collection still requires separately accepted
retention, at-rest protection, withdrawal, backup expiry and replacement-host
recovery. A local workbench must not be advertised as that operating platform.

```sh
python3 scripts/community-workbench.py remove --root "$AITRUST_COMMUNITY_PRACTICE/store" --confirm-synthetic-removal
```

This removes only the verified synthetic SQLite store. Exports remain yours to
remove deliberately. PostgreSQL test teardown belongs to the disposable-cluster
runner; its CLI refuses generic database removal.

## Run engineering checks

```sh
python3 -m pytest -q tests/test_community_core.py tests/test_community_store.py tests/test_community_cli.py tests/test_community_postgres.py
python3 scripts/verify-community-core.py --output output/verification/community-cli.json
```

For PostgreSQL18 installed at the existing Linux path, use the isolated wrapper:

```sh
sudo unshare --net -- "$(command -v python3)" scripts/community-postgres-sandbox.py --run-as "$(id -un)" --output output/verification/community-postgres.json
```

It drops privileges through the existing reviewed helper, creates its own private
socket-only cluster, runs actual CLI/database/role/concurrency/retraction controls,
then verifies shutdown before deleting the cluster. It cannot select production.
The focused hosted workflow performs this same check. Actual executed results and
remaining operating gates are recorded in [the result](community-core-result.md).
