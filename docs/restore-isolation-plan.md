Restore drill isolation repair

Architecture: keep the existing synthetic named-target restore contract and socket-only PostgreSQL topology. Before umask, filesystem creation, configuration reads or subprocesses, require root on Linux, a network namespace distinct from PID 1 and exactly the loopback interface. Recheck identity immediately before restore and cluster startup, and retain the existing post-start check. Refuse namespace inspection errors and any external interface.

Protect the original named generation before resolving it: no symlink, root-owned directory, owner-only permissions and a root-owned non-writable ancestor chain. Protected generation hard links remain allowed because cycle.py deliberately uses them between root-only copies; do not imply provider immutability. No arbitrary generation path, new CLI bypass, environment bypass or production mutation.

Risks: namespace difference alone does not imply no egress; require loopback-only too. A hostile root could switch namespace later, which this tool cannot defend against. Missing procfs or unsupported hosts must refuse. Keep existing unshare invocation compatible. Unit refusal/ordering tests plus a real owned Linux namespace preflight must exercise positive and negative behavior; do not restore a real backup or read host secrets to test the guard. Full replacement-host recovery remains open.

Acceptance: a wrong/non-root/host/connected/uninspectable namespace and linked/service-owned/writable generation refuse before any side effect; valid root-only synthetic generation and fresh loopback-only network namespace pass the guard; no actual restore is claimed from guard tests. New code must be covered by host-config CI and source-bound inventory/changelog.

Reference: Linux man-pages network_namespaces(7), https://www.man7.org/linux/man-pages/man7/network_namespaces.7.html. Namespace identity and interface checks are applied together because a namespace may be connected through veth; the engineering test must confirm the selected kernel behavior.

Before copying a generation, inspect its full directory/file shape: same filesystem, directories 0700, files 0600, every member owned by root, no links/special nodes, with 100,000 visited entries and a 30-second inspection budget. Preserve legitimate root-owned regular-file hard links between protected copies. Refuse service-owned/shared members, unreadable trees, mount crossings or budget overflow before secret reads. This is permission/topology inspection, not a valid-backup or permission-to-restore claim. Full replacement-host recovery remains open.

Before the inspection implementation is finalized, traverse directory entries lazily with scandir rather than materializing whole directory path lists. Enforce the visit/time budget before inspecting each entry; keep only accepted private child directories pending. Test nested directories and explicit entry-budget refusal as well as the kernel-backed permissions cases.
