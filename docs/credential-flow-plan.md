# Credential-to-network flow — implementation plan

Implementer: Codex. Scope: F-012. The legacy Semgrep/tag method remains a proposal.
This independent reference observation uses Python's built-in syntax tree, not a
regular expression that merely finds a secret path and a network call together.

Accept explicitly supplied straight-line Python source only. Never import or run
the program. Recognize selected literal credential paths and secret environment
keys, track their values through supported assignments/containers, and identify
when those values are arguments to an imported requests HTTP sink. Report both
the secret-read and sink-call positions. Unrelated reads/calls and overwritten
values must not become findings. Unknown transformations, branches, functions,
dynamic paths/URLs, unknown aliases and unsupported syntax fail explicitly; no guessed
negative result is allowed. Use/mention classification is outside this program
analysis profile and must precede any eventual PS mapping.

Risks: names of files/variables do not prove they contain live credentials. A
network sink can be legitimately owner-authorized. A static flow is not proof of
the program executing, an attack or intent. This component returns no PS tag and
uses no network, environment values, files named by the program or model. Its
source/subject identity and limits are explicit. The original full PS enhancement
and held-out acceptance remain open, independent of this component's controls.

Acceptance: direct and assigned flows, import aliases, data overwrite, unrelated
read/sink, shadowed sink, UTF-8 AST offsets, comments/literal mentions, unknown
transform/branch refusal, bounded hostile input, actual CLI and isolated Linux.
