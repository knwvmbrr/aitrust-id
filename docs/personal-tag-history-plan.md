# Personal tag history and the identification standard

Owner direction recorded November 23, 2026. This is an execution contract and
scope clarification, not working history storage or a new released detector.
All 202 original requirements and their completion criteria remain intact.

## Product and business outcome

AI Trust ID's goal is an openly implementable identification standard with
independent tags, reproducible eligible evidence and a usable challenge process.
People should be able to understand both a finding and what was not established.
The owner accepted the existing business model: free personal checking and current-result evidence; optional paid personal
history; free signup-based community participation; organizational fleet, private
deployment, audit retention, SSO and support as separately specified paid capabilities. No price, customer, revenue, valuation,
certification authority or standards-body recognition is established here.

Adoption of a standard must be earned. Publish versioned contracts and vectors,
support independent implementations, disclose errors and conflicts, preserve
compatibility, and keep a commercial entitlement from changing a tag's meaning.
Accuracy is measured per job, format, method and declared population.

## Independent history job

**Job:** let a person revisit tags that AI Trust ID actually displayed to them.
**Outcome:** a readable timeline explains where and when a finding appeared,
what the tag found, which method produced it, and its current correction state.
The owner explicitly selected personal history as a PAID UPGRADE. It is an
account-based enhancement of evaluated results, never a prerequisite for free
checking or a claim that every visible screen item was inspected. A user can
always inspect/export the current finding without buying a timeline. Export and
deletion of already-held personal account data must remain available when a
subscription ends; expiry does not authorize withholding a user’s data.

Initial implementation target: the browser's existing explicit check route and
its resulting tag. Extend to the extension and native Share through adapters to
the same versioned record. Each route must demonstrate its own consent,
storage, failure and deletion behavior. An unrelated tag, offline checker or host
action must remain usable if history is disabled, full, corrupt or unavailable.

## Privacy and record boundary

History starts off and requires an explicit upgrade choice; no checkout or paid
service is operating yet. Before enabling it, show what will be saved, where, the
retention limit and how to erase it. Treat origin, timestamps, tag subjects and
even hashes as potentially sensitive/linkable data.

The proposed minimal record includes a random local event ID, local display
time, tag/method/version, bounded result state and non-input explanation, adapter
identity and a user-approved source label. Local display time is not a trusted
timestamp. An origin must exclude paths, query strings, credentials and fragments
by default; an application name can replace an origin. Do not store original
text, image pixels, screenshots, audio, clip data, page titles or excerpts by
default. Do not scrape the surrounding page to enrich a history entry.

Content excerpts, full locations and content fingerprints require separately
explained choices. Eligible reproducibility requires the original private input
and complete processing identity; a minimal history entry alone cannot promise
replay. Keep historical records unchanged and append a correction/supersession
link rather than silently rewriting what was previously shown.

Personal history and optional research submissions are separate stores and
separate permissions. Signing up or paying does not authorize training, ambient capture, telemetry or
business tracking. Account data may be processed for the disclosed account and
service purpose. Server history storage, if selected, needs its own approved
endpoint contract, least-privilege authentication, encryption/key recovery,
withdrawal, retention and recovery acceptance before activation; do not claim browser storage is encrypted or secure against a
compromised device merely because it is local.

Proposed first bounds are at most 1,000 entries and 30 days of retention, with
the retained metadata body limited to 5 MB. Check expiry on startup and each
write/read; test clock rollback and unavailable storage. Show quota/eviction
behavior before loss, offer deletion and a previewed metadata export, and avoid
unbounded background retention. These are proposed engineering limits to qualify,
not already-operating retention promises.

## Delivery sequence and ownership

| Increment | Working outcome | Accountable owner | Completion evidence |
| --- | --- | --- | --- |
| H1 | Versioned metadata record, strict allowlist, independent history adapter | Tag/API engineer; PM integrates | Supported and malformed record cases; no raw-input/network effects; failure cannot alter the original finding |
| H2 | Opt-in timeline on the existing web check route | Web product engineer | Actual enable/check/revisit/filter/delete/disable; clear where/why wording; origin minimization; quota and expiry failures |
| H3 | Extension and native Share adapters | Platform engineers | Actual route-local display binding, duplicate/stale-result handling, offline storage and independent sibling behavior |
| H4 | Safe export, correction links and user control | Privacy engineer; different reviewer | Preview matches exported fields, no hidden content, selected/all deletion and retraction behavior; no automatic research submission |
| H5 | Supported-user acceptance | Michael and independent users, with engineering fixes | Physical phone and assistive-technology operation, comprehension, removal and a documented response to feedback |

