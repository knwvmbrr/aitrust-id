# Use tags with an agent's output

Save an agent's answer with a signed source statement, then choose which supported
checks to run. Source information and tag findings stay separate. This free,
open-source command-line tool works without an account, gateway or local Docker.
For a single pasted answer, you can also [open PS on your device](https://aitrustid.com/#person/PS).

The supported adapter runs a **single-file Python stdio agent** that you select and
review. It supplies one UTF-8 task on stdin and receives one UTF-8 answer on stdout.
The agent has your OS user's file and network privileges. This is not a sandbox:
review the program and its dependencies before allowing it to execute. Credential
environment variables are not automatically forwarded. Temporary working files
are removed; an agent requiring a persistent working directory needs a different
adapter.

## Try invented practice data

Use macOS or Linux, Python 3.12 or newer and Node.js 22 or newer. Download the
repository and open a terminal in it. The adapter and optional PS use the existing
standard-library/runtime code; no additional Python package is needed to run them.
The development tests separately require the repository's hashed test dependencies.

Create a private folder outside every Git checkout:

~~~sh
AITRUST_AGENT_HOME="$HOME/AITrust-agent-practice"
install -d -m 700 "$AITRUST_AGENT_HOME"
python3 scripts/agent-output.py demo --output "$AITRUST_AGENT_HOME/input"
~~~

Read `input/agent.py` and `input/agent.json`. This is a **rule-driven practice
agent**, not a model. Its invented task produces a download-and-run example for
PS to inspect. Do not run the command printed inside that example. The generated
key is for practice.

Record the practice run and request PS:

~~~sh
python3 scripts/agent-output.py record \
  --program "$AITRUST_AGENT_HOME/input/agent.py" \
  --task "$AITRUST_AGENT_HOME/input/task.json" \
  --agent "$AITRUST_AGENT_HOME/input/agent.json" \
  --key "$AITRUST_AGENT_HOME/input/private.pem" \
  --public-key "$AITRUST_AGENT_HOME/input/public.pem" \
  --output "$AITRUST_AGENT_HOME/result" \
  --execute-reviewed-agent --check-ps
~~~

Read `result/answer.txt` in a text editor. Open `result/agent-output.html` for the
brief source caption and tag result. The default HTML omits answer text. To
deliberately include the answer in that private view, choose
`--include-output-view` when recording to a new destination. Every output folder
must be new; existing files are never overwritten.

Verify the saved bytes using the original descriptor and separately selected key:

~~~sh
python3 scripts/agent-output.py verify \
  --record "$AITRUST_AGENT_HOME/result/agent-source.json" \
  --answer "$AITRUST_AGENT_HOME/result/answer.txt" \
  --agent "$AITRUST_AGENT_HOME/input/agent.json" \
  --public-key "$AITRUST_AGENT_HOME/input/public.pem"
~~~

`MATCHED` means the signature matches your selected key, the descriptor matches
your selection and the answer bytes match the signed statement. It does not mean
the content is true or safe. Do not obtain the trusted key or descriptor from the
received result folder; that would let a sender supply their own authority.

## Connect your own agent

Review a single-file Python program that reads its task from stdin and writes
only its answer to stdout. Its output must be nonempty valid UTF-8, at most 20,000
Unicode codepoints / 80,000 bytes, without terminal control characters. The
default deadline is 10 seconds; `--timeout` permits an explicit 1–60 seconds.
The chosen program may perform its own network/file operations. This tool does
not establish its dependency integrity or contain a malicious program.

Use your own separately trusted Ed25519 key and a private descriptor. Required
fields are `profile` (exactly `agent-stdio/python-v1`), `agent_id` (your assigned
UUID version 4), `name` (1–64 ASCII letters/digits/spaces/underscore/dot/hyphen,
starting with a letter or digit), `kind` (`caller_declared_model_agent` or
`rule_driven_practice`), and `program_sha256` (SHA-256 of the exact program bytes).
The practice descriptor is a complete, runnable example.

Compute your own UUID and program hash with Python's standard-library
`uuid.uuid4()` and `hashlib.sha256()`. The kind describes your declaration; it is
not inferred or independently verified. For your own key pair, the existing
`node scripts/receipt.cjs keygen Ed25519` command accepts new private/public PEM
destinations in an owner-only directory.

Keep the descriptor, input and PEM files in owner-held directories with mode
`0700`; use mode `0600` for their files. Symlinks, hardlinks, shared permissions,
sensitive system/credential directories and Git checkout destinations are
refused. The public program is read as selected bytes and must match its pinned
hash. Source, key and destination checks happen before agent execution.

## What each file does

| File | Job |
| --- | --- |
| `answer.txt` | Exact private answer bytes. No redaction is performed. |
| `agent-source.json` | Signed source statement, byte identity and current recorder-source hashes. |
| `tag-check.json` | Separately requested PS result, not an origin or truth certificate. |
| `agent-output.html` | Private offline view with native keyboard controls and a compact finding tag. |

Omit `--check-ps` to record the agent without a tag checker. A failed optional
checker reports `UNAVAILABLE`; it does not erase the answer or source statement.
A failed agent run, wrong key, changed source or invalid output never creates a
success packet. An absent agent tool does not disable the standalone personal PS
checker. PS keeps its own current method, development status and release gate.

The signer states that the selected program returned these bytes. A verifier
can check that signed statement and the exact artifact binding. It cannot
independently prove the execution occurred, that AI generated the text, a person's
identity, benign intent, authorship or truth. Revocation and local-clock
authenticity remain unchecked. Unsupported/old recorder identities are refused
by this current profile. This does not adopt BT, FA or PA, or certify a tag.

The adapter never automatically uploads files or enrolls you in research. Your
selected agent has its own disclosure behavior. Saved answers, fingerprints and
handles may contain or correlate private information: review them before sharing.
No task text, command arguments, keys or agent stderr are saved to diagnostic logs.
