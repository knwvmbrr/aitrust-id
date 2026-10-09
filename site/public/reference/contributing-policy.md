# Contributing

## Principles that are not up for negotiation

1. **No paid dependencies.** A component with a metered API is a rejected PR, regardless of
   how good it is. This project must cost a contributor nothing to run.
2. **No network egress at inference.** The anonymizer and evaluator run on an internal Docker
   network with no route out. CI runs the test suite with networking disabled — if your
   component needs the internet to evaluate text, it does not belong in the pipeline.
3. **No response content in assertion records or telemetry.** The personal workflow
   transfers text only to its authenticated local gateway and local redaction/evaluation
   services. Do not add automatic remote uploads or content persistence. Public assertions
   carry hashes and offsets; those metadata still deserve careful disclosure.
4. **Accessibility is a gate, not a follow-up.** See ACCESSIBILITY.md. Any serious or critical
   axe violation fails the build.
5. **A tag may not claim more confidence than its evidence supports.** If human annotators only
   agree at 0.6, your classifier does not ship at 0.9.
6. **No detection capability is ever withheld from an individual.** Every label, every signal,
   every piece of evidence is free and open, forever. Never add a feature flag that disables a
   label, a signal or an evidence panel for a free user. What an organisation pays for is
   administration of other people's installs — SSO, fleet policy, audit export, retention — not
   a capability a person would ever want.

**Nothing half-built ships.** If a feature cannot be finished to its written acceptance
criteria, leave it out of the release and say so in the README. Do not ship a stub behind a
flag.

## Changing the taxonomy

Open an RFC (`rfcs/0000-template.md`). It needs a detection basis, a labeled dataset, and
measured inter-annotator agreement. Opinions are welcome in the Town Hall; changes need
evidence. Without this discipline community tagging drifts into noise within a year and the
labels stop meaning anything.

## Commits

Sign off with DCO (`git commit -s`). No CLA — lower barrier, still gives provenance.

## Change accountability

Every source, public copy, policy, scope or operational-evidence change needs a
new attributed record before build/deploy/commit. [Changelog](CHANGELOG.md),
[policy and commands](docs/changelog-policy.md) and [scope completion ledger](docs/scope-progress.md)
have separate jobs: history, enforcement, and acceptance.
Use `npm run changelog -- --help`, then `npm run verify:changelog`; contributor
is required. Engineering passes never substitute for independent tag validation.
