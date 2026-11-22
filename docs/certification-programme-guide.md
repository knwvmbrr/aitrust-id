# Run the reference programme privately

This working local CLI is for the [complete programme design](certification-programme.md).
It neither accredits anyone nor issues certificates, tag judgments or mark rights.
It requires CPython3.10+ on macOS/Linux, no new package/service/account/network.
The existing current28-case engineering receipt is used as evidence, never
converted into independent accuracy or organization-service certification.
Only source-compatible evidence can be prepared; a stale source refuses.

## Private application and record

From the source folder, choose a new file in an existing owner-private0700
folder **outside every Git checkout**. Resolve ancestor symlinks, including
macOS `/var` to `/private/var`. Files are0600 and never replaced. For a disposable
parent use `mktemp -d`, then resolve its absolute path. Replace the example path.

```sh
python3 -I -S -B scripts/certification-programme.py practice --output /your/private/application.json
python3 -I -S -B scripts/certification-programme.py start --application /your/private/application.json --output /your/private/review-0.json
python3 -I -S -B scripts/certification-programme.py inspect --record /your/private/review-0.json
```

Practice creates an **invented** applicant, four declared role IDs, documents and
current public engineering evidence. It reads no real application or private
organization. `checklist_complete:true` means the reference application has the
required named documentation/current selected evidence and no declared conflict;
it does not prove competence, honesty, actual independence or authority. Review
and replace the private documents deliberately for your preparation task.
Tag-accuracy and organization-service scopes retain their additional requirements.

## A complete assessment and separate decision

An event is private UTF8 JSON with `kind`, `actor`, UTC `at`, and closed `data`.
Here is an assessor event for the invented application. Save it as a new0600
`assess.json`, replace the timestamp with actual current UTC and inspect the
application/document/evidence contents before making any declaration:

```json
{
  "kind":"assess",
  "actor":"example_assessor",
  "at":"2026-11-22T06:00:00+00:00",
  "data":{
    "disposition":"recommend",
    "checked_requirements":["scope","competence","test_plan","evidence","impartiality","decision","appeals","surveillance","privacy","authority"],
    "reason":"Invented exercise: all reference documents inspected; no actual accreditation."
  }
}
```

The time must be no earlier than the current record and no later than now.
Writing an event does not apply it. This command consumes it, validates the
current exact programme/source/application and saves the next immutable record:

```sh
python3 -I -S -B scripts/certification-programme.py advance --record /your/private/review-0.json --event /your/private/assess.json --output /your/private/review-1.json
```

A separate decision event uses `kind:decide`, `actor:example_decision_reviewer`,
`disposition:complete`, the same ten checked requirement IDs, a new time/reason.
Consume it against `review-1.json` to a new `review-2.json` using the same command.
`REFERENCE_REVIEW_COMPLETE` is a completed reference checklist review, with
`certification_granted:false`, `accreditation_granted:false`,
`actual_role_identity_verified:false`, `independent_accuracy_verified:false` and
`mark_authorized:false`. Distinct strings are not independent real people.

## Events and allowed transitions

| Event kind | Declared actor | Required data and result |
| --- | --- | --- |
| `assess` | assessor | `disposition:recommend/changes/recuse`, all `checked_requirements`, `reason`. Conflicted assessor can only recuse. |
| `decide` | decision reviewer | `disposition:complete/changes/refuse`, all checked requirements, reason; a recommendation must already exist. |
| `appeal` | applicant | `reason`; replaces the current displayed state with `APPEAL_PENDING`. |
| `appeal_decide` | appeal reviewer | `disposition:remand/uphold`, all checked requirements, reason. Remand requires correction; uphold cannot restore an expired/incomplete completion. |
| `correct` | applicant | `application` (complete replacement object with same ID), `reason`; invalidates prior recommendation/completion. |
| `renew` | applicant | `valid_until` UTC timestamp, `reason`; invalidates review, never renews approval automatically. |
| `suspend` | decision reviewer | `reason`; withholds prior recommended/completed reference review. |
| `withdraw` | applicant | `reason`; terminal for that application record. |

Every event uses the same `advance` command, a different new output, and the
prior record. Unknown fields/roles, missing acknowledgments, bad order and
unresolved conflicts refuse. An appeal reviewer is distinct from the applicant,
assessor and decision reviewer. A correction can change declared roles/scope,
but every earlier recommendation/completion is invalidated. `inspect` replays
history and reports current expiry; it does not trust the stored state label.
No unfilled role is appointed automatically.

When method/programme sources change, obtain fresh application/evidence and run:

```sh
python3 -I -S -B scripts/certification-programme.py revalidate --record /your/private/old-review.json --application /your/private/new-application.json --output /your/private/revalidated-0.json
```

No prior action or approval is imported. The old record is linked by exact byte
digest only; this does not authenticate an older method. Keep the same application
ID for revalidation of a current, replay-valid nonwithdrawn record. After
terminal withdrawal, or when older programme/method sources cannot be replayed,
use a **new** application ID. A current record's stored state is replayed before
this decision; changing it cannot bypass terminal withdrawal.
Do not fill in missing metadata or change the hash of an old source observation.

## Failure, privacy, removal and limits

Exit0 means the requested reference operation ran, not that an application is
accepted by a real body. Inspect state/missing count and all false claim flags.
Exit2 is fixed `UNAVAILABLE`; the console includes no document text, actor ID,
private path or hash. If publication or cleanup cannot be confirmed,
`reason:output_commit_uncertain` and `output_may_exist:true` require inspection of
your selected destination. Abrupt interruption can leave files. Do not assume
rollback/erasure or overwrite a previous output. There is no daemon to uninstall;
remove the explicit files when wanted, recognizing backups/forensic copies.

Limits:1MB per JSON input,2MB combined input, depth16,8192 characters per string,
64 documentation items,32 actions and bounded source captures. Output must fit
1MB so a subsequent command can consume it. Inputs do not select code, policies,
executables, URLs or network calls. The OS/source owner remains trusted; local
hashes/replay are not authenticated identities, immutable storage or legal proof.
Failure of this optional CLI leaves existing personal checkers unchanged.
