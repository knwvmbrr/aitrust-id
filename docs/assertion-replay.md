# Reproduce a local-service check

A replay asks: does the **same implementation**, given your original input,
produce the same findings? It does not prove accuracy, independent agreement,
authorship or signature trust. This guide is for new, unsigned local-service
records carrying `local-text-pipeline/v1` preprocessing metadata.

1. In the browser tag dialog, open **Reproduce this check**. Read the metadata
   notice, check the permission box, then choose **Download replay record**.
   All findings for that response are included; no response text is included.
2. Keep that JSON file private. Save the exact original response separately as a
   UTF-8 text file. Restrict the text file to your account (`chmod 600 original.txt`).
   Do not paste or upload either file into a public issue.
3. From a downloaded checkout, use Python 3.12 and an isolated environment:

   ```sh
   python3.12 -m venv .replay-venv
   .replay-venv/bin/python -m pip install --require-hashes \
     -r services/gateway/requirements.lock -r eval/requirements.lock
   ```

   Start the matching authenticated local stack using the [quick start](../README.md).
   Rebuild it after updating source. Read the matching source commit, models and
   pipeline identity in the record before replaying.
4. Put only your existing local gateway token in an owner-only regular file,
   permission 0400 or 0600. Do not pass the token as a command argument or put it
   in Git. A `runtime.env` file containing multiple settings is not a token file.
5. Explicitly select local replay:

   ```sh
   .replay-venv/bin/python scripts/replay-assertion.py ai-trust-id-replay.json original.txt \
     --local-gateway --token-file /private/path/to/local-token
   ```

The command sends the original text only to the existing authenticated
`127.0.0.1:8787/v1/evaluate` service. Proxies, redirects and assertion-supplied
URLs cannot select a destination. It creates no intake, database record or local
copy of your input. Your original files and any downloaded copies remain yours
to protect or delete. A compromised local host remains outside this guarantee.
The small JSON output contains no text, credentials, input fingerprint or paths.

| Result | Exit | Meaning |
|---|---:|---|
| `matched` | 0 | Same method/preprocessing identities, subject hash/length, tags and abstentions |
| `mismatch` | 1 | Identical method and subject, different findings; retain privately for investigation |
| `input_mismatch` | 2 | The evaluated redacted subject differs; check the original input |
| `unavailable` | 3 | Service, dependencies or matching method/history unavailable |
| `invalid` | 4 | Input/record/identity/credential permissions fail the contract |

UUID, capture time and latency naturally vary and are excluded from the finding
comparison. Redaction/model/configuration, normalization, source and policy hashes
must match. Both command observations and procedural PII redaction are compared.
A digest identifies selected metadata; it is not a signature or trusted attestation.

Older records without preprocessing identity cannot be reconstructed by guessing.
On-device website downloads use a different record format and do not carry this
service's redactor identity; use their matching offline checker package to rerun
the text. This command refuses those records. The signal catalogue preserves
historical/proposed IDs but does not manufacture missing inputs or implementations.

## Identity encoding

`protocol/replay_identity.py` defines bounded typed identities. First validate and
normalize the object through its versioned model, including numeric constants and
all default values. Canonicalize the `{version, configuration}` object with sorted
keys, ASCII JSON escapes, compact separators and finite numbers, then SHA-256 the
bytes. Model validation checks each identity digest. Installed distribution RECORD
hashes identify installation metadata; they do not themselves verify every runtime
package file. English model assets separately pass the pre-load integrity check.
Current consumer checks validate metadata shape/consistency; the gateway and replay
command check the digest. No independent detector or security certification follows.
