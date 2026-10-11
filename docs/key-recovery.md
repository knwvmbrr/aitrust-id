# Keep a private backup. Practice restoring it.

This optional tool protects a copy of your receipt signing key with a password.
It runs on your computer and sends nothing to us. Your personal tag checkers
work without a key or backup. Requires Node 24 on a Unix-like computer.

**Keep three things:** the encrypted backup, its password, and your separately
saved public key. Put the password in your password manager. Keep a second
private copy of the backup on a separate device you control. Never post these
files in a community report or repository. The backup's fingerprint can link
your receipts, even though the signing key is encrypted.

## Save your key

First create your key using the [receipt guide](offline-receipts.md). Then run
these commands from the downloaded repository. Use your actual file locations.

```sh
node scripts/key-backup.cjs backup "$HOME/aitrust-receipts/private.pem" "$HOME/aitrust-receipts/key-backup.json"
node scripts/key-backup.cjs check "$HOME/aitrust-receipts/key-backup.json" "$HOME/aitrust-receipts/public.pem"
```

Choose a strong, unique password of at least 12 characters. The terminal asks
you to enter it twice, with no characters shown. Length alone does not make a
password strong. Save it separately in your password manager. `check` asks for
that password and confirms the backup matches your saved public key; it writes
no private key. Press Control-C to cancel. Files are never overwritten.

## Practice recovery before you need it

```sh
node scripts/key-backup.cjs restore "$HOME/aitrust-receipts/key-backup.json" "$HOME/aitrust-receipts/public.pem" "$HOME/aitrust-receipts/restored-private.pem"
```

The tool asks for your password. It restores a new key file only after both the
encrypted contents and separately supplied public key match. Use that restored
key to sign a **test** receipt with the receipt guide, then verify it with your
original public key. Practice this on a second computer you control before
relying on the backup. Remove the extra test key using your chosen secure
storage practices; deleting a file does not guarantee physical disk erasure.

Key and backup destinations must be outside this repository, in an owner-only
directory (0700). Private inputs and new files require owner-only permissions
(0600). The tool refuses unsafe permissions, final symlinks, output directories
containing symlinks, existing outputs and unsupported signing keys. A restore
refusal does not change your existing key or backup.

## If something is lost or compromised

- **Lost key, intact backup:** restore using the password and original public
  key, then check a test receipt. Verifiers continue using that same public key.
- **Forgotten password or missing backup:** we cannot recover the key. Create
  a new key and establish its public fingerprint separately with your verifiers.
  Old signatures remain associated with the old key.
- **Stolen or exposed key:** restoring does not make its stolen copies safe.
  Stop signing, record revocation through your chosen trusted process, create a
  new key, and notify your verifiers. The [cached status tool](offline-revocation.md)
  is an optional local check; it is not a public revocation service.

## What is implemented and what remains

The `offline-key-backup/1.0.0` format supports Ed25519 and ECDSA P-256. It uses
Node's built-in AES-256-GCM with a random 12-byte nonce and 16-byte salt, and
scrypt N=32768, r=8, p=1, 32-byte output. Version, algorithm, public fingerprint,
KDF and cipher settings are authenticated. Unsupported parameters and malformed
or ambiguous records are rejected before acceptance. These are implementation
choices, not a certified cryptographic assurance or a post-quantum claim.

A stolen backup can be guessed offline; a compromised computer can access keys
and passwords in memory. Mutable working buffers are cleared where available;
JavaScript strings, operating-system caches and physical disk erasure are not
guaranteed. No hosted escrow, automatic password reset, automatic rotation or
production key change occurs. For owner-controlled scripts, `--password-file`
accepts an existing owner-only UTF-8 file with no newline; never put a password
in command arguments, environment variables, source files or execution logs.

Automated checks cover backup, wrong password, wrong public key, tampering,
permissions and recovery-to-receipt verification. Actual nontechnical-author
operation remains required before F-129 is complete. Recovery proves possession
of a signing key, not a person's identity, authorship or content accuracy.
