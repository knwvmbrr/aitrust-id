#!/usr/bin/env python3
"""Keep the actual optional-audit Linux acceptance bound to its executed source."""
import argparse,json,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools.organization_audit_lab import hashes
from tools.organization_audit import parse,require

EVIDENCE='runs/2026-10-15-organization-audit-cli-linux.json'
CASES={
 'actual_dedicated_database_install','existing_database_reinstall_refused','privileged_principal_enrollment_refused',
 'database_owner_cannot_be_tenant_principal','unaccepted_policy_refused','concurrent_first_append_serialized',
 'actual_checker_prepare_append_retry','conflicting_overwrite_refused','direct_sql_raw_text_bypass_refused',
 'direct_sql_span_overrun_refused','server_side_closed_metadata_validation','null_policy_acceptance_refused',
 'role_and_unauthorized_session_denied','tenant_isolation_and_direct_table_denial','temporary_table_tenant_spoof_refused',
 'supersession_and_fixed_choice_review','paged_export_and_external_checkpoint','pinned_history_tampering_refused',
 'metadata_tampering_refused','actual_encrypted_full_backup_with_quarantine','restored_database_refuses_tenant_access',
 'old_backup_deletion_limit_explicit','missing_wrong_or_stale_recovery_authority_refused',
 'current_deletion_overlay_before_access','expired_metadata_hidden_before_sweep','declared_audit_prefix_retention',
 'post_deletion_encrypted_backup','expired_backup_label_cannot_restore','personal_checker_works_with_audit_store_stopped'}

def verify(receipt):
    require(receipt['pass'] is True and receipt['private_failure'] is None)
    for key in ('non_root','isolated_network_namespace','clusters_stopped','owned_scratch_removed','source_unchanged_during_execution'):require(receipt[key] is True)
    for key in ('actual_participant_data','production_changes','physical_erasure_verified','independent_tag_accuracy_evidence'):require(receipt[key] is False)
    when=datetime.fromisoformat(receipt['captured_at']);require(when.tzinfo is not None and when<=datetime.now(timezone.utc))
    require(receipt['sources']==hashes())
    controls=receipt['controls'];require(len(controls)==len(CASES) and {c['case'] for c in controls}==CASES and all(c['pass'] is True for c in controls))
    require(receipt['postgresql_version'].startswith('postgres (PostgreSQL) 18.') and receipt['pgbackrest_version']=='pgBackRest 2.59.3')
    return {'pass':True,'actual_linux_controls':len(CASES),'executed_sources_current':True,'independent_tag_accuracy_evidence':False,'company_collection_enabled':False}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--evidence',type=Path,default=ROOT/EVIDENCE);a=p.parse_args()
    try:print(json.dumps(verify(parse(a.evidence.read_bytes()))));return 0
    except Exception:print('Organization audit execution evidence refused.',file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
