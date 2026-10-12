"""Owner-selected editorial decisions, separate from unsigned preview tag claims."""
from datetime import datetime, timezone
import hashlib
import html
import json
import re
import runpy
import uuid
from pathlib import Path
from protocol.normalization import normalize_nfc, NORMALIZATION_ID
from protocol.evidence import unique, reject, finite
from protocol.replay import inspect_record

PROFILE = 'owner-editorial-review/v1'
SUBJECT_LIMITS = {'gateway-wire-0.1.0': (200_000, 800_000), 'device-preview-v1': (20_000, 80_000)}
DECISIONS = {'needs_review': 'Needs review', 'reviewed': 'Reviewed by the named editor', 'withheld': 'Held back by the editor'}
REASONS = {'needs_context': 'More context is needed.', 'source_checked': 'The editor reports checking the source.',
           'disagreed': 'The editor disagrees with this finding.', 'privacy': 'The editor is holding this back for privacy.',
           'scope_mismatch': 'The tag does not cover the question being asked.'}


def require(value):
    if not value: raise ValueError('Editorial input or record refused.')


def sha(raw): return hashlib.sha256(raw).hexdigest()


def parse(raw, limit):
    require(isinstance(raw, bytes) and 0 < len(raw) <= limit)
    value = json.loads(raw.decode('utf-8'), object_pairs_hook=unique, parse_constant=reject)
    finite(value); require(isinstance(value, dict)); return value


def encode(value): return (json.dumps(value, sort_keys=True, ensure_ascii=True, allow_nan=False) + '\n').encode()


def inspect_source(record, root):
    calibration=record.get('calibration_id')
    if calibration is None:
        require(isinstance(record.get('evaluator'),dict))
        calibration=record['evaluator'].get('calibration_id')
    require(calibration == 'uncalibrated-rules-v6')
    if record.get('spec_version') == '0.1.0':
        require(inspect_record(record, root=root) is None)
        require(datetime.fromisoformat(record['subject']['captured_at'].replace('Z', '+00:00')) <= datetime.now(timezone.utc))
        return 'gateway-wire-0.1.0', record['subject'], record['tags'], record['abstentions'], record['evaluator']['models']
    require(set(record) == {'format','state','subject','candidates','models','calibration_id','redaction_performed',
        'independently_validated','training_label','label_status','text_included','device_runtime','bundle_sha256','record_id'}
        and record['format'] == 'ai-trust-id-device-preview/v1'
        and record['redaction_performed'] is False and record['independently_validated'] is False
        and record['training_label'] is None and record['label_status'] == 'unreviewed_prediction'
        and record['text_included'] is False and record['device_runtime'] == '314.0.7')
    require(isinstance(record['record_id'],str) and str(uuid.UUID(record['record_id']))==record['record_id']
            and uuid.UUID(record['record_id']).version==4)
    subject=record['subject'];require(isinstance(subject,dict) and set(subject)=={'sha256','codepoint_count','normalization'}
        and type(subject['codepoint_count']) is int and 1<=subject['codepoint_count']<=20000
        and subject['normalization']==NORMALIZATION_ID and isinstance(subject['sha256'],str)
        and re.fullmatch(r'[a-f0-9]{64}',subject['sha256']))
    method=(root/'services/evaluator/app.py').read_bytes()
    projection,_=runpy.run_path(str(root/'scripts/build-device-detector.py'))['project'](method)
    require(record['bundle_sha256']==sha(projection)
        and record['models']==[{'name':'rules-only','revision':'context-v6','sha256':sha(method)}])
    candidates=record['candidates'];require(isinstance(candidates,list) and len(candidates)<=1)
    require(record['state']==('FINDING' if candidates else 'NO_FINDING'))
    for candidate in candidates:
        require(isinstance(candidate,dict) and set(candidate)=={'code','confidence','signals'}
            and candidate['code']=='PS' and type(candidate['confidence']) in (int,float)
            and .7<=candidate['confidence']<=1 and isinstance(candidate['signals'],list))
        for signal in candidate['signals']:
            require(isinstance(signal,dict) and set(signal)=={'id','score','spans'}
                and type(signal['score']) in (int,float) and 0<=signal['score']<=1
                and isinstance(signal['spans'],list))
            for span in signal['spans']:
                require(isinstance(span,list) and len(span)==2 and all(type(v) is int for v in span))
        require(candidate['signals'] and candidate['confidence']==max(s['score'] for s in candidate['signals']))
    return 'device-preview-v1',{'sha256':subject['sha256'],'char_len':subject['codepoint_count']},candidates,[],record['models']


