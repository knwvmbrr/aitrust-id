"""Exercise the bridge using the actual editorial and community commands."""
import json
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

from test_assertion_replay import assertion
from test_newsroom import TEXT, device_record
from tools import community_core, newsroom

ROOT = Path(__file__).resolve().parents[1]


def call(script, *args, payload=None):
    return subprocess.run([sys.executable, str(ROOT / 'scripts' / script), *map(str, args)],
                          input=payload, capture_output=True, timeout=15)


def output(result):
    assert result.returncode == 0 and not result.stderr, result.stderr
    return json.loads(result.stdout)


class Case:
    def __init__(self, parent, finding, include_subject=False, decision='withheld', reason='disagreed'):
        self.parent = parent
        parent.chmod(0o700)
        self.store = parent / 'community'
        self.registry = parent / 'registry'
        self.registry.mkdir(mode=0o700)
        self.source = parent / 'source.json'
        self.subject = parent / 'subject.txt'
        self.assertion_id = finding.get('assertion_id', finding.get('record_id'))
        self.report_id = str(uuid.uuid4())
        self.source.write_bytes(newsroom.encode(finding))
        self.subject.write_bytes(TEXT)
        self.source.chmod(0o600)
        self.subject.chmod(0o600)

        def prepare_review(packet, reviewer, choice, reason_code, previous=None):
            args = ['--source', self.source, '--subject', self.subject, '--reviewer', reviewer,
                    '--decision', choice, '--reason', reason_code, '--output', packet, '--reviewed-record']
            if previous is not None:
                args.extend(['--previous', previous])
            output(call('prepare-editorial-review.py', *args))

        prior_packet = parent / 'prior-packet'
        prior_output = parent / 'prior-output'
        prepare_review(prior_packet, 'editor-one', 'needs_review', 'needs_context')
        output(call('editorial-review.py', '--packet', prior_packet, '--output', prior_output, '--reviewed-record'))
        self.prior = prior_output / 'editorial-review.json'
        self.packet = parent / 'correction-packet'
        correction_folder = parent / 'correction-output'
        prepare_review(self.packet, 'mod-one', decision, reason, self.prior)
        args = ['--packet', self.packet, '--output', correction_folder, '--reviewed-record', '--supersede']
        if include_subject:
            args.append('--include-subject')
        output(call('editorial-review.py', *args))
        self.correction = correction_folder / 'editorial-review.json'
        output(call('community-workbench.py', 'init', '--root', self.store, '--synthetic-only'))

    def add_report(self, target=None, reporter='user-one', category='wrong_result'):
        return self.action(reporter, 'report', {'target_id': target or self.assertion_id,
                           'category': category, 'consent_private_metadata': True}, request_id=self.report_id)

    def action(self, actor, operation, data, request_id=None):
        payload = community_core.encode({'format': community_core.REQUEST, 'synthetic_only': True,
                  'request_id': request_id or str(uuid.uuid4()), 'operation': operation, 'data': data})
        return output(call('community-workbench.py', 'apply', '--root', self.store, '--actor', actor, payload=payload))

    def run(self, operation, *, moderator='mod-one', store=None, confirm=True):
        opts = ['--confirm-synthetic-link'] if confirm else []
        return call('link-dispute-correction.py', operation, '--workbench', store or self.store,
                    '--registry', self.registry, '--report', self.report_id, '--moderator', moderator,
                    '--packet', self.packet, '--correction', self.correction, *opts)

    def close(self, replacement, *, moderator='mod-one', disposition='correction_referenced'):
        self.action(moderator, 'review_report', {'report_id': self.report_id, 'disposition': disposition,
                    'replacement_record_id': replacement})

    def refused(self, result):
        assert result.returncode == 2 and not result.stdout
        assert b'Traceback' not in result.stderr and b'PRIVATE_LINK_CANARY' not in result.stderr
        assert str(self.parent).encode() not in result.stderr and TEXT not in result.stderr
        assert not self.link_file.exists()

    @property
    def link_file(self):
        return self.registry / ('link-' + self.report_id) / 'link.json'


