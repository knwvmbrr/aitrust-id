# Full replacement-host recovery — architecture before execution

F-073 requires a replacement operating system, not another restored database
inside a container. Exercise an actual fresh Debian 13 virtual machine with its
own kernel, systemd, SSH configuration, PostgreSQL cluster, runtime identities,
firewall and monitoring units. Use the already-paid project-exclusive primary
host's spare resources; add no paid service or public endpoint. Keep the live
cluster and its configuration untouched. Record baseline and final identities,
service state and configuration hashes. Owner/provider MFA and physical/offline
custody are separate obligations and are not inferred from this drill.

Prepare a verified official Debian cloud image and signed packages before any
project secrets enter the guest. Use a throwaway development SSH key during this
preparation. Bound the QEMU process's memory and CPU, run it unprivileged with
NoNewPrivileges and isolated writable paths, and retain a verified guest host-key
pin. Inspect the host package plan before installing only the required tools;
never run the production host's bootstrap or an unrestricted upgrade.

Before recovery material is delivered, shut down the preparation guest and boot
it in a fresh loopback-only Linux network namespace. Its virtual networking must
have no outbound path. Retrieve an explicitly selected encrypted backup generation
from the independent repository using owner-authorized SSH, without moving an
administrative private key to another provider. Root-only encrypted staging and
owner recovery material stay inside the existing primary trust boundary. Never
copy the decryption key onto the backup provider.

Reconstruct the supported host configuration from the versioned project source
and owner recovery bundle, not a copy of the live root disk. Restore the actual
selected database into fresh guest storage. Verify data checksums, database
identity, application schema/record counts without exposing content, least-
privilege OS/SQL roles, socket-only database access, SSH and dual-stack firewall
configuration, and effective monitoring units. Prevent automatic backup/notification
jobs from reaching production while testing; no real collection is enabled.

Use separately bound failure scenarios for missing/wrong recovery material,
corrupt backup input and wrong restore destination. Exercise incident/adapter
response with a documented actual failure and correction, without disrupting the
public website. Reboot the guest and rerun the selected operating checks. Preserve
sanitized timings and source/configuration identities, then destroy the guest,
private temporary credentials, decrypted disk and staging copies. Keep the original
backup generations and primary services unchanged. Do not claim cross-provider
failover, production-scale RTO, human recovery acceptance or a response SLA.

Stop or adjust the drill if package installation would replace/restart critical
live services, resource headroom is inadequate, the guest boundary cannot be
verified, recovery material cannot be obtained through existing authorization, or
there is no complete recoverable host profile. A failed drill remains open and
must not be counted as a full requirement closure.

Transient systemd units can disappear after the preparation guest powers off.
Keep the verified preparation checkpoint in root-only storage, reuse one bounded
launch-argument builder, and recreate an explicitly isolated unit after shutdown.
Never restart the VM through a leftover service name or copy data before the new
namespace is independently checked. Store helper versions in a root-only cache
under their content hashes; do not execute helpers from writable temporary paths.

Control subprocesses must receive closed standard input. Only the explicitly named
archive or private-material transfer may inherit a supplied byte stream. Read the
expected payload before readiness commands and test that a control child cannot
consume its parent's recovery stream. This prevents accidental delivery to a
control SSH command, including a command on the backup provider.
