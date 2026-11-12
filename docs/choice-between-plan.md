# Observe caller-selected “between A and B” wording

## Job and outcome

Extend the existing independent MT research component with one paired-marker
form. A person can inspect the exact `between` and `and` locations, two spans
they selected, and a separately nominated reference. This remains a literal
observation. It does not establish that the spans are discrete choices, that a
numeric range is a false dilemma, that an alternative works, or that someone is
manipulating the reader. The new form always has `proposed_signal: null`.

## Architecture and compatibility

Keep the bound v1 input context, NFC offsets, corpus identity, private-file
access, output privacy and all existing refusal controls. Add `between: and` to
the existing paired-marker parser; preserve the three earlier constructions and
their fields. Version the research result profile to 1.2.0. No service endpoint,
network request, model, dependency, production signal or MT tag is added.

## Risks and gates

Ranges, quoted examples and legitimate safety choices share this syntax. Retain
those as explicit controls and suppress a proposed signal for this construction.
Reject mixed connectors and embedded-word/confusable prefixes. Verify literal
locations, NFC Unicode offsets, negation disclosure, unchanged old forms,
all-context-before-output refusal and the real private CLI on Mac and isolated
Linux. Development examples do not provide independent MT accuracy.

F-019b stays open at its existing milestone: broader grammar, automatic
selection, negation/quotation interpretation, useful alternatives, freshness,
independent contextual errors and accepted MT integration remain separate.