@pytest.mark.parametrize('producer', ['gateway', 'browser'])
def test_real_producer_and_review_link_exact_artifacts_and_refuse_replay(tmp_path, assertion, device_record, producer):
    selected = assertion if producer == 'gateway' else device_record
    case = Case(tmp_path, selected)
    case.add_report()
    inputs = (case.source.read_bytes(), case.subject.read_bytes(), case.prior.read_bytes(), case.correction.read_bytes())
    prepared = output(case.run('prepare'))
    replacement = prepared['replacement_reference_id']
    assert community_core.identity(replacement) != case.assertion_id
    assert case.run('prepare').returncode == 2
    case.refused(case.run('link'))
    case.close(replacement)
    case.action('user-two', 'submit', {'body': 'Unrelated pending discussion', 'consent_public': True})
    assert output(case.run('link')) == {'linked': True, 'synthetic_only': True}
    saved = case.link_file.read_bytes()
    proof = json.loads(saved)
    assert proof['format'] == 'private-dispute-correction-link/v1'
    assert proof['report_id'] == case.report_id and proof['replacement_reference_id'] == replacement
    assert proof['editorial']['assertion_id'] == case.assertion_id
    assert proof['editorial']['assertion_sha256'] == newsroom.sha(inputs[0])
    assert proof['editorial']['prior_journal_sha256'] == newsroom.sha(inputs[2])
    assert proof['editorial']['correction_sha256'] == newsroom.sha(inputs[3])
    assert proof['reviewer_identity_verified'] is False and proof['selected_history_hops'] == 1
    assert TEXT not in saved and b'source_tags' not in saved and str(tmp_path).encode() not in saved
    assert case.link_file.parent.stat().st_mode & 0o777 == 0o700
    assert case.link_file.stat().st_mode & 0o777 == 0o600
    assert case.run('link').returncode == 2 and case.link_file.read_bytes() == saved
    assert inputs == (case.source.read_bytes(), case.subject.read_bytes(), case.prior.read_bytes(), case.correction.read_bytes())
    for projection in ('public', 'replay'):
        result = call('community-workbench.py', projection, '--root', case.store)
        assert result.returncode == 0 and case.report_id.encode() not in result.stdout and replacement.encode() not in result.stdout


@pytest.mark.parametrize('conflict', ['target', 'category', 'reporter', 'moderator', 'include_subject', 'same_decision', 'no_confirmation'])
def test_prepare_requires_selected_open_dispute_and_real_changed_correction(tmp_path, device_record, conflict):
    options = {'include_subject': conflict == 'include_subject'}
    if conflict == 'same_decision':
        options.update(decision='needs_review', reason='needs_context')
    case = Case(tmp_path, device_record, **options)
    case.add_report(target=str(uuid.uuid4()) if conflict == 'target' else None,
                    category='privacy' if conflict == 'category' else 'wrong_result',
                    reporter='mod-one' if conflict == 'reporter' else 'user-one')
    case.refused(case.run('prepare', moderator='mod-two' if conflict == 'moderator' else 'mod-one',
                          confirm=conflict != 'no_confirmation'))
    assert list(case.registry.iterdir()) == []


@pytest.mark.parametrize('conflict', ['wrong_replacement', 'different_moderator', 'other_disposition', 'copied_database', 'replacement_database_file',
                                     'previous_bytes', 'review_selection_bytes', 'correction_bytes', 'changed_method',
                                     'fake_accuracy', 'future_time', 'public_correction'])
def test_link_refuses_stale_mutated_or_different_workbench_evidence(tmp_path, device_record, conflict):
    case = Case(tmp_path, device_record)
    case.add_report()
    replacement = output(case.run('prepare'))['replacement_reference_id']
    if conflict == 'wrong_replacement':
        replacement = str(uuid.uuid4())
    case.close(None if conflict == 'other_disposition' else replacement,
               moderator='mod-two' if conflict == 'different_moderator' else 'mod-one',
               disposition='no_change' if conflict == 'other_disposition' else 'correction_referenced')
    store = case.store
    if conflict == 'copied_database':
        store = tmp_path / 'lookalike'
        shutil.copytree(case.store, store)
        assert (store / 'community.sqlite').read_bytes() == (case.store / 'community.sqlite').read_bytes()
    elif conflict == 'replacement_database_file':
        database = store / 'community.sqlite'
        original_inode = database.stat().st_ino
        duplicate = store / 'replacement.sqlite'
        shutil.copy2(database, duplicate)
        duplicate.replace(database)
        assert database.stat().st_ino != original_inode
    elif conflict in ('previous_bytes', 'review_selection_bytes', 'correction_bytes'):
        selected = {'previous_bytes': case.packet / 'previous.json', 'review_selection_bytes': case.packet / 'review.json',
                    'correction_bytes': case.correction}[conflict]
        selected.write_bytes(selected.read_bytes() + b'\n')
    elif conflict == 'public_correction':
        case.correction.chmod(0o644)
    elif conflict == 'changed_method':
        selected = case.packet / 'source.json'
        changed = json.loads(selected.read_bytes())
        changed['models'][0]['sha256'] = '0' * 64
        selected.write_bytes(newsroom.encode(changed))
    elif conflict in ('fake_accuracy', 'future_time'):
        changed = json.loads(case.correction.read_bytes())
        if conflict == 'fake_accuracy':
            changed['independent_accuracy_verified'] = True
            changed['private_note'] = 'PRIVATE_LINK_CANARY'
        else:
            changed['recorded_at'] = '2099-11-17T00:00:00+00:00'
        case.correction.write_bytes(newsroom.encode(changed))
    case.refused(case.run('link', store=store))
