#!/usr/bin/env python3
"""Execute host/role checks. Does not certify a public service or recovery."""
import json
import os
import subprocess
import sys
import uuid


def run(args, *, check=True):
    return subprocess.run(args, text=True, capture_output=True, check=check)


def sql(query, *, account="postgres", role="postgres", check=True, readwrite=False):
    args = ["runuser", "-u", account, "--", "psql", "--no-psqlrc", "-XAt",
                "--set", "ON_ERROR_STOP=1", "-h", "/var/run/postgresql",
                "-U", role, "-d", "aitrustid"]
    if readwrite:
        args += ["-c", "SET default_transaction_read_only=off"]
    return run(args + ["-c", query], check=check)


def main():
    if os.geteuid() != 0:
        raise SystemExit("Run with sudo for OS-identity and effective policy checks.")
    checks = {}
    failures = []

    def record(name, passed):
        checks[name] = bool(passed)
        if not passed:
            failures.append(name)

    ssh = dict(line.split(" ", 1) for line in run(["sshd", "-T"]).stdout.splitlines())
    for setting, expected in {"passwordauthentication": "no", "permitrootlogin": "no",
                              "kbdinteractiveauthentication": "no", "pubkeyauthentication": "yes",
                              "x11forwarding": "no", "allowagentforwarding": "no"}.items():
        record("ssh_" + setting, ssh.get(setting) == expected)
    rules = json.loads(run(["nft", "--json", "list", "ruleset"]).stdout)["nftables"]
    chains = {x["chain"]["name"]: x["chain"] for x in rules if "chain" in x and x["chain"].get("table") == "aitrust_host"}
    record("firewall_input_drop", chains.get("input", {}).get("policy") == "drop")
    record("firewall_forward_drop", chains.get("forward", {}).get("policy") == "drop")
    record("firewall_persistent", run(["systemctl", "is-enabled", "nftables"], check=False).stdout.strip() == "enabled")
    resolver = run(["resolvectl", "status"]).stdout
    protocols = [line for line in resolver.splitlines() if "Protocols:" in line]
    record("resolver_multicast_disabled", bool(protocols) and all("-LLMNR" in line and "-mDNS" in line for line in protocols))
    sockets = run(["ss", "-lnutH"]).stdout.splitlines()
    record("no_multicast_name_listeners", not any(line.split()[4].rsplit(":", 1)[-1] in {"5353", "5355"} for line in sockets))
    record("dns_resolution_works", run(["getent", "ahostsv4", "apt.postgresql.org"], check=False).returncode == 0)
    record("postgres_socket_only", sql("SHOW listen_addresses").stdout.strip() == "")
    record("postgres_18", int(sql("SHOW server_version_num").stdout.strip()) // 10000 == 18)
    record("postgres_checksums", sql("SHOW data_checksums").stdout.strip() == "on")
    record("postgres_hba_valid", sql("SELECT count(*) FROM pg_hba_file_rules WHERE error IS NOT NULL").stdout.strip() == "0")
    record("no_database_tcp_listener", not any(":5432" in line for line in run(["ss", "-lnt"]).stdout.splitlines()))
    record("postgres_durable", sql("SELECT current_setting('fsync')='on' AND current_setting('full_page_writes')='on' AND current_setting('synchronous_commit')='on'").stdout.strip() == "t")
    record("database_health", sql("SELECT 1").stdout.strip() == "1")
    record("runtime_roles_unprivileged", sql("SELECT count(*) FROM pg_roles WHERE rolname IN ('aitrust_intake','aitrust_reviewer','aitrust_reader') AND (rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls)").stdout.strip() == "0")
    mapping = [("debian", "aitrust_reader"), ("ait-analysis", "aitrust_reader"),
               ("ait-intake", "aitrust_intake"), ("ait-review", "aitrust_reviewer")]
    for account, role in mapping:
        record("peer_identity_" + account, sql("SELECT current_user", account=account, role=role).stdout.strip() == role)
        impersonate = sql("SELECT 1", account=account, role="postgres", check=False)
        record("peer_blocks_admin_" + account, impersonate.returncode != 0)
        elevate = sql("SET ROLE aitrust_owner", account=account, role=role, check=False)
        record("no_owner_escalation_" + account, elevate.returncode != 0)
    record("reader_read_only_default", sql("SHOW transaction_read_only", account="debian", role="aitrust_reader").stdout.strip() == "on")
    # Actual runtime sessions test permissions, rather than SET ROLE under the
    # postgres superuser (which would retain the superuser's elevation ability).
    schema = "verify_" + uuid.uuid4().hex
    try:
        sql(f"CREATE SCHEMA {schema} AUTHORIZATION aitrust_owner; SET ROLE aitrust_owner; CREATE TABLE {schema}.probe (value integer); GRANT USAGE ON SCHEMA {schema} TO aitrust_intake, aitrust_reviewer, aitrust_reader; GRANT INSERT ON {schema}.probe TO aitrust_intake; GRANT SELECT ON {schema}.probe TO aitrust_reader; GRANT UPDATE ON {schema}.probe TO aitrust_reviewer")
        record("intake_insert", sql(f"INSERT INTO {schema}.probe VALUES (7)", account="ait-intake", role="aitrust_intake", check=False).returncode == 0)
        record("reader_select", sql(f"SELECT value FROM {schema}.probe", account="ait-analysis", role="aitrust_reader").stdout.strip() == "7")
        for account, role in mapping:
            denied = sql(f"DELETE FROM {schema}.probe", account=account, role=role, check=False)
            record("no_delete_" + account, denied.returncode != 0)
        for statement in [f"SELECT * FROM {schema}.probe", f"UPDATE {schema}.probe SET value=9"]:
            record("intake_denied_" + statement.split()[0].lower(), sql(statement, account="ait-intake", role="aitrust_intake", check=False).returncode != 0)
        # Turning off a session's read-only flag must not grant table writes.
        attempt = sql(f"INSERT INTO {schema}.probe VALUES (9)", account="ait-analysis", role="aitrust_reader", check=False, readwrite=True)
        record("reader_write_denied_even_without_readonly", attempt.returncode != 0 and "permission denied" in attempt.stderr)
    finally:
        sql(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
    record("verification_schema_cleaned", sql("SELECT count(*) FROM pg_namespace WHERE nspname LIKE 'verify_%'").stdout.strip() == "0")
    backup = run(["pgbackrest", "version"]).stdout.strip().split()[-1]
    record("pgbackrest_patched", run(["dpkg", "--compare-versions", backup, "ge", "2.59.3"], check=False).returncode == 0)
    record("random_access", len(os.getrandom(32)) == 32)
    record("updates_timer", run(["systemctl", "is-active", "apt-daily-upgrade.timer"], check=False).stdout.strip() == "active")
    report = {"scope": "private_host_foundation", "checks": checks, "failures": failures,
              "passed": not failures, "pgbackrest_version": backup,
              "production_ready": False, "independent_backup_verified": False,
              "public_intake_deployed": False, "tenant_isolation_verified": False}
    print(json.dumps(report, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