def analyze(raw_assertion, raw_subject, raw_selection, *, root, raw_previous=None):
    assertion = parse(raw_assertion, 2_000_000); selection = parse(raw_selection, 16_384)
    require(set(selection) == {'profile', 'assertion_sha256', 'subject_sha256', 'reviewer_handle', 'decision', 'reason', 'previous_record_sha256'})
    require(selection['profile'] == PROFILE and selection['assertion_sha256'] == sha(raw_assertion))
    require(isinstance(selection['reviewer_handle'], str) and re.fullmatch(r'[a-z0-9][a-z0-9_-]{2,63}', selection['reviewer_handle']))
    require(isinstance(selection['decision'], str) and selection['decision'] in DECISIONS and isinstance(selection['reason'], str) and selection['reason'] in REASONS)
    source_format, subject, tags, abstentions, models = inspect_source(assertion, Path(root))
    character_limit, byte_limit = SUBJECT_LIMITS[source_format]
    require(isinstance(raw_subject, bytes) and 0 < len(raw_subject) <= byte_limit)
    text = normalize_nfc(raw_subject.decode('utf-8'))
    require(text.strip() and len(text) <= character_limit and '\x00' not in text)
    require(sha(text.encode()) == subject['sha256'] == selection['subject_sha256'] and len(text) == subject['char_len'])
    require(len(tags) <= 2 and len(abstentions) <= 16 and len({tag['code'] for tag in tags}) == len(tags))
    for row in abstentions:
        require(set(row) == {'code', 'confidence', 'floor', 'reason'}
                and type(row['confidence']) in (int,float) and 0 <= row['confidence'] <= 1)
        if row['code'] == 'PS':
            require(row['reason'] == 'below_floor' and row['floor'] == .7 and row['confidence'] < .7)
        else:
            require(row['code'] != 'PII_REDACTED' and row['reason'] == 'not_in_production_allowlist' and row['floor'] is None)
    for tag in tags:
        require(tag['code'] in {'PS', 'PII_REDACTED'} and 1 <= len(tag['signals']) <= 64)
        expected = {'code', 'confidence', 'signals'}
        if source_format == 'gateway-wire-0.1.0': expected |= {'state'}
        if tag['code'] == 'PS' and source_format == 'gateway-wire-0.1.0': expected |= {'floor'}
        require(set(tag) == expected)
        if tag['code'] == 'PS':
            require((source_format != 'gateway-wire-0.1.0' or tag['floor'] == assertion['evaluator']['preprocessing']['configuration']['rule_floor'])
                    and tag['confidence'] >= .7
                    and tag['confidence'] == max(signal['score'] for signal in tag['signals']))
        else:
            require(tag['confidence'] == 1 and 'floor' not in tag)
        for signal in tag['signals']:
            if tag['code'] == 'PS':
                require(set(signal) == {'id', 'score', 'spans'}
                        and signal['id'] in {'sig.piped_installer.v4','sig.obfuscated_payload.v3','sig.remote_command_substitution.v4','sig.remote_process_substitution.v4','sig.remote_backtick_substitution.v3'})
            else:
                require(set(signal) == {'id', 'score', 'detail'} and signal['id'] == 'presidio.entity.v1' and signal['score'] == 1)
                detail = signal['detail']
                require(set(detail) == {'entities', 'count'} and isinstance(detail['entities'], list)
                        and 1 <= len(detail['entities']) <= 64
                        and all(isinstance(entity, str) and re.fullmatch(r'[A-Z][A-Z0-9_]{1,63}', entity) for entity in detail['entities'])
                        and len(set(detail['entities'])) == len(detail['entities'])
                        and type(detail['count']) is int and len(detail['entities']) <= detail['count'] <= 20000)
            spans = signal.get('spans', [])
            require((tag['code'] != 'PS' or len(spans) >= 1)
                    and len(spans) <= 128 and all(0 <= a < b <= len(text) for a, b in spans))
    previous_hash = selection['previous_record_sha256']
    if raw_previous is None: require(previous_hash is None)
    else:
        previous = parse(raw_previous, 2_000_000)
        require(previous_hash == sha(raw_previous) and previous.get('profile') == PROFILE
                and previous.get('assertion_sha256') == sha(raw_assertion)
                and previous.get('subject_sha256') == selection['subject_sha256']
                and previous.get('source_authenticity_verified') is False
                and previous.get('independent_accuracy_verified') is False
                and previous.get('tag_release_approved') is False
                and previous.get('source_assertion_rewritten') is False
                and previous.get('network_used') is False and previous.get('automatic_collection') is False
                and previous.get('reviewer_identity_verified') is False
                and type(previous.get('subject_included')) is bool
                and previous.get('source_tags') == tags and previous.get('source_abstentions') == abstentions
                and previous.get('source_models') == models
                and previous.get('source_format') == source_format
                and previous.get('calibration_id') == 'uncalibrated-rules-v6'
                and previous.get('decision') in DECISIONS and previous.get('reason') in REASONS
                and isinstance(previous.get('reviewer_handle'), str)
                and re.fullmatch(r'[a-z0-9][a-z0-9_-]{2,63}', previous['reviewer_handle']))
    result = {'profile': PROFILE, 'recorded_at': datetime.now(timezone.utc).isoformat(),
              'assertion_sha256': sha(raw_assertion), 'assertion_id': assertion.get('assertion_id',assertion.get('record_id')), 'source_format': source_format,
              'subject_sha256': subject['sha256'], 'subject_char_len': len(text),
              'normalization_id': NORMALIZATION_ID, 'source_models': models,
              'calibration_id': 'uncalibrated-rules-v6',
              'source_tags': tags, 'source_abstentions': abstentions,
              'reviewer_handle': selection['reviewer_handle'], 'reviewer_identity_verified': False,
              'decision': selection['decision'], 'reason': selection['reason'],
              'previous_record_sha256': previous_hash, 'source_authenticity_verified': False,
              'independent_accuracy_verified': False, 'tag_release_approved': False,
              'source_assertion_rewritten': False, 'subject_included': False,
              'network_used': False, 'automatic_collection': False}
    if raw_previous is not None:
        require(set(previous) == set(result))
        prior_time = datetime.fromisoformat(previous['recorded_at'])
        require(prior_time.tzinfo is not None and prior_time <= datetime.now(timezone.utc))
        require(previous['normalization_id'] == NORMALIZATION_ID and previous['assertion_id'] == assertion.get('assertion_id',assertion.get('record_id'))
                and previous['subject_char_len'] == len(text))
    return result, text


