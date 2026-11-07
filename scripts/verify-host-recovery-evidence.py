#!/usr/bin/env python3
"""Verify bounded replacement-host evidence without claiming production failover."""
import hashlib,json,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from protocol.evidence import read_evidence
CASES={'fresh_replacement_os_and_empty_distinct_cluster','selected_encrypted_repository_and_backup_metadata_valid','wrong_recovery_key_refused','corrupted_repository_metadata_refused','actual_source_cluster_identity_restored','actual_application_and_synthetic_table_counts_match','restored_database_is_socket_only_and_outbound_archiving_disabled','checksummed_restored_database_promoted','restored_runtime_roles_remain_unprivileged','reconstructed_os_peer_identity_and_admin_denial','reconstructed_ssh_and_dual_stack_firewall_active','replacement_administration_works','owner_public_administration_key_reconstructed','actual_source_monitor_units_reconstructed','offline_archive_disabled_failure_detected','replacement_database_outage_detected','bounded_incident_message_contains_no_application_data','replacement_database_restart_detected_as_recovery','production_wal_shipping_stays_disabled','owner_key_authentication_without_private_key_transfer','restored_guest_reboot_persistence','source_host_identity_configuration_and_services_unchanged','source_archive_health_passes','nonce_guest_and_private_staging_removed','original_protected_generations_preserved'}
SOURCES=tuple('deploy/recovery/'+n+'.py' for n in ['prepare','guest','isolate','receive','collect','apply','restore-guest','monitor','monitor-guest','finish'])+tuple('deploy/host/'+n for n in ['bootstrap.sh','verify.py','roles.sql','postgresql.conf','pg_hba.conf','pg_ident.conf','sshd.conf','nftables.conf'])+('deploy/alerts/alerts.py','deploy/backup/source-health.py','tests/test_recovery_stream_boundary.py','docs/full-host-recovery-plan.md','docs/security-operations.md')
def check(ok):
    if not ok:raise ValueError('Replacement-host evidence missing, stale or overstated')
def hashes(root=ROOT):return {name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in SOURCES}
def verify(d,root=ROOT):
    check(d['format']=='full-host-recovery/v1' and d['pass'] is True and d['platform']=='linux/amd64' and d['foundation_checks']==46)
    at=datetime.fromisoformat(d['captured_at']);check(at.tzinfo is not None and at<=datetime.now(timezone.utc))
    check(d['sources']==hashes(root));rows=d['controls'];check(len(rows)==len(CASES) and {r['case'] for r in rows}==CASES and all(r['pass'] is True for r in rows))
    for name in ['actual_encrypted_generation_recovered','own_kernel_systemd_firewall_and_ssh','wrong_destination_refused','independent_backup_provider_used','secret_delivery_only_after_loopback_namespace_verified']:check(d[name] is True)
    for name in ['occupied_application_table_recovery_claimed','production_source_host_changed','public_endpoint_added','collection_enabled','external_messages_sent_by_drill','production_scale_rto_claimed','cross_provider_failover_claimed','physical_or_human_acceptance','independent_security_certification','physical_erasure_claimed','current_source_full_vm_rerun_claimed']:check(d[name] is False)
    check(d['actual_application_tables']==0 and d['encrypted_files']>0 and d['encrypted_bytes']>0)
    cleanup=d['cleanup'];check(cleanup['pass'] is True and cleanup['physical_erasure_claimed'] is False)
    for name in ['nonce_guest_removed','private_test_key_and_recovery_material_removed','decrypted_guest_disk_removed','encrypted_staging_copy_removed','source_host_unchanged','original_protected_backup_generations_untouched']:check(cleanup[name] is True)
    # The exact six measured helper hashes are retained separately. Do not
    # pretend the later metadata/stdin preflight repairs ran through the VM.
    old=d['full_vm_executed_helper_hashes'];check(set(old)=={'guest','isolate','apply','restore-guest','monitor','finish'})
    for name in ['apply','restore-guest','monitor','finish']:check(old[name]==d['sources']['deploy/recovery/'+name+'.py'])
    check(len(d['post_drill_repairs'])==3 and d['source_bound_focused_post_drill_checks_required'] is True)
    guards=read_evidence(root/'runs/2026-11-06-host-final-guards.json');check(guards['pass'] is True and guards['tests']==10 and guards['sources']==hashes(root))
    binding=read_evidence(root/'runs/2026-11-07-recovery-source-binding.json')
    expected={Path(name).name:d['sources'][name] for name in SOURCES if name.startswith('deploy/host/')}
    check(binding['pass'] is True and binding['actual_foundation_source_hashes']==expected and binding['source_host_configuration_matches_current'] is True and binding['source_production_configuration_changed'] is False)
    check(d['private_security_reporting_enabled'] is True and d['accountable_operator']=='Michael' and d['response_sla_claimed'] is False)
    return {'pass':True,'controls':len(CASES),'focused_guard_cases':10,'actual_application_tables':0,'current_source_full_vm_rerun_claimed':False,'independent_security_certification':False,'collection_enabled':False}
def verify_operations(root=ROOT):
    packet=read_evidence(root/'runs/2026-11-07-security-operations-acceptance.json')
    check(packet['pass'] is True and packet['requirement']=='F-073' and packet['criteria_moved_or_waived'] is False)
    check(packet['original_required_acceptance']==['Maintain named operational owners and source-bound evidence; exercise incident/adapter response and full replacement-host recovery, then close outstanding security findings.'])
    check(packet['global_security_clearance'] is False and packet['staffed_response_sla_claimed'] is False and packet['real_data_collection_enabled'] is False)
    channel=read_evidence(root/'runs/2026-11-07-security-channel-status.json')
    check(channel['pass'] is True and channel['private_vulnerability_reporting_enabled'] is True and channel['accountable_operator']=='Michael' and channel['staffed_response_sla_claimed'] is False)
    adapter=read_evidence(root/'runs/2026-11-07-adapter-incident-exercise.json')
    check(adapter['pass'] is True and adapter['case_count']==49 and adapter['live_vendor_compatibility'] is False and adapter['synthetic_chrome_storage_and_fetch'] is True)
    check(all(hashlib.sha256((root/name).read_bytes()).hexdigest()==value for name,value in adapter['source_sha256'].items()))
    return {'private_reporting_channel_enabled':True,'adapter_injected_failure_cases':49,'staffed_response_sla_claimed':False}

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--evidence',type=Path,default=ROOT/'runs/2026-11-06-host-final-acceptance.json');a=p.parse_args()
    try:print(json.dumps({**verify(read_evidence(a.evidence)),**verify_operations()}))
    except (ValueError,KeyError,TypeError,OSError) as e:print(str(e),file=sys.stderr);raise SystemExit(1)
