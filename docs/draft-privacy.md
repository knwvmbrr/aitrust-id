# Check a draft before sharing

The local privacy preview looks for supported personal details in text you
choose. It gives you a short reminder to review the draft. It does not send to
a chat app, change your file, intercept a browser send, or collect research data.
Recognition can miss details and flag ordinary text. No finding is a privacy
clearance. English is the current development target.

## Use it

First follow [one-command Linux setup](https://github.com/knwvmbrr/aitrust-id/blob/main/docs/open-validation-path.md). Save a draft as
`draft.txt`, then run from the downloaded repository folder:

```sh
LOCAL_STATE="$HOME/.config/aitrust-id/local-stack"
"$LOCAL_STATE/checker/bin/python" scripts/aitrust.py privacy draft.txt --env-file "$LOCAL_STATE/runtime.env"
```

You can also supply text on standard input using `-`. Review the original
yourself, make any edits, and check again before you decide to share it. This
tool does not press Send or copy a redacted replacement into another app.

The command talks only to the existing authenticated `127.0.0.1:8787` gateway.
Its explicit privacy mode runs the local redactor without calling PS. An
evaluator outage cannot disable this selected route; redactor or authentication
failure makes it unavailable. `/healthz` and `doctor` still describe the full
stack, so an evaluator outage can make them fail while privacy mode works.

Existing installations need the current gateway and CLI source. Downloading a
new CLI does not update a running container. Stop your owned installation and
create a fresh setup in a new private state directory, or use the documented
manual rebuild path. Never replace credentials or a different running stack.

## Optional details and automation

Add `--json` to export the versioned observation. The export contains no draft
text, but fingerprints, categories and times can still link information. Share
it only deliberately. `--fail-on-finding` returns 2 when supported detections
are present, 0 for no finding, and 1 when no valid check is obtained. Neither 0
nor 2 establishes recognition accuracy or complete privacy protection.

A complete supported record can be [repeated with its private original input](https://github.com/knwvmbrr/aitrust-id/blob/main/docs/assertion-replay.md).
The replay selects privacy mode explicitly and cannot silently add PS. Old
records with missing inputs, identities or different sources stay unavailable.

## Verify your own installation

```sh
"$LOCAL_STATE/checker/bin/python" scripts/verify-draft-privacy.py --env-file "$LOCAL_STATE/runtime.env"
```

The basic check exercises real HTTP and CLI behavior. The optional
`--setup-state "$LOCAL_STATE"` test temporarily stops and restarts **only the
owned setup's** evaluator and redactor. It verifies independence and recovery,
requires an installation that matches the source, and interrupts checks on that
installation while it runs. The full replay command requires the documented
verification environment, which includes replay dependencies; the ordinary
privacy CLI needs only the hash-locked checker environment.

This is a manual privacy-preview enhancement, not released PII_OUTBOUND browser
interception. No new tag code or confidence threshold is adopted. Independent
PII recognition, physical-device and human accessibility acceptance stay open.
