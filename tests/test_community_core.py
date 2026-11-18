import copy
import json
import uuid
import pytest
from tools import community_core as c


def request(op, data, rid=None):
    return {'format': c.REQUEST, 'synthetic_only': True, 'request_id': rid or str(uuid.uuid4()), 'operation': op, 'data': data}


def run(engine, actor, op, data, now=1000): return engine.apply(actor, request(op, data), now)


def submit(engine, actor='user-one', text='Invented community question.', now=1000):
    return run(engine, actor, 'submit', {'body': text, 'consent_public': True}, now)


def published(engine, actor='user-one', text='Invented community question.', now=1000):
    p = submit(engine, actor, text, now)
    return run(engine, 'mod-one', 'approve', {'post_id': p['id'], 'version': p['version']}, now)


def test_two_users_official_and_moderator_have_distinct_reviewed_outcomes():
    e = c.Community(); a = submit(e); b = submit(e, 'user-two'); o = submit(e, 'official-one')
    assert e.public()['items'] == []
    assert set(e.private('user-one')['posts']) == {a['id']}
    for post in (a, b, o): run(e, 'mod-one', 'approve', {'post_id': post['id'], 'version': 1})
    public = e.public(); assert len(public['items']) == 3
    assert sum(x['official'] for x in public['items']) == 1
    assert public['training_consent'] is False
    assert not any(x in c.encode(public).decode() for x in c.ACTORS)


@pytest.mark.parametrize('actor', ['user-two', 'official-one', 'admin-one'])
def test_non_moderator_cannot_approve_another_user(actor):
    e = c.Community(); p = submit(e); before = copy.deepcopy(e.state)
    with pytest.raises(c.Refused): run(e, actor, 'approve', {'post_id': p['id'], 'version': 1})
    assert e.state == before


@pytest.mark.parametrize('data', [{'body': 'PRIVATE_CANARY', 'consent_public': False},
    {'body': 'PRIVATE_CANARY', 'consent_public': 1}, {'body': 'PRIVATE_CANARY', 'consent_public': True, 'role': 'moderator'},
    {'body': 'PRIVATE_CANARY\x1b[2J', 'consent_public': True}, {'body': 'x'*2001, 'consent_public': True},
    {'body': '\u202esecret', 'consent_public': True}, {'body': '   ', 'consent_public': True}])
def test_consent_closed_payload_and_hostile_control_refusals_do_not_mutate(data):
    e = c.Community(); before = copy.deepcopy(e.state)
    with pytest.raises(c.Refused) as error: run(e, 'user-one', 'submit', data)
    assert e.state == before and 'PRIVATE_CANARY' not in str(error.value)


def test_private_report_is_metadata_only_and_never_reaches_public_or_audit():
    e = c.Community(); target = str(uuid.uuid4())
    p = run(e, 'user-one', 'report', {'target_id': target, 'category': 'security', 'consent_private_metadata': True})
    assert e.private('user-two')['reports'] == {}
    assert p['id'] in e.private('mod-one')['reports']
    with pytest.raises(c.Refused): run(e, 'user-one', 'report', {'target_id': target, 'category': 'security', 'consent_private_metadata': True, 'body': 'PRIVATE_CANARY'})
    for value in [e.public(), e.replay(), e.state['audit']]:
        text = c.encode(value).decode(); assert target not in text and 'security' not in text and 'PRIVATE_CANARY' not in text
    run(e, 'mod-two', 'review_report', {'report_id': p['id'], 'disposition': 'needs_evidence', 'replacement_record_id': None})
    assert e.private('user-one')['reports'][p['id']]['state'] == 'reviewed'


def test_retry_conflict_and_cross_actor_request_replay():
    e = c.Community(); req = request('submit', {'body': 'Example', 'consent_public': True})
    a = e.apply('user-one', req, 1000); snapshot = copy.deepcopy(e.state)
    assert e.apply('user-one', req, 1000) == a and e.state == snapshot
    with pytest.raises(c.Refused): e.apply('user-two', req, 1000)
    req['data']['body'] = 'Changed'
    with pytest.raises(c.Refused): e.apply('user-one', req, 1000)


def test_edit_hides_previous_text_until_fresh_approval_and_invalidates_old_cache():
    e = c.Community(); a = published(e, text='FIRST_PRIVATE_CANARY')
    cache = c.update_cache({'sequence': 0, 'items': {}}, e.replay())
    assert cache['items'][a['id']]['body'] == 'FIRST_PRIVATE_CANARY'
    edit = run(e, 'user-one', 'edit', {'post_id': a['id'], 'version': a['version'], 'body': 'Revised example', 'consent_public': True})
    values = [e.public(), e.replay(), e.state]
    assert all('FIRST_PRIVATE_CANARY' not in c.encode(x).decode() for x in values)
    updated = c.update_cache(cache, e.replay(after=cache['sequence']))
    assert updated['items'][a['id']]['body'] is None
    with pytest.raises(c.Refused): run(e, 'mod-two', 'approve', {'post_id': a['id'], 'version': a['version']})
    run(e, 'mod-two', 'approve', {'post_id': a['id'], 'version': edit['version']})
    assert e.public()['items'][0]['body'] == 'Revised example'


