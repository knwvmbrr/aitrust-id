# Check a receipt against a selected revocation log

A signature tells you which key signed a record. This optional tool adds a
separate question: **does your selected key authority's saved log record that key
as revoked, and is that saved information recent enough for your chosen policy?**
It runs locally without an account, network connection or automatic sharing.
Existing receipts and group tools continue to work independently.

This is a selected offline log component, not a running public transparency log.
It does not verify identity, human authorship or the accuracy of any tag. A fresh
snapshot means “not recorded revoked as of this selected checkpoint,” never “the
key cannot be compromised” or “globally/currently valid.” Local clocks are not
independently verified. No PA, FA or IV tag is issued.

## If you manage your own keys

Use a **separate authority key** and an existing owner-only directory outside the
repository. Create it with the existing receipt key generator, or use your own
supported Ed25519/P-256 authority. Keep the private key private. This authority
represents your chosen key policy; it does not identify or certify you.

From your downloaded source directory:

```sh
node scripts/receipt.cjs keygen Ed25519 /your/private-directory/authority.pem /your/private-directory/authority-public.pem
node scripts/revocation.cjs create /your/private-directory/authority.pem 3600 /your/private-directory/log-1.json
```

The example gives the checkpoint a one-hour declared window. **This is an example
policy, not an adopted protocol or a measured security threshold.** To record a
revocation, name the device's public key; do not send the private device key:

```sh
node scripts/revocation.cjs revoke /your/private-directory/log-1.json /your/private-directory/authority.pem /your/private-directory/device-public.pem 3600 /your/private-directory/log-2.json
```

A `refresh` command signs a new checkpoint with the same cumulative revocations.
Every new file preserves all prior checkpoints. Revocations cannot be removed;
there is no overwrite or silent reset. A lost/compromised authority and key
recovery need their own trust decision, not a newly generated key pretending to
be the old authority. Public witnessed distribution/recovery remain unimplemented.

## If you verify a receipt

Obtain the authority public key and checkpoint through your own trusted channel,
separately from the receipt. Confirm which authority you are choosing. Never treat
a public key included with an untrusted receipt as automatically trusted.

Choose a maximum age and maximum checkpoint lifetime; pin the known checkpoint
explicitly. This example permits ten-minute-old status and a one-hour declared
lifetime. It does not establish a universal safe interval:

```sh
node scripts/revocation.cjs policy /your/saved/log-1.json /your/saved/authority-public.pem 600 3600 /your/saved/policy.json --trust-checkpoint
node scripts/revocation.cjs verify-receipt /your/saved/receipt.json /your/saved/device-public.pem /your/saved/artifact.txt /your/saved/log-1.json /your/saved/authority-public.pem /your/saved/policy.json
```

For a group record, use `verify-group` and the separately trusted roster in place
of the single receipt and device public key. All required signatures and every
selected key's status are checked. One revoked/unknown key prevents continuation.
Use `-` in place of the log filename to report unavailable status explicitly.

The JSON result separates receipt integrity, artifact binding, expiry and each
key's selected-log status. Exit `0` permits continuation **under your selected
policy only**. Exit `3` means the receipt window or status is insufficient:
revoked, unavailable, future, expired or stale. Exit `2` refuses malformed or
untrusted input, altered history, rollback or unsafe file permissions. None of
these exits is an independent authorship, identity, accuracy or certification result.

## What this protects, and what remains open

Canonical signed complete history and a separately pinned checkpoint detect
changes, missing history, rollback and removal of earlier revocations. At most
64 checkpoints and 128 revoked keys are accepted, within the existing 256 KiB
record bound. Exhaustion refuses extension; do not discard history to reset it.
Supported key algorithms are Ed25519 and P-256/SHA-256. Windows-specific key/file
permissions are not supported by this Unix CLI.

A compromised authority could omit a revocation or sign conflicting histories.
This tool does not contact witnesses or check completeness against other people.
A long-disconnected verifier has unknown current status. Local clock manipulation,
key custody/recovery, public distribution and independent witnessing need separate
controls and acceptance. F-125 remains open for a publicly witnessed transparency
log and distribution. F-126 is the functioning freshness-model component: it
reports the chosen limits, age, insufficient evidence and conditional results.
Completing that model does not complete F-125, authorship validation or RFC adoption.

The log contains public-key fingerprints and authority-local times. These can
link records and devices. Save/share only by deliberate choice; there is no text,
contact information, event stream, reason free text, automatic collection or new
project endpoint. Private keys are read with owner-only permission checks and
never printed. Outputs are new owner-readable files, never existing-file overwrite.

Run the repeatable engineering checks:

```sh
node --test --test-reporter=tap tests/offline-revocation.cjs
```

The synthetic checks prove these implementation contracts. They do not constitute
actual outside-user key recovery, a public transparency service or a validated tag.
