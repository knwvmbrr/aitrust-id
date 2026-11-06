#!/usr/bin/env python3
"""Refuse missing, stale or incomplete real directory integration evidence."""
import argparse,json,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools.organization_directory_lab import hashes
from protocol.evidence import read_evidence
CASES=('actual_https_provider_with_explicit_test_ca','valid_foreign_issuer_token_refused','untrusted_tls_certificate_refused','wrong_selected_ca_refused','actual_device_login_and_private_record_view_cli','actual_separate_export_permission','actual_organization_feedback_review','view_does_not_grant_export','configuration_does_not_grant_review','cross_tenant_request_refused','wrong_database_tenant_binding_refused','forged_token_refused','current_directory_role_removal_denies_old_token','restored_directory_role_works','disabled_directory_user_denied','local_membership_revoke_denies','current_admin_can_restore_non_compromised_member','separate_owner_recovery_fences_compromised_admin','pre_recovery_replacement_session_also_fenced','fresh_replacement_login_restores_authorized_access','directory_admin_cannot_undo_owner_compromise_fence','actual_local_and_provider_token_revocation','logged_out_private_access_denied','provider_outage_denies_private_access','personal_checker_runs_with_directory_offline','local_logout_persists_during_provider_outage','journal_contains_no_tokens_credentials_or_response_text')
def verify(row):
    def check(ok):
        if not ok:raise ValueError('Directory evidence refused')
    check(row['format']=='organization-directory-software/v1' and row['platform']=='linux')
    for k in ('pass','source_unchanged','non_root','isolated_network_namespace','real_provider_and_database','synthetic_identities_only'):check(row[k] is True)
    for k in ('production_changed','collection_enabled','independent_accuracy_evidence','human_acceptance','certification'):check(row[k] is False)
    check(row['keycloak_version']=='26.8.2' and type(row['postgresql_major']) is int and row['postgresql_major']==18 and row['failure'] is None)
    check(row['sources']==hashes())
    expected=[{'case':name,'pass':True} for name in CASES];check(row['controls']==expected)
    t=datetime.fromisoformat(row['captured_at']);check(t.tzinfo is not None and t<=datetime.now(timezone.utc))
    return {'pass':True,'actual_provider_controls':len(CASES),'sources_current':True,'hosted_service_enabled':False,'human_acceptance':False,'independent_accuracy_evidence':False}
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--receipt',type=Path,default=ROOT/'runs/2026-11-06-directory-final-linux.json');a=p.parse_args()
    try:print(json.dumps(verify(read_evidence(a.receipt))));return 0
    except Exception:print('{"pass":false,"reason":"directory_execution_missing_or_stale"}');return 1
if __name__=='__main__':raise SystemExit(main())