def test_retraction_scrubs_prior_body_replay_export_and_idempotency_hash():
    e = c.Community(); req = request('submit', {'body': 'REMOVED_PRIVATE_CANARY', 'consent_public': True})
    a = e.apply('user-one', req, 1000); a = run(e, 'mod-one', 'approve', {'post_id': a['id'], 'version': 1})
    removed = run(e, 'mod-one', 'retract', {'post_id': a['id'], 'version': a['version'], 'reason': 'privacy'})
    assert 'REMOVED_PRIVATE_CANARY' not in c.encode(e.state).decode()
    assert e.state['requests'][req['request_id']]['digest'] is None
    with pytest.raises(c.Refused): e.apply('user-one', req, 1000)
    for value in [e.public(), e.replay()]: assert 'REMOVED_PRIVATE_CANARY' not in c.encode(value).decode()
    assert e.public()['items'][0]['body'] is None
    assert e.public()['items'][0]['reason_category'] == 'privacy'
    assert e.public()['items'][0]['appeal'] == 'independent_review_requested_privately'
    assert 'REMOVED_PRIVATE_CANARY' not in c.render(e.public())
    assert removed['version'] == 3


def test_independent_appeal_reconsideration_does_not_restore_removed_text():
    e = c.Community(); a = published(e)
    a = run(e, 'mod-one', 'suspend', {'post_id': a['id'], 'version': a['version'], 'reason': 'conduct'})
    with pytest.raises(c.Refused): submit(e)
    appeal = run(e, 'user-one', 'appeal', {'post_id': a['id'], 'version': a['version']})
    with pytest.raises(c.Refused): run(e, 'mod-one', 'resolve_appeal', {'appeal_id': appeal['id'], 'decision': 'reconsider'})
    with pytest.raises(c.Refused): run(e, 'user-two', 'resolve_appeal', {'appeal_id': appeal['id'], 'decision': 'reconsider'})
    run(e, 'mod-two', 'resolve_appeal', {'appeal_id': appeal['id'], 'decision': 'reconsider'})
    assert e.state['actors']['user-one']['restriction'] == 'active'
    assert e.public()['items'][0]['body'] is None
    assert submit(e)['id'] != a['id']


def test_appeal_does_not_clear_a_separate_restriction():
    e = c.Community(); a = published(e); b = published(e)
    a = run(e, 'mod-one', 'restrict', {'post_id': a['id'], 'version': a['version'], 'reason': 'conduct'})
    b = run(e, 'mod-two', 'suspend', {'post_id': b['id'], 'version': b['version'], 'reason': 'conduct'})
    appeal = run(e, 'user-one', 'appeal', {'post_id': a['id'], 'version': a['version']})
    run(e, 'mod-two', 'resolve_appeal', {'appeal_id': appeal['id'], 'decision': 'reconsider'})
    assert e.state['actors']['user-one']['restriction'] == 'suspended'


def test_correction_requires_fresh_review_and_preserves_safe_supersession_link():
    e = c.Community(); old = published(e, text='OLD_PRIVATE_CANARY')
    new = run(e, 'user-one', 'supersede', {'post_id': old['id'], 'version': old['version'], 'body': 'Corrected example', 'consent_public': True})
    assert e.public()['items'][0]['body'] == 'OLD_PRIVATE_CANARY'
    run(e, 'mod-two', 'approve', {'post_id': new['id'], 'version': 1})
    assert 'OLD_PRIVATE_CANARY' not in c.encode(e.state).decode()
    rows = {x['id']: x for x in e.public()['items']}
    assert rows[old['id']]['state'] == 'superseded' and rows[old['id']]['replacement'] == new['id']
    assert rows[new['id']]['body'] == 'Corrected example'


def test_safe_html_does_not_execute_markup_or_fetch_embedded_resource():
    e = c.Community(); published(e, text='<img src="https://example.invalid" onerror="alert(1)"><script>bad()</script>')
    rendered = c.render(e.public())
    assert '<script>' not in rendered and '<img' not in rendered and '&lt;script&gt;' in rendered
    assert 'default-src &#39;none&#39;' in rendered


