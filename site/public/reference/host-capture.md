# Check a file while you work

HOST is an optional **foreground file adapter for macOS and Linux**. You choose
one private text file. It notices saved changes and, if you select PS, checks
each changed version using the existing local PS development method. It does
not execute the file, edit it, send it anywhere or require Docker or an account.
It is not screen, clipboard, keyboard, browser-history or whole-computer monitoring.

## Start with a test file

Use Python 3.12 or newer from an inspected source checkout. From its root:

```sh
mkdir -m 700 "$HOME/aitrust-host-example"
printf '%s\n' 'A plain answer to check.' > "$HOME/aitrust-host-example/answer.txt"
chmod 600 "$HOME/aitrust-host-example/answer.txt"
python3 scripts/host-capture.py --fingerprint --tag PS
```

The last command prints JSON. Copy its `sha256` value into the command below.
The fingerprint identifies **these source bytes**, not their safety, publisher
or accuracy. Keep the terminal visible and run:

```sh
python3 scripts/host-capture.py \
  --root "$HOME/aitrust-host-example" --file answer.txt \
  --source-sha256 PASTE_THE_SHA256_VALUE_HERE \
  --consent-local-text-only --tag PS
```

Edit and save `answer.txt` using your editor. It must remain an owner-private
UTF-8 regular file, not a link. The adapter checks changed saved versions; it
is not a complete event history and can miss intermediate edits between reads.
A PS finding means a supported command pattern was found. No finding is **not**
a safety clearance. PS remains a development checker awaiting independent release
validation. HOST does not redact personal information.

Type a letter below and press Return:

| Key | What happens |
| --- | --- |
| `p` | Pause immediately: cancel pending analysis and stop reading the file. |
| `c` | Continue with a fresh capture of the current version. |
| `r` | Cancel analysis, clear this session's optional captured metadata, and stay paused. |
| `d` | Delete this session's verified generated metadata and stop. The input stays. |
| `q` | Stop; keep any explicitly requested metadata. |

Ctrl-C, Ctrl-Z, terminal hangup and ordinary termination stop the session.
Ctrl-Z exits rather than leaving a capture job that could resume with `bg`.
Foreground ownership is checked throughout capture and before publishing a
result; ownership loss stops the session without reading another saved version. Nothing
registers a startup task or restarts automatically. After a forced kill, retained
records describe an interrupted session; a session directory is never resumed.
A code-only temporary worker may remain after abrupt termination; it contains no
captured text. A parent-death watcher stops orphan PS work. This is not protection
against a compromised OS, administrator or other process using your account.

## Capture only, or keep metadata by choice

To observe file versions **without any detector**, omit `--tag PS` from both the
fingerprint and start commands. Capture-only has its own fingerprint and works
without the optional detector files. Failure of this adapter does not disable
the standalone PS checker or other independently available tag routes.

By default, no captured records are saved. Add an explicit **new** directory to
retain metadata, for example:

```sh
mkdir -m 700 "$HOME/aitrust-host-records"
# Add this argument to the start command above:
# --record-dir "$HOME/aitrust-host-records/session-1"
```

The parent must already be private; `session-1` must not exist. Events contain
session/revision IDs, source versions, timestamps, input hashes and sizes, plus
optional PS evidence spans and method metadata. They contain no original text or
input path. **Hashes, sizes and offsets can still link to private input.** Keep
them private; sharing them is your separate choice. No automatic upload occurs.
No consent to training, research, publication or organization monitoring follows
from using this tool.

The journal stops at 1,000 events, 2 MB per event or 20 MB total. A disk, permission,
quota or integrity failure stops the foreground session rather than silently
losing records. Reset/deletion only removes unchanged, verified files generated
by this session. Added or modified files cause refusal. If a stopped/interrupted
session needs removal, inspect its private folder and delete it yourself; the
tool will not reopen or overwrite an old session. Deletion here is logical, not
certified physical erasure of files, swap, editor history or external backups.

## Boundaries and updates

The directory must be mode 0700 and owned by you; the file must be mode 0600,
with one hard link. The filename is a simple ASCII name ending in `.txt`.
The adapter refuses repositories, known credential/configuration directories,
links, devices, pipes, binary/invalid UTF-8, empty input, control characters other
than tab/newline/carriage return, more than 80,000 bytes or 20,000 characters.
A missing or refused file produces Unavailable, never a no-finding conclusion.
Use a dedicated folder with only material you have permission to inspect.
A path allowlist is not a sensitive-content classifier.

Active file polling is every 250 ms; source identity is checked periodically and
again before publishing a result. This is not a latency or lossless-capture SLA.
Late results for a changed, paused or reset revision are discarded. Source changes
stop capture, even while paused. There is no hot update or automatic download.
Stop, inspect/authenticate the new source using the
[source-provenance guide](source-provenance.md), obtain its new mode-specific
fingerprint, then start again with explicit consent. Never run a downloaded
script merely because its adjacent fingerprint matches.

Windows, phones, native share extensions, privileged background agents, fleet
management, signed installers and independently reviewed enterprise deployment
are not provided by this adapter. The automated macOS/Linux terminal checks use
synthetic text; they are not human usability or independent security acceptance.
Personal detection stays free. No enterprise payment, hosted-service readiness,
certification or new tag assertion is implied.

## Run the engineering checks

```sh
python3 scripts/verify-host-capture.py --output output/verification/host-capture.json
```

These checks create real foreground pseudo-terminals and private temporary test
files. They exercise permissions, pause/reset/delete, changes, worker faults,
interruption and independence. Test fault injection exists only in the test
launcher; no runtime flag disables capture boundaries.
