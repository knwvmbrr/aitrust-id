#!/usr/bin/env python3
"""Bind supported host-capture OS claims to actual, current terminal execution."""
from datetime import datetime,timezone
import importlib.util
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
spec=importlib.util.spec_from_file_location('host_capture_verification',ROOT/'scripts/verify-host-capture.py')
implementation=importlib.util.module_from_spec(spec);spec.loader.exec_module(implementation)
CASES={
 'test_ctrl_z_stops_instead_of_creating_a_background_capture_job',
 'test_background_resume_refuses_new_capture_after_sigstop',
 'test_capture_lifecycle_duplicate_pause_reset_delete','test_capture_only_survives_broken_optional_detector',
 'test_consent_pin_and_foreground_are_required','test_directory_change_and_sensitive_scope_refused',
 'test_failed_optional_analysis_recovers_on_next_revision','test_file_boundaries','test_frozen_normalization_and_record_identity',
 'test_hanging_analysis_can_be_paused_without_late_result','test_invalid_files_never_become_no_finding',
 'test_journal_quota_stops_without_overwriting','test_journal_refuses_unowned_modified_or_existing_files',
 'test_optional_ps_checks_both_states_without_saving_text','test_parent_death_stops_frozen_worker',
 'test_termination_does_not_resume_existing_session','test_two_queued_commands_are_not_lost',
 'test_version_change_stops_even_while_paused','test_worker_failure_timeout_and_cancellation_are_bounded'}

def verify(row,platform):
    def require(ok):
        if not ok:raise ValueError('Host capture evidence refused')
    require(row['format']=='ai-trust-id-host-capture-engineering/v1' and row['platform']==platform)
    for key in ('pass','non_root','actual_foreground_pty','source_unchanged','synthetic_inputs_only'):require(row[key] is True)
    for key in ('automatic_upload','independent_accuracy_evidence','human_acceptance_complete','physical_phone_tested','company_collection_enabled'):require(row[key] is False)
    for key in ('failures','errors','skipped'):require(type(row[key]) is int and row[key]==0)
    require(type(row['test_count']) is int and row['test_count']==len(CASES)==len(row['cases']) and set(row['cases'])==CASES)
    require(row['sources']==implementation.hashes())
    if platform=='linux':require(row['isolated_network_namespace'] is True)
    when=datetime.fromisoformat(row['captured_at']);require(when.tzinfo is not None and when<=datetime.now(timezone.utc))
    require(tuple(int(n) for n in row['python_version'].split('.'))>=(3,12))
    return True

def main():
    try:
        for platform,label in (('darwin','macos'),('linux','linux')):
            verify(json.loads((ROOT/('runs/2026-11-06-host-capture-final-'+label+'.json')).read_bytes()),platform)
        print(json.dumps({'pass':True,'supported_os':['macOS','Linux'],'controls_per_os':len(CASES),
            'current_source_bound':True,'independent_accuracy_evidence':False,'human_acceptance_complete':False}));return 0
    except Exception:print('Host capture OS execution evidence refused.',file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