def test_throttle_clock_rollback_and_pause_are_explicit_and_isolated():
    e = c.Community()
    for i in range(8): submit(e, text=f'Invented {i}')
    with pytest.raises(c.Refused): submit(e)
    submit(e, now=1060)
    with pytest.raises(c.Refused): submit(e, now=1059)
    run(e, 'admin-one', 'pause', {'paused': True}, 1060)
    with pytest.raises(c.Refused): submit(e, 'user-two', now=1060)
    assert e.public()['items'] == []
    run(e, 'admin-one', 'pause', {'paused': False}, 1060)
    submit(e, 'user-two', now=1060)


def test_replay_is_bounded_reset_discards_stale_cache_and_order_must_match():
    e = c.Community(); a = published(e)
    e.state['public_sequence'] = 200; e.state['events'] = [{'sequence': i, 'post': a['id']} for i in range(73, 201)]
    c.validate(e.state)
    batch = e.replay(after=0); assert batch['reset_required'] is True
    assert c.update_cache({'sequence': 1, 'items': {a['id']: {'body': 'PRIVATE_CANARY'}}}, batch) == {'sequence': 0, 'items': {}}
    normal = e.replay(after=72); assert len(normal['events']) == 20
    with pytest.raises(c.Refused): c.update_cache({'sequence': 0, 'items': {}}, normal)


def test_state_roundtrip_retains_roles_and_rejects_corrupt_publication():
    e = c.Community(); a = published(e); assert c.Community(c.parse(c.encode(e.state), 8*1024*1024)).public() == e.public()
    bad = copy.deepcopy(e.state); bad['actors']['user-one']['role'] = 'moderator'
    with pytest.raises(c.Refused): c.Community(bad)
    bad = copy.deepcopy(e.state); bad['posts'][a['id']]['approved_by'] = None
    with pytest.raises(c.Refused): c.Community(bad)


@pytest.mark.parametrize('raw', [b'{"a":1,"a":2}', b'{"a":NaN}', b'\xff', b'[]'*9000])
def test_duplicate_nonfinite_invalid_and_oversized_json_refuse(raw):
    with pytest.raises(c.Refused): c.parse(raw)


def test_official_reply_is_linked_but_requires_its_own_review():
    e = c.Community(); parent = published(e, 'user-one')
    reply = run(e, 'official-one', 'reply', {'post_id': parent['id'], 'version': parent['version'], 'body': 'Invented official reply.', 'consent_public': True})
    assert len(e.public()['items']) == 1
    run(e, 'mod-two', 'approve', {'post_id': reply['id'], 'version': 1})
    rows = {x['id']: x for x in e.public()['items']}
    assert rows[reply['id']]['reply_to'] == parent['id'] and rows[reply['id']]['official']
    pending = submit(e, 'user-two')
    with pytest.raises(c.Refused): run(e, 'official-one', 'reply', {'post_id': pending['id'], 'version': 1, 'body': 'Not public yet', 'consent_public': True})


def test_dispute_resolution_records_separate_proposed_correction_without_rewriting_tag():
    e = c.Community(); original = str(uuid.uuid4()); replacement = str(uuid.uuid4())
    report = run(e, 'user-one', 'report', {'target_id': original, 'category': 'wrong_result', 'consent_private_metadata': True})
    run(e, 'mod-one', 'review_report', {'report_id': report['id'], 'disposition': 'correction_referenced', 'replacement_record_id': replacement})
    own = e.private('user-one')['reports'][report['id']]
    assert own['target'] == original and own['replacement'] == replacement and own['reviewed_by'] == 'mod-one'
    assert original not in c.encode(e.public()).decode() and replacement not in c.encode(e.replay()).decode()
    assert e.audit('mod-two')['bodies_included'] is False
    with pytest.raises(c.Refused): e.audit('user-two')


def test_audit_capacity_reserves_pause_and_retraction_without_pruning():
    e = c.Community(); p = published(e, text='REMOVE_AT_CAPACITY_CANARY')
    row = copy.deepcopy(e.state['audit'][0])
    e.state['audit'] = [copy.deepcopy(row) for _ in range(c.MAX_AUDIT-c.MAX_POSTS-1)]
    e.state['revision'] = c.MAX_AUDIT-c.MAX_POSTS-1
    c.validate(e.state)
    before = len(e.state['audit'])
    with pytest.raises(c.Refused): submit(e, 'user-two')
    run(e, 'admin-one', 'pause', {'paused': True})
    with pytest.raises(c.Refused): run(e, 'admin-one', 'pause', {'paused': False})
    with pytest.raises(c.Refused): run(e, 'admin-one', 'pause', {'paused': True})
    run(e, 'mod-one', 'retract', {'post_id': p['id'], 'version': p['version'], 'reason': 'privacy'})
    assert len(e.state['audit']) == before+2
    assert 'REMOVE_AT_CAPACITY_CANARY' not in c.encode(e.state).decode()
