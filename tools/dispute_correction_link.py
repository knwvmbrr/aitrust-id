"""Bind an existing synthetic dispute to one selected private editorial correction."""
import copy
import os
import stat
import uuid
from datetime import datetime, timezone
from pathlib import Path

from tools import community_core as community
from tools import community_store
from tools import newsroom
from tools.blind_review_io import create, directory, source
from tools.editorial_cli import read_packet

PLAN = 'private-dispute-correction-plan/v1'
LINK = 'private-dispute-correction-link/v1'
MAX_ARTIFACT = 2_000_000


def workbench_identity(folder, root):
    """Distinguish a selected database from a copied or rebuilt workbench."""
    with directory(folder, root) as directory_fd:
        folder_info = os.fstat(directory_fd)
        database_info = os.stat('community.sqlite', dir_fd=directory_fd, follow_symlinks=False)
        lock_info = os.stat('access.lock', dir_fd=directory_fd, follow_symlinks=False)
    newsroom.require(stat.S_ISREG(database_info.st_mode) and stat.S_ISREG(lock_info.st_mode))
    identity = {
        'directory': [folder_info.st_dev, folder_info.st_ino],
        'database': [database_info.st_dev, database_info.st_ino],
        'lock': [lock_info.st_dev, lock_info.st_ino, lock_info.st_ctime_ns],
    }
    return newsroom.sha(newsroom.encode(identity))


def read_report(store, report_id, moderator, root):
    community.identity(report_id)
    newsroom.require(community.ACTORS.get(moderator) == 'moderator')
    with store.transaction() as engine:
        before = workbench_identity(store.path, root)
        report = copy.copy(engine.state['reports'].get(report_id))
        newsroom.require(report is not None and report['category'] == 'wrong_result' and report['reporter'] != moderator)
        newsroom.require(workbench_identity(store.path, root) == before)
    return report, before


def editorial_binding(raw_assertion, raw_subject, raw_selection, raw_prior, raw_correction, *, root):
    """Reconstruct the producer's decision and require exact selected predecessor bytes."""
    expected, _ = newsroom.analyze(raw_assertion, raw_subject, raw_selection, root=root, raw_previous=raw_prior)
    prior = newsroom.parse(raw_prior, MAX_ARTIFACT)
    correction = newsroom.parse(raw_correction, MAX_ARTIFACT)
    newsroom.require(type(correction.get('recorded_at')) is str)
    correction_time = datetime.fromisoformat(correction['recorded_at'])
    newsroom.require(correction_time.tzinfo is not None)
    prior_time = datetime.fromisoformat(prior['recorded_at'])
    newsroom.require(prior_time <= correction_time <= datetime.now(timezone.utc))

    # The ordinary editorial CLI supplies the decision timestamp. All other
    # fields must equal the validated record, with subject inclusion disabled.
    expected['recorded_at'] = correction['recorded_at']
    newsroom.require(newsroom.encode(correction) == newsroom.encode(expected))
    newsroom.require((correction['decision'], correction['reason']) != (prior['decision'], prior['reason']))
    community.identity(expected['assertion_id'])
    method = {'models': expected['source_models'], 'calibration_id': expected['calibration_id']}
    return {
        'assertion_id': expected['assertion_id'],
        'assertion_sha256': newsroom.sha(raw_assertion),
        'normalized_subject_sha256': expected['subject_sha256'],
        'source_format': expected['source_format'],
        'method_identity_sha256': newsroom.sha(newsroom.encode(method)),
        'prior_journal_sha256': newsroom.sha(raw_prior),
        'review_selection_sha256': newsroom.sha(raw_selection),
        'correction_sha256': newsroom.sha(raw_correction),
        'reviewer_handle': expected['reviewer_handle'],
    }


def load_binding(packet, correction, root):
    packet = community_store.scope(packet)
    correction = Path(correction).expanduser().absolute()
    community_store.scope(correction.parent)
    inputs, previous = read_packet(packet, root, supersede=True)
    return editorial_binding(*inputs, previous, source(correction, root, MAX_ARTIFACT), root=root)


def selected_report_identity(report_id, report):
    immutable_fields = {key: report[key] for key in ('reporter', 'target', 'category', 'created')}
    return newsroom.sha(newsroom.encode({'report_id': report_id, **immutable_fields}))


def plan_record(report_id, report, workbench, moderator, editorial, replacement_id):
    newsroom.require(report['target'] == editorial['assertion_id'])
    newsroom.require(moderator == editorial['reviewer_handle'])
    community.identity(replacement_id)
    newsroom.require(replacement_id not in (report_id, editorial['assertion_id']))
    return {
        'format': PLAN,
        'synthetic_only': True,
        'report_id': report_id,
        'report_identity_sha256': selected_report_identity(report_id, report),
        'workbench_identity_sha256': workbench,
        'replacement_reference_id': replacement_id,
        'moderator': moderator,
        'editorial': editorial,
    }


def prepare(store, registry, report_id, moderator, editorial, *, root):
    registry = community_store.scope(registry)
    report, workbench = read_report(store, report_id, moderator, root)
    newsroom.require(report['state'] == 'open' and report['reviewed_by'] is None
                     and report['disposition'] is None and report['replacement'] is None)
    reference = str(uuid.uuid4())
    plan = plan_record(report_id, report, workbench, moderator, editorial, reference)
    create(registry / ('plan-' + report_id), root, {'plan.json': newsroom.encode(plan)})
    return {'prepared': True, 'replacement_reference_id': reference, 'synthetic_only': True}


def link(store, registry, report_id, moderator, editorial, *, root):
    community.identity(report_id)
    registry = community_store.scope(registry)
    plan_folder = community_store.scope(registry / ('plan-' + report_id))
    raw_plan = source(plan_folder / 'plan.json', root, 16_384)
    prepared = newsroom.parse(raw_plan, 16_384)
    report, workbench = read_report(store, report_id, moderator, root)
    expected = plan_record(report_id, report, workbench, moderator, editorial, prepared.get('replacement_reference_id'))
    newsroom.require(newsroom.encode(prepared) == newsroom.encode(expected))
    newsroom.require(report['state'] == 'reviewed' and report['disposition'] == 'correction_referenced'
                     and report['reviewed_by'] == moderator
                     and report['replacement'] == expected['replacement_reference_id'])
    record = expected.copy()
    record.update(format=LINK, plan_sha256=newsroom.sha(raw_plan), disposition='correction_referenced',
                  source_rewritten=False, network_used=False, independent_accuracy_evidence=False,
                  reviewer_identity_verified=False, selected_history_hops=1)
    create(registry / ('link-' + report_id), root, {'link.json': newsroom.encode(record)})
    return {'linked': True, 'synthetic_only': True}
