#!/usr/bin/env python3
"""Internal bounded pipe worker. Inputs are never sent to a service or logged."""
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import mt_workflow as workflow


def execute(request):
    if not isinstance(request, dict) or set(request) != {'component', 'subject', 'packet'}:
        raise ValueError('Invalid worker request')
    kind = request['component']
    if kind not in workflow.COMPONENTS:
        raise ValueError('Unsupported component')
    text = workflow.subject(request['subject'], 'en')
    sources = workflow.identity(kind)
    rows = []
    if kind == workflow.QUOTATION:
        from tools.mt_quotation_component import produce, replay
        if request['packet'] is None:
            return produce(request['subject'], sources, workflow.LIMITS)
        if type(request['packet']) is not dict or set(request['packet']) != {'replay_record'}:
            raise ValueError('Unsupported quotation replay request')
        return replay(request['subject'], request['packet']['replay_record'], sources, workflow.LIMITS)
    if kind == 'choice':
        from tools.blind_review_io import source
        from protocol import corpus
        from tools import choice_framing
        if not isinstance(request['packet'], str) or not request['packet']:
            raise ValueError('Explicit choice packet required')
        packet = Path(request['packet'])
        packet_text = source(packet / 'subject.txt', ROOT, workflow.MAX_BYTES).decode('utf-8', 'strict')
        if workflow.subject(packet_text, 'en') != text:
            raise ValueError('Packet belongs to another subject')
        record = corpus.parse(source(packet / 'corpus.json', ROOT, corpus.MAX_STORE_BYTES))
        context = workflow.parse(source(packet / 'context.json', ROOT, 32768).decode('utf-8', 'strict'))
        result = choice_framing.observe(text, record, context)
        method = result['profile']
        for item in result['observations']:
            ref = item['additional_reference']
            rows.append({'subject_spans': item['choice_spans'] + item['binary_marker_spans'],
                         'context_span': item['frame_span'], 'construction': item['construction'],
                         'reference': {'sha256': ref['document_sha256'],
                                       'normalized_sha256': ref['normalized_source_sha256'],
                                       'span': ref['source_span']}})
    else:
        if request['packet'] is not None:
            raise ValueError('Unrequested packet')
        from tools.language_observations import observe
        result = observe(kind, text, 'en')
        method = result['method']
        if kind == 'urgency' and result['findings']:
            for item in result['measurements']['paired_units']:
                rows.append({'subject_spans': [item['directive_span'], *item['time_pressure_spans']],
                             'context_span': item['unit_span'], 'reference': None, 'construction': None})
        else:
            for item in result['findings']:
                rows.append({'subject_spans': [list(s) for s in item['spans']],
                             'context_span': item.get('context_span'), 'reference': None, 'construction': None})
    return {'component': kind, 'state': 'OBSERVATIONS' if rows else 'NO_SUPPORTED_PATTERN',
            'method': method, 'subject_sha256': workflow.sha(text.encode()),
            'normalization_id': workflow.NORMALIZATION_ID, 'observations': rows,
            'sources': sources, 'context_selection_performed': kind == 'choice',
            'limitations': dict(workflow.LIMITS)}


def main():
    try:
        raw = sys.stdin.buffer.read(200001)
        if len(raw) > 200000:
            raise ValueError('Oversized request')
        result = execute(workflow.parse(raw))
        print(json.dumps(result, allow_nan=False, ensure_ascii=True))
        return 0
    except Exception:
        # No private exception, path, output or process diagnostics leave a worker.
        print('{"state":"UNAVAILABLE"}')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
