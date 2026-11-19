# Independent Linux tag development lab

The user requested continuous virtual research and testing on 18 November 2026.
Development does not require thousands of recruited users for each engineering
change. Linux runners can execute controlled examples, failure injection,
regressions and protocol compatibility repeatedly. Independent accuracy uses
separate accepted labels, sampling and release gates; repeat runs of the same
examples are not new independent observations.

## Implemented automation

The `independent-tag-lab` workflow runs three separate Ubuntu 24.04 / Python 3.12
jobs: PS standalone/batch controls, MT context/evidence controls and NF/FI
reference-mapping contracts. Jobs do not cancel each other when one fails. At
most two run concurrently; each has a twelve-minute deadline. It runs on relevant
pull requests, on manual dispatch, and daily at 07:10 UTC after this workflow is
merged to the default branch. Reports and JUnit results remain artifacts for
fourteen days. A public hosted Linux runner is an actual virtual environment,
not an iPhone emulator or an independent human reviewer.

The optional MCP tools have their own daily Linux lane at 07:40 UTC. Existing
network-isolated image-manifest/declaration checks run daily at 08:00 UTC. The
existing isolated privacy-engine cohort workflow runs weekly Monday 08:20 UTC,
reflecting its heavier model/container setup. All can be dispatched manually.
Nothing starts Docker on the owner's Mac. Scheduled workflows have no guaranteed
start time and may be disabled by GitHub on inactive repositories; check actual
run results before claiming a run occurred. No standing paid server is ordered.

These lanes use existing pinned locks and authored/public development controls.
The NF/FI contract lane does not download an NLI model or claim to measure its
semantic accuracy. Image declarations are signed statements, not proof that an
image is authentic or human-made. Privacy cohorts remain development evidence.
Failures in one lane must not become a finding or clear another tag.

## Reproduce in an independent Linux VM

Clone the public source at an exact commit. Create a fresh Python 3.12+ virtual
environment, then install `eval/requirements.lock` using pip's `--require-hashes`.
Run the exact commands in `.github/workflows/tag-lab.yml`; they need no account,
private corpus or AI provider key. MCP and image SDKs use their own separate
hashed environments; the privacy engine has its own isolated container. Keep
logs and method/source versions. Do not call a dependency-installed shell an
OS-level no-egress sandbox: the image and privacy workflows enforce their own
explicit runtime network restrictions.

Future research candidates get a versioned job, input domain, expected failure
behavior and separately adjudicated test examples. Generated labels are proposals
until accepted under the evaluation policy. Do not automatically promote a
candidate, change a public threshold, alter a production tag or train on private
content because a daily workflow passes.

## Government and security-sensitive use

Local inspectable software, small independent checks and versioned evidence may
support procurement evaluation. No government approval, clearance, classified
handling, FedRAMP authorization or regulatory compliance is granted by a Linux
run. The initial virtual lab accepts only public or invented material. Do not put
classified, controlled, customer-confidential or private participant material in
public GitHub jobs or artifacts. An organization's authorized environment, data
rules, supply chain and contract must be reviewed separately before real use.
