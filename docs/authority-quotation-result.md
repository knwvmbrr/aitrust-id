# Authority quotation candidate — engineering result

Completed by Codex's MT evidence engineering lane on 2026-11-18 from
`7b5ab10df9c91a4134d0d655c315b13df890e422`, in an isolated branch.

The job is an optional executable method for inspecting authority phrases in
supported quotation context. The old method remains unchanged. The new candidate
is `ascii-quoted-authority-observations/1.0.0`; [operation and boundaries](authority-quotation.md)
are published beside its [architecture plan](authority-quotation-plan.md).

| Authored example | Existing authority behavior | New opt-in candidate |
| --- | --- | --- |
| `The training example says "Experts agree".` | One ordinary unmarked finding. | One retained quoted phrase; zero outside markerless phrases. |
| `Experts agree; the quoted example is "https://example.invalid".` | Quoted URL marks the outside phrase; zero ordinary findings. | One outside markerless phrase; quoted URL is not borrowed. |
| `Experts agree; see https://example.invalid.` | One marked phrase. | One outside marked phrase; existing supported behavior retained. |

The [immutable receipt](../runs/2026-11-18-authority-quotation-candidate.json)
preserves the initial mismatches against the proposed context contract and the
current exact executable controls. The legacy behavior is not retrospectively
relabeled as a failure of its published method: this is a new opt-in meaning.

Verification completed:

- **114 focused tests passed** in the candidate, legacy language and existing MT
  workflow suites. These cover normalized identity and exact spans, quoted-marker
  locality, mixed units, input and count limits, fixed refusal diagnostics,
  filesystem privacy, optional import failures and continued legacy operation.
- **22 actual CLI controls passed**, including old behavior, new context outcomes,
  private NFC-bound details, mode 0700/0600 output and refusal to overwrite.
  The CLI verifier compared source hashes before and after execution.
- No network is used by the method. A socket-refusal unit control passed, but
  this run did not test an isolated Linux network namespace.

This delivers a bounded software component toward F-019c/T-MT, not either full
requirement. It does not settle a quotation's endorsement, semantic attribution,
negation, coercion or manipulation. It has no independent accuracy measurement,
new tag, production MT assertion or public endpoint. Existing MT selection and
all global scope percentages remain unchanged. Integrating a candidate into a
future tag requires separate reviewed method adoption and the tag's own evidence
and acceptance gates.
