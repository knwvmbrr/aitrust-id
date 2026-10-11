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
