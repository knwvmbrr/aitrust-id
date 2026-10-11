# Optional key backup and recovery — architecture before implementation

F-129 needs usable custody and recovery, including actual nontechnical-author
acceptance. This increment implements the offline mechanism and owner-run guide;
it cannot substitute a terminal test for that human acceptance. No tag, receipt
standard, public revocation service or server endpoint is enabled.

Use Node 24 built-in cryptography and the existing strict bounded record/file
primitives. Encrypt canonical PKCS8 Ed25519 or P-256 signing keys with AES-256-GCM
and a fixed, bounded scrypt profile (N=32768, r=8, p=1). Each backup gets an
independent random salt and nonce. Authenticate its version, algorithm, public
fingerprint and KDF/cipher fields as associated data. On recovery require the
separately saved public key; never trust a key embedded in a backup. Refuse wrong
passwords, tampering, unsupported parameters, ambiguous keys and records,
oversize data, unsafe private input permissions, symlinks and overwrites.

Provide an interactive password entry with hidden input and confirmation for a
new backup. Passwords never appear in CLI arguments, environment variables or
logs. A separate owner-only password file can support disposable automated
tests and owner-controlled scripts. New restored keys stay outside this repo,
in an owner-only directory with 0600 permissions. Cancelled operations must not
create output. Erase mutable key/derived-password buffers after use; immutable
JavaScript strings and compromised-host memory remain explicit limits.

Acceptance: execute both algorithms and backup-to-recovery-to-receipt verification
on actual Mac and network-isolated Linux; exercise CLI cancellation/permissions,
lost password, wrong selected key, header/body tampering and unsupported profiles.
Keep usable step-by-step save, restore, practice and compromise instructions. A
recovered key does not revoke its stolen copies or establish identity/authorship.

Risks: an offline stolen backup permits password guessing. A memorable strong
password and a separate password manager are required; the tool cannot measure
password entropy or recover a forgotten password. Backups reveal algorithm and
key fingerprint and can link records. Keep them privately outside the repository.
Compromised machines, clipboard/password-manager security, disk erasure and
actual human operation remain outside what automated checks can prove.

Author: Codex. Planned 2026-10-11 UTC before feature code.

## Review repair plan — failed output containment

PR-22 review identified that the reused receipt writer creates the destination
before write/fsync success. For this optional private-key workflow, replace that
use with a dedicated publisher: validate the existing owner-only destination,
create a random owner-only temporary file in the same directory, write and sync
all bytes, close, then atomically hard-link the complete file to the new final
name without overwrite. Write/sync/close/link failures must leave no final key;
clean temporary output and permit a retry. Test failures with injected I/O errors
over actual files, plus concurrent destination creation without deleting the
other writer's file. Do not alter current personal checks or their receipt writer.
Temporary-file cleanup failures must be surfaced explicitly; do not promise
physical erasure or disk/host compromise protection. Plan recorded before repair.

The repair also applies this publisher to the existing receipt CLI writer, so
initial key creation has the same write/sync failure containment as restoration.
Extract it as an internal built-in-only module; keep each caller’s existing path
and permission checks. Personal gateway, capture, assertion and tag semantics
remain unchanged. Update source inventories and run both CLI families before
resolving the review. This broader repair was planned before changing the writer.
