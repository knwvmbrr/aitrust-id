# MT owner increment: keep urgency evidence in its own sentence unit

Codex MT owner · 2026-11-16 · isolated branch `codex/mt-method-increment`.
Base: `2739570` (current main when this lane started).

## What changed in functioning code

Urgency revision `english-context-observations/1.1.0` requires a supported
sentence-start directive and a time phrase inside the same existing sentence
unit before nominating an observation. It keeps whole-input directive density,
the same threshold, every literal time-phrase/directive measurement and the
8,000-character input limit. New `paired_units` and
`unpaired_time_pressure_spans` make the association boundary inspectable.
Findings no longer borrow supporting positions from unrelated units.

This is a bounded method improvement, not a finding that the old code contradicted
its published global-co-occurrence contract. Hedge and authority algorithms stay
at revision 1.0.0. Their shared source fingerprint changes and remains explicit.
The existing JSON CLI and observation verifier accept the new output; no public
assertion schema, taxonomy, production allowlist or PS method changed.

## Actual before and after, using invented examples

| Input | Previous method | Current method |
| --- | --- | --- |
| The committee met today. Read the archived minutes. | Nominates urgency observation | Retains literal measurements; no within-unit association |
| Install the patch. The news was published today. | Nominates urgency observation | Retains literal measurements; no within-unit association |
| Read the evacuation notice now. | Nominates lexical observation | Still nominates lexical observation; never a manipulation verdict |
| Act now! This is an example, not advice. | Nominates lexical observation | Still nominates it; quoted/recommended context remains unresolved |
| Buy the guide. Last chance today. | Nominates lexical observation | No within-unit association; deliberate cross-sentence coverage tradeoff |
| Install the viewer. Buy the pass now. The workshop is today. | Includes unrelated Install/today positions in support | Finding supports Buy/now only; other measurements retained |

These are developer-authored controls, not independently labeled samples or an
estimated false-positive rate. Ordinary persuasion and emergency directions can
still contain this lexical pattern. The method is not an MT intent classifier.

## Executed evidence

- One final adjacent pytest run: **108 passed in 0.93 seconds**. Existing language,
  verifier-identity and quantitative-consumer checks plus the new locality cases.
- Existing actual CLI verifier: **22/22 controls pass on Darwin arm64**, with its
  source inventory unchanged during execution. This includes legitimate emergency
  urgency, unrelated-unit refusal, unresolved cross-sentence association, authority,
  hedge and the existing separate package/credential-flow tools.
- New actual CLI control confirms a completed no-supported-pattern result retains
  unpaired measurements without echoing input text. No input is executed.
- Full suite, Linux execution, browser/native builds, physical devices and independent
  accuracy were not run or inferred in this lane. The source-bound route inventory
  and broad Linux receipts need normal PM integration revalidation; historical
  evidence is not relabeled current.

[Execution receipt](../runs/2026-11-16-mt-urgency-locality.json) ·
[Actual existing consumer](../runs/2026-11-16-mt-urgency-consumer-macos.json) ·
[Architecture and risks](mt-urgency-locality-plan.md) ·
[Published method](language-observations.md).

## Scope contribution and remaining work

| Original requirement | Before | After this lane | Owner and remaining acceptance |
| --- | --- | --- | --- |
| F-019a urgency framing observation | 80% | 80% | Codex MT owner: remaining grammar/use-versus-mention/context evaluation, independently labeled categories and accepted MT integration |
| T-MT parent tag | 20% | 20% | Codex MT owner builds the independent method; actual human reviewers and product acceptance retain their own gates |
| F-019b choice framing and F-019c authority appeal | Unchanged | Unchanged | Separate methods; success here transfers no validation credit |

No whole original requirement is closed. Global scope records and counts are not
modified by this isolated lane. `tags` stays empty, `intent_established` and
`independent_accuracy_evidence` stay false. No account, model, service, collection,
network operation or new price gate is introduced.

Next: collect a declared, representative and blinded context set distinguishing
urgency, persuasion, safety advice and quoted discussion; evaluate actual grammar
and cross-sentence association before selecting another method revision. The
current deterministic unit-local observation can be run independently today and
can fail without becoming a prerequisite for PS, PII or another MT component.
