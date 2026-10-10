"""Explicit seeded decisions; recording a proposal never accepts it."""
from datetime import datetime, timezone
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
IDS = {'D1','D3','D4','D5','D11','D12','D13','D14','D15','D16','D17','D18','D19','D20','D21'}

def dated(value):
    stamp = datetime.fromisoformat(value)
    if stamp.tzinfo is None or stamp > datetime.now(timezone.utc):
        raise ValueError('Decision date must be an observed, timezone-aware date')

def validate(data):
    if data.get('schema_version') != 1 or data.get('operating_institution') is not False:
        raise ValueError('Unsupported decision ledger')
    dated(data['recorded_at'])
    rows = data['decisions']
    if len(rows) != len(IDS) or {r['id'] for r in rows} != IDS:
        raise ValueError('Seed decision IDs changed or duplicated')
    for row in rows:
        dated(row['recorded_at'])
        if row['status'] != 'open' or row['decision_at'] is not None or row['accepted_by'] is not None or row['acceptance_evidence'] is not None:
            raise ValueError('Seed ledger cannot manufacture an acceptance')
        if row['owner'] not in ('Michael','Michael + counsel'):
            raise ValueError('Decision owner must be accountable')
        if any(not isinstance(row[k], str) or not row[k].strip() for k in ('question','reason')):
            raise ValueError('Decision needs a question and reason')
    return rows

def render(data, history):
    rows = validate(data)
    out = '# Decisions\n\nMachine source: [dated decision ledger](docs/decisions.json). '
    out += 'The 15 existing open decisions were recorded at **'+data['recorded_at']+'**. '
    out += 'This is a recording date, not an invented historical decision or approval. '
    out += 'Each proposal keeps its owner, reason and separate acceptance. No operating board is implied.\n\n'
    out += '| ID | Status | Owner | Decision | Reason | Blocks |\n|---|---|---|---|---|---|\n'
    for r in rows:
        cell = lambda v: str(v or '—').replace('|', '\\|').replace('\n',' ')
        out += '| '+' | '.join(cell(r[k]) for k in ('id','status','owner','question','reason','blocks'))+' |\n'
    out += '\nHistoric observations below retain their dates and limits. Later dated entries supersede earlier deployment/purchase status; they are not fresh runtime checks.\n\n'
    return out + history.removeprefix('# Preserved decision history\n\n')

def verify(root=ROOT):
    data = json.loads((root/'docs/decisions.json').read_text())
    expected = render(data, (root/'docs/decision-history.md').read_text())
    if (root/'DECISIONS.md').read_text() != expected:
        raise ValueError('Decision prose differs from dated source or preserved history')
    return {'pass':True,'open_seed_decisions':len(data['decisions']),
            'owner_acceptances_invented':False,'operating_board':False}