H1-H4 engineering can advance without impersonating H5 users. No increment
reaches 100% until its complete named outcome is functioning and evidenced.
Run focused checks after implementation, then the affected release pipeline.
Do not repeatedly run an unchanged full suite to generate activity.

## Free signup community and the product interface

The community is an open forum about AI for users who sign up. Accounts support
participation, moderation and a direct relationship with users. Keep public
reading transparent and require an account to post; never expose account email,
billing identity or a user’s personal history in public discussions. Use explicit
moderation, reporting, appeals, rate limits and safe retraction rather than
autonomous unrestricted posting. This extends the existing community scope; it
is not an operating chat service.

The first interface should lead with Check, Tags, History and Community as each
becomes functional. Do not add dead navigation or a fake checkout. Explain the
current action/result in one short sentence, use small tag chips, and keep full
methods, validation, sources and legal detail in accessible disclosures. Publish
each supported tag independently once its own release gate passes, and deliver
later tag improvements through versioned web/app updates. No all-tags release
dependency is introduced.

## Visual, spatial and temporal subjects

Keep separate evidence questions: file structure, declared provenance,
watermarks, statistical synthesis/manipulation, information support and context.
A valid signature does not establish the depicted event; a classifier score
does not establish an author's identity or intent. Several independent tags may
describe the same subject without depending on another tag's verdict.

| Format | Subject and finding binding required before release |
| --- | --- |
| Image | Exact image/version plus the relevant region and declared transformation |
| Video | Exact clip/version, timebase, frame/time interval and transformations; correlated frames are not independent samples |
| 3D | Exact scene/asset/resources plus object, geometry/view and rendering identity; rendered pixels and scene structure are distinct subjects |
| 4D working definition | 3D scene evolution over time: object identities, coordinate/time units, clock alignment, intervals and changing observations |

The 4D definition is a planning interpretation of the owner's direction. It
does not add a live protocol modality, physical dimension, detector or result
code. A standards/RFC decision must define compatibility and actual evidence
before a new subject profile is adopted. Retain Unsupported/Unavailable for
unimplemented formats instead of assigning an AI-origin verdict.

Model-level provenance is part of the intended ID: distinguish a provider/model
label displayed by a service, a signed generation declaration, and a measured
statistical attribution. Record exact supported model/version and trust policy
when established. Keep unknown-model rejection and declared transformation/error
coverage in targeted model-attribution research; dataset volume alone is not
proof. No arbitrary input is assigned an exact model without supporting evidence.

Current priority remains a bounded working image method, then independently
validated image outcomes, video localization, and one constrained spatial
format. Use the existing [visual execution baseline](visual-tag-execution-plan.md)
for rights, resource limits, benchmark separation, adversarial media and privacy.
History records format-specific findings through adapters; it never pretends
that missing image/video/spatial evaluation occurred.

## Risks and release rules

The main risks are sensitive browsing history, misleading replay promises,
untrusted stored text, history-driven coercion, storage exhaustion, corrupted
records, broken migration, and collecting data before meaningful consent.
Escape rendered fields, reject unexpected record fields, bound reads/writes,
test hostile records and keep diagnostics free of content/location values.
An organization cannot require a personal receipt or use history as covert
employee monitoring. Payment must not change the evidence standard.

This plan activates no capture permission, payment integration, endpoint, account,
proprietary model, live tag or data collection. The new history enhancement and
explicit 4D clarification are tracked separately from original closure counts.

## Explicit owner revision of the former free-feature boundary

The November23 owner direction supersedes the earlier blanket assertion that no
personal feature could be paid, solely for the optional personal history service.
Personal tag checking, meanings, current-result explanations/evidence,
accessibility and the public standard remain free/open. Account acquisition and
paid history are product scope, not permission to resell data or train on content.
The historical rule and rationale remain in Git; revise the current contribution
wording explicitly before this scope change is accepted into the public baseline.
Open-source code and the public standard remain inspectable and self-operable.
The optional paid service charges for the operated account/history experience;
we do not claim to prevent lawful independent implementations. No price, merchant
integration or terms of sale is invented here.
