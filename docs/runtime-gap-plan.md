# First-tag live findings: implementation plan

The 2026-10-08 live feedback found a real fetch-and-execute blind spot and no
capture anchor on the observed ChatGPT page. Healthy containers and successful
synthetic fixtures do not establish compatibility or independent accuracy.

## Changes and risk boundaries

1. Keep PS as the development tag and preserve the existing v2 methods. Add
   separately versioned lexical observations for direct command and process
   substitution into supported execution commands. No command is fetched,
   decoded, or executed by the detector. New examples come from the live review,
   with download-only, display-only and warning counterexamples. Lexical matching
   remains bounded; it is not a universal shell interpreter or a scam verdict.
2. Capture the whole assistant body using the live-observed attribute
   `data-markdown-text-style="assistant-message"`. The observed response identity
   is carried by its `data-chatgpt-selection-message-id` ancestor; the assistant
   heading also carries `data-conversation-role="assistant"`. Exclude toolbar
   descendants marked `data-markdown-copy="exclude"`, hidden text and extension
   UI. Keep older explicitly assistant-owned anchors where supported; a generic
   conversation-turn container must not be accepted without role filtering.
   Do not rely on hashed CSS names. Reused DOM hosts must invalidate requests
   when message identity changes, even if text is unchanged. Ambiguous ownership
   must not capture user input. A visible status must distinguish absent capture
   from a successful no-finding result. These attributes were inspected in the
   live page's Elements tree; that observation does not verify extension runtime.
3. Emit explicit abstentions for recognized disabled evaluator candidates. A
   disabled capability has no numeric threshold; schema represents its floor as
   null. Unknown/unadopted candidate codes fail the upstream contract explicitly
   instead of disappearing. Only the trusted redactor can assert PII_REDACTED.
4. Execute Python boundary/HTTP/schema checks, changed-DOM browser cases,
   out-of-order and stale-result checks, and the rebuilt real local pipeline.
   Use the existing live Homebrew conversation to check compatibility if native
   browser access permits it. Synthetic checks never stand in for that result.
5. Refresh neutral role ownership and allowlisted site references. Preserve old
   evidence as historical observations; new results identify the new source.

Independent holdout labels, human accessibility and release-policy decisions
remain necessary. No new endpoint, taxonomy adoption, universal accuracy claim,
external publication or private-content export is part of this change.

## Reconciliation after writer handoff

The engineering lead owns the evaluator, gateway, assertion schema and extension
implementation pass. The broad `sig.fetch_execute.v1` prototype is retained in the
method history but withdrawn from runtime: it matches a fetch prefix without
establishing stdout delivery. Consolidated substitution methods use new IDs and
full bounded spans, with output-to-file and quote guards. Single quoting has
different effects at different evaluation layers: a shell `-c` or `eval` can
interpret substitution passed literally by the outer shell, while a single-quoted
Python `-c` argument does not perform shell substitution. A local fake-curl probe
records this distinction without making network requests. Conflicting historical
fixture labels remain visible and are explicitly superseded in development checks;
this does not constitute independent adjudication.
