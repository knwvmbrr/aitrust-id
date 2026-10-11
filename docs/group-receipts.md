# Keep one shared record. Everyone signs for themselves.

This free, optional tool lets a group sign the same file record with separate
keys. Each participant keeps their own private key. You can verify all the
signatures offline. It works with two to sixteen keys, including a four-person
team; different keys do **not** prove there are different people.

Nothing is uploaded. No account or payment is required. You can use the personal
checkers without making or signing any receipt. This is a development integrity
tool, not a PA, FA, IV or independently validated authorship tag.

## 1. Choose the group

Requires Node 24 on Linux or macOS. Each participant creates their own key using
[the local key instructions](offline-receipts.md). Exchange **public.pem only**
through a channel your group trusts. Never send anyone your private key.

One organizer selects those public keys and the exact final file:

```sh
node scripts/group-receipt.cjs roster roster.json alice-public.pem bob-public.pem carol-public.pem dev-public.pem
node scripts/group-receipt.cjs create final.txt roster.json manifest.json
```

These are example filenames; select your actual files. The output directory must
already exist, use its real path, and choose new filenames. Outputs are private
0600 files. The roster is your trust selection; an attached key list cannot make
an unknown sender trustworthy.

## 2. Each participant chooses to sign

Send participants `manifest.json` and the exact file. Before signing, confirm the
artifact SHA-256, byte count and selected group keys in the manifest. A signature
means the selected key signed **this record**; it makes no claim about who wrote
what. The declared window defaults to one day on an unverified local clock.

Each willing participant runs this on their own computer:

```sh
node scripts/group-receipt.cjs sign manifest.json "$HOME/aitrust-receipts/private.pem" my-signature.json --agree
```

Then return `my-signature.json`. Keep the private key. Without `--agree`, no
signature is created. There is no forced-signing mode.

## 3. Keep the group record

The organizer collects the separate signatures:

```sh
node scripts/group-receipt.cjs assemble manifest.json roster.json group.json alice-signature.json bob-signature.json carol-signature.json dev-signature.json
node scripts/group-receipt.cjs verify group.json roster.json final.txt
```

Assembly checks every selected signature against the same manifest before saving
anything. Missing, duplicate or additional signers, different records, changed
files, untrusted keys and unsupported algorithms refuse the operation. Existing
outputs are never overwritten. An optional [independent timestamp](independent-timestamps.md)
can be kept separately for the final `group.json`; it does not change its signatures.

## Read the result

- **All signatures verified:** every selected key signed the same record.
- **Artifact matched:** the file’s bytes match that record.
- **Window:** current, not yet current or expired under the verifier’s local clock.
- **Revocation unchecked:** no fresh revocation evidence was supplied.
- **Authorship and distinct people unestablished:** keys do not establish either.

Exit 0 verifies integrity within the declared window. Exit 3 verifies the record
but its window is expired or not yet current. Exit 2 refuses invalid inputs,
trust, signatures, unsafe files or unavailable prerequisites. No certification
or tag is issued, even on exit 0.

The record reveals a group of key fingerprints and a hash of a known file. Share
it only when everyone agrees to that disclosure. The tool cannot establish
identity, truthful authorship, key custody or freedom from coercion. Institutional
anti-coercion, recovery and fresh revocation remain separate unfinished work.

Run `node --test tests/group-receipts.cjs` for the two-/four-/sixteen-key,
mixed-algorithm, separate-signing and refusal controls. Synthetic signers test
cryptography; they are not evidence of human authorship or independent accuracy.
See the [architecture and risk plan](group-receipt-plan.md).