CSS = '''html{color-scheme:light dark;font-family:ui-rounded,system-ui,sans-serif}body{margin:0;background:#f7f8f4;color:#1d2820}main{max-width:48rem;margin:auto;padding:1.5rem}h1{font-size:1.8rem;line-height:1.2}p{line-height:1.6}section{margin:1.25rem 0;padding-top:1rem;border-top:1px solid #bcc6bc}summary{cursor:pointer;width:fit-content;border:1px solid #798b7c;border-radius:.5rem;padding:.4rem .7rem;font-weight:700}details{margin:.7rem 0}summary:focus-visible{outline:3px solid #356747;outline-offset:3px}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-family:inherit;line-height:1.6}small{line-height:1.5;display:block}dd{margin:0 0 .7rem;overflow-wrap:anywhere}dt{font-weight:700}code{overflow-wrap:anywhere}@media(prefers-color-scheme:dark){body{background:#111913;color:#eff5ee}section{border-color:#536457}summary{border-color:#94a997}summary:focus-visible{outline-color:#b2dfb5}}'''


def render(record, text=None):
    e=lambda value: html.escape(str(value), quote=True)
    style_hash=__import__('base64').b64encode(hashlib.sha256(CSS.encode()).digest()).decode()
    require(record['profile'] == PROFILE and record['decision'] in DECISIONS and record['reason'] in REASONS
            and record['subject_included'] is (text is not None))
    chips=''
    for tag in record['source_tags']:
        explanation = ('This source record reports a supported command-risk pattern. It does not establish a scam or malicious intent.' if tag['code']=='PS'
                       else 'The source reports masking detected personal information. Other private information may remain.')
        signals=''.join('<li>'+e(signal['id'])+
                       (' — evaluated-text positions '+e(', '.join(str(a)+'–'+str(b) for a,b in signal.get('spans',[])))
                        if signal.get('spans') else '')+'</li>' for signal in tag['signals'])
        chips += '<details><summary>'+e(tag['code'])+'</summary><p>'+explanation+'</p><p>Preview finding. Independent release validation is not established here.</p><ul>'+signals+'</ul></details>'
    if not chips: chips='<p>No finding in this source record. That is not a safety clearance.</p>'
    if record['source_abstentions']:
        meanings={'below_floor':'Below the source method threshold.', 'no_corpus':'Required references unavailable.',
                  'unsupported_modality':'Input type unsupported.', 'timeout':'Evaluation timed out.',
                  'not_in_production_allowlist':'Capability not enabled.'}
        chips += '<h3>Withheld by the source</h3><ul>'+''.join('<li>'+e(row['code'])+' — '+e(meanings[row['reason']])+'</li>' for row in record['source_abstentions'])+'</ul>'
    subject='<p>The subject is not included. Compare this record alongside your own source document.</p>'
    if text is not None:
        require(sha(text.encode())==record['subject_sha256'] and len(text)==record['subject_char_len'])
        subject='<p>You chose to include this evaluated text in this private file. Redaction may miss sensitive information; review before sharing.</p><pre>'+e(text)+'</pre>'
    previous = '<p>This supersedes the selected prior private record. Keep both files if you need the history.</p>' if record['previous_record_sha256'] else ''
    title='Editorial review'
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'sha256-'+style_hash+'\'; base-uri \'none\'; form-action \'none\'; frame-src \'none\'; connect-src \'none\'">'
            '<title>'+title+' · AI Trust ID</title><style>'+CSS+'</style></head><body><main><p>AI TRUST ID</p><h1>'+title+'</h1>'
            '<p>Read the source finding, then consider the editor’s separate decision. Neither verifies the truth of the content.</p>'
            '<section aria-labelledby="choice"><h2 id="choice">Editor’s decision</h2><p>'+e(DECISIONS[record['decision']])+'</p><p>'+e(REASONS[record['reason']])+'</p><small>Declared reviewer: '+e(record['reviewer_handle'])+'. Identity is not authenticated.</small>'+previous+'</section>'
            '<section aria-labelledby="tags"><h2 id="tags">Source findings</h2>'+chips+'</section>'
            '<section aria-labelledby="subject"><h2 id="subject">Selected subject</h2>'+subject+'</section>'
            '<details><summary>Record details</summary><dl><dt>Source format</dt><dd>'+e(record['source_format'])+'</dd><dt>Source record identifier</dt><dd>'+e(record['assertion_id'] or 'Not supplied by this preview format')+'</dd><dt>Method</dt><dd>'+e(record['calibration_id'])+'</dd><dt>Recorded</dt><dd>'+e(record['recorded_at'])+'</dd></dl><p>Unsigned source authenticity and independent accuracy are not verified. Scores are rule values, not measured chances. Method identities match the selected current checkout; that is not proof the producer ran it. Hashes in the private JSON can correlate content and are not anonymity.</p></details>'
            '<section><h2>Your files, your choice</h2><p>This static page makes no network request, uses no account and uploads nothing. Keep its JSON private, review before sharing, and delete the private output folder when you no longer need it. Your existing personal checker is unchanged.</p></section></main></body></html>').encode()
