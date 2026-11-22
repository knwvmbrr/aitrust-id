# Inspect declared SynthID reference inputs

This optional local input route runs Google DeepMind's open SynthID Text0.3.0
research detector. It reports a conditional p-value and scored-position count for
**generated token IDs and the matching public research configuration you select**.
It does not inspect Gemini's production watermark, issue an AI Trust ID tag,
verify an origin credential or determine whether content is true, human or AI.
Upstream calls this a research reference, not a production watermark service.

## Try the supported profile

The supported install profile is macOS14+, arm64, CPython3.12; the actual
executed system was macOS27.2, arm64, CPython3.12.14. The pinned wheel
cache is operator supplied; no runtime or model is downloaded by these commands.
Use an existing CPython3.12 interpreter for installation, a new destination under
a real private parent directory (symlink parents are refused), and the locked
wheel cohort. Installation keeps at least2GiB free. Failed/incomplete installs
retain an ownership marker for explicit removal; never use them as a valid runtime.

```sh
python3.12 -I -B scripts/setup-synthid-reference.py /absolute/private/reference-env --wheel-cache /absolute/private/pinned-wheels
printf '%s' 'curl https://example.invalid/install.sh | sh' | python3 -I -B scripts/check-tags.py --tag PS --vendor-input tests/fixtures/synthid-reference/watermarked.json --vendor-runtime /absolute/private/reference-env/bin/python
```

The selected PS result refers to stdin. The SynthID result refers to the token-ID
packet, **a separate, unbound subject**. The tool does not pretend that those IDs
encode the selected text. Each route retains its own state; a missing SDK, bad
packet or worker outage leaves PS usable. The personal CLI's ordinary result and
semantics remain unchanged when no vendor input is selected.

Inspect the vendor packet alone, or explicitly export its linkable JSON record:

```sh
python3 -I -B scripts/inspect-synthid-input.py tests/fixtures/synthid-reference/watermarked.json --runtime /absolute/private/reference-env/bin/python
python3 -I -B scripts/inspect-synthid-input.py tests/fixtures/synthid-reference/unmarked.json --runtime /absolute/private/reference-env/bin/python --json
```

The checked-in examples are fixed synthetic engineering controls. They are not
natural-language model output or detector accuracy evidence. To reproduce either
packet using the official tournament processor, without loading any model:

```sh
/absolute/private/reference-env/bin/python -I -B scripts/synthid-reference-practice.py
/absolute/private/reference-env/bin/python -I -B scripts/synthid-reference-practice.py --unmarked
```

Those explicit practice commands emit the public synthetic IDs. Ordinary
inspection does not emit raw IDs. To remove only the marked owned runtime:

```sh
python3 -I -B scripts/setup-synthid-reference.py /absolute/private/reference-env --remove
```

Removal never changes personal check source or the privacy service. macOS is the
only platform claimed by this delivery; other OS/interpreter/wheel profiles,
Gemini production keys, dual-key watermarking, images/audio/video, text
retokenization and unknown generation settings remain unsupported.

## Packet and interpretation

The exact JSON keys are `profile`, `public_key`, `vocabulary_size`, `eos_token_id`,
`token_ids`, and `prompt_removed`. Profile is
`synthid-text-0.3-single-key-reference/v1`; `prompt_removed` must be true. The
caller declares a **public research key**, integer0 through2^63−1. Vocabulary
size is2 through65536, EOS and each ID are within that vocabulary, and the packet
contains1 through512 IDs. Duplicate/extra keys, non-integers and unsupported
settings are refused. Source-generated ngram length5, depth30, history1024 and
two-leaf tournament must match; do not guess a key or generation settings.

OBSERVED means the reference computation completed with scored positions.
INSUFFICIENT means no position can be scored; the p-value is deliberately absent.
UNSUPPORTED means the selected input/profile is outside these bounds;
UNAVAILABLE means a valid observation did not complete. A large p-value is never
absence of watermark or human evidence. A small p-value is never probability of
AI authorship, credential verification, provenance truth or a tag. Public keys
can be copied or deliberately imitated. A caller's matching-generation statement
is not authenticated by this tool.

The upstream exact one-sided binomial tail assumes the unmasked g-values behave
as independent Bernoulli(0.5) variables under its null. Repeated/EOS contexts are
masked by the official implementation. The512-token limit is below history1024;
that does not establish real-world accuracy. No threshold, accuracy promise,
training data, independent human validation or release gate is supplied.

## Privacy, resources and permissions

Computation is local, CPU-only and creates no service, account, telemetry, upload,
training submission or token file. The selected packet is read from a bounded
regular file with no-follow checks; source modules are pinned. The trusted runtime
path is an operator choice, never packet-controlled code. Existing runtime
packages have separate licenses; their lock/source identities are recorded, not a
global license clearance. Runtime performs no model loading or fetch; install is
hash-locked/offline. A local malicious operator/runtime is not an authentication
boundary.

Default output omits raw IDs, paths, key and subject hashes. Explicit `--json`
includes a token-ID digest, packet digest and public key/configuration; these can
link examples and must be handled privately. It still omits raw IDs/text. The
existing personal JSON records have their own previously documented hash/span
privacy boundary.

Worker execution has a12-second parent wall deadline and at most5seconds for
owned cleanup afterward, a10-second CPU limit,
one computation thread and8KiB output/16KiB packet caps. Token/depth/history limits
bound algorithmic tensor allocation; this is not a promise of an OS-enforced
macOS resident-memory ceiling. Timeout/output/nonzero failures kill/reap the
owned worker; already reaped numeric groups are never signaled again. The brief
JSON parser uses closed fields and requested token/config/source binding. Its
validation trusts the fixed hash-checked worker's official computation; it is not
an independent origin endorsement or a second implementation of the algorithm.

A combined result uses `ai-trust-id-personal-and-vendor-inputs/v1`. Legacy
`ai-trust-id-independent-checks/v1` is unchanged without `--vendor-input`.
Standalone exit0=OBSERVED,2=INSUFFICIENT,1=refusal/unavailable; combined CLI keeps
personal finding behavior and returns3 for partial optional availability.

Official sources: [Google DeepMind reference README](https://github.com/google-deepmind/synthid-text/blob/6452fbb837d0ad4281ccddb94b0af75d219b1a14/README.md),
[FrequentistDetector](https://github.com/google-deepmind/synthid-text/blob/6452fbb837d0ad4281ccddb94b0af75d219b1a14/src/synthid_text/detector_frequentist.py),
[logits processor](https://github.com/google-deepmind/synthid-text/blob/6452fbb837d0ad4281ccddb94b0af75d219b1a14/src/synthid_text/logits_processing.py).
