# Independent backup option for owner review

Updated 2026-10-08. The owner reports payment completed; the provider shows the
backup Droplet Active. The encrypted backup pilot and offline synthetic restores
are complete within the tested scope; production onboarding remains blocked.
The purchase/access paragraph below records the earlier handoff. Its key mismatch
was resolved by the owner; the [executed implementation](backup-implementation.md)
and [result](../runs/2026-10-08-independent-backup-result.json) supersede the
configuration-pending status. Encrypted backups, protected generations and two
offline synthetic restores passed. Owner key custody, MFA and external alerts
remain open; collection stays disabled.
The main OVHcloud VPS and an installed pgBackRest binary do not establish recovery.

**Signed-in console update:** the owner requested the purchase configuration in
their logged-in Chrome account. Regular CPU was disabled in NYC1, SFO3 and NYC3.
The prepared alternative is Debian 13 in NYC3, Basic Premium Intel, 1 vCPU,
2 GB RAM, 70 GB NVMe disk, **$16/month** before tax, named `aitrust-backup-01`.
No volumes, provider backups or managed database were added to the draft. This is
$4 above the published Regular-plan quote below. The owner completed purchase and
the provider confirms the selected capacity is Active. The provider console has
root access and confirms Debian 13; its SSH host fingerprint matches the local
pinned record. IPv4 and owner-enabled IPv6 still require firewall verification.

**Access gap:** the selected key name in the draft did not establish its actual
fingerprint. The provisioned host has an existing local administrator key,
not the dedicated backup key. The existing key is accepted by SSH but cannot
complete unattended authentication; the signing failure's cause is unresolved.
The dedicated key is rejected because it is absent. The owner has been asked to
install the dedicated public key in the open provider console. No password login
was enabled, no key removed and no server rebuilt. Deployment remains blocked
until the dedicated SSH login is verified. See
[runtime check](../runs/2026-10-08-backup-provisioning-check.json).

Other regions were not exhaustively checked.
[DigitalOcean configuration](https://cloud.digitalocean.com/droplets/new).

The original recommendation for full Linux control was a separate **Debian backup VPS at
DigitalOcean: Basic Regular, 1 vCPU, 2 GiB RAM, 50 GiB SSD, $12/month before tax**.
Choose an available US region separate from the primary site; live inventory and
the final checkout total still need checking. That earlier quote added $12/month to the existing $10/month main host; the
owner purchased the available $16/month alternative above instead.
[Published VPS pricing](https://www.digitalocean.com/pricing/droplets).

This keeps Debian and the backup software under our control. The cloud control
plane is proprietary, as OVHcloud's is. The server is exclusive to AI Trust ID,
in a separate provider account with separate administrative keys; account MFA
still requires verification.
It stores database-consistent backups and restore instructions. The 50 GiB disk
is a bounded pilot repository, not a guarantee it can back up a full 75 GB primary
disk indefinitely. Measure full backup size, WAL volume and retention before
accepting data; monitor free space and scale before exhaustion.

The lower-cost alternative is a **private Backblaze B2 bucket**. Its published
storage rate is $6.95/TB/month, first 10 GB free; egress is free up to three times
average stored data, then $0.01/GB. At 100 GB, budget about $0.70/month for storage
before the free allowance and tax. Actual retained backups and WAL determine
billing. B2 is a proprietary storage service; our backup client and data format
remain portable. S3-compatible operation needs execution against this specific
provider before acceptance. [B2 pricing](https://www.backblaze.com/cloud-storage/pricing).

## Implementation and release checks after selection

1. Create a fresh encrypted pgBackRest repository with the patched version
   already installed on the primary. Record its identity and package versions.
   Store its recovery key separately from either server, in an owner-controlled
   password manager plus an offline recovery copy. Losing that key can make
   sound backups unusable.
2. Use restricted backup credentials, encrypted transport and verified host/TLS
   identity. Never reuse the primary administrator key or database runtime roles.
   Keep backup-account administration unavailable to a compromised primary.
3. Enable WAL archiving, scheduled backups, retention and alerts. Proposed pilot
   retention is two weekly full backups with daily differentials; the owner must
   accept retention/deletion behavior before real data. Deleting a live record
   does not immediately delete historical backup copies.
4. Protect a recoverable generation from primary-host deletion or overwrite.
   Test attempted destruction using only the primary's backup credential.
   Encryption alone does not prevent ransomware or malicious deletion. For a
   Linux repository, use a separately controlled protected generation; for an
   object store, validate retention protection against pgBackRest expiry behavior
   before enabling it. Neither option is called immutable without testing.
5. Restore synthetic records to a fresh isolated PostgreSQL 18 instance, verify
   record IDs, permissions and point-in-time recovery, then test key revocation,
   repository outage, capacity alerts and owner recovery access. Restoration
   must work without the lost primary host/account.

pgBackRest documents client-side repository encryption, separate repository hosts
and S3-compatible storage. Those capabilities are not a tested deployment here.
[Configuration](https://pgbackrest.org/configuration.html),
[backup and restore guide](https://pgbackrest.org/user-guide.html).

The proposed 15-minute recovery-point and four-hour recovery-time targets remain
unverified until measured by the drill. A backup location supports recovery; it
does not make the live application highly available. Collection remains disabled
while destination, keys, retention and restoration are incomplete.
