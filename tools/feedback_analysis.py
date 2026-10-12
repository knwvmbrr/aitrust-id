"""Private synthetic feedback distributions; no accuracy, people or anomaly verdict."""
from collections import Counter
from fractions import Fraction
import json
import math
from tools.research_admission import metadata, CHOICES, FIXED, AdmissionError, unique

PROFILE = 'synthetic-feedback-batch/1.0.0'
RESULT = 'synthetic-feedback-comparison/1.0.0'
MAX_BYTES = 2_000_000
MAX_RECORDS = 5000


class AnalysisError(ValueError):
    pass


def require(ok):
    if not ok: raise AnalysisError('Private synthetic feedback contract refused.')


def finite(value):
    v = float(value); require(math.isfinite(v)); return v


def validate_batch(batch):
    require(type(batch) is dict and set(batch) == {'profile', 'synthetic', 'records'})
    require(batch['profile'] == PROFILE and batch['synthetic'] is True)
    require(type(batch['records']) is list and 1 <= len(batch['records']) <= MAX_RECORDS)
    captured = []
    for record in batch['records']:
        require(type(record) is dict)
        row = dict(record)
        metadata(row)
        captured.append(row)
    return {'profile': PROFILE, 'synthetic': True, 'records': captured}


def parse(raw):
    require(type(raw) is bytes and 0 < len(raw) <= MAX_BYTES)
    try:
        batch = json.loads(raw.decode('utf-8', 'strict'), object_pairs_hook=unique,
            parse_float=finite, parse_constant=lambda _: require(False))
        return validate_batch(batch)
    except (ValueError, TypeError, KeyError, UnicodeError, RecursionError):
        raise AnalysisError('Private synthetic feedback contract refused.') from None


def distribution(batch):
    fields = tuple(CHOICES)
    records = batch['records']; n = len(records)
    combinations = Counter(tuple(record[field] for field in fields) for record in records)
    return {'records': n, 'unique_metadata_combinations': len(combinations),
        'repeated_metadata_combinations': sum(count > 1 for count in combinations.values()),
        'records_in_repeated_combinations': sum(count for count in combinations.values() if count > 1),
        'categories': {field: {choice: sum(record[field] == choice for record in records)
            for choice in choices} for field, choices in CHOICES.items()}}


def compare(first, second, minimum_records=20, percentage_points=10):
    require(type(minimum_records) is int and 1 <= minimum_records <= MAX_RECORDS)
    require(type(percentage_points) in (int, float) and 0 < percentage_points <= 100
            and math.isfinite(percentage_points))
    require(len(str(percentage_points)) <= 12)
    # Revalidate each captured object; caller-defined real or mixed records refuse.
    try:
        a, b = validate_batch(first), validate_batch(second)
    except (ValueError, TypeError, KeyError):
        raise AnalysisError('Private synthetic feedback contract refused.') from None
    before, after = distribution(a), distribution(b)
    sufficient = min(before['records'], after['records']) >= minimum_records
    threshold = Fraction(str(percentage_points)) / 100
    rows = []
    for field, choices in CHOICES.items():
        for choice in choices:
            x, y = before['categories'][field][choice], after['categories'][field][choice]
            delta = Fraction(y, after['records']) - Fraction(x, before['records'])
            rows.append({'field': field, 'choice': choice,
                'before_count': x, 'before_records': before['records'],
                'after_count': y, 'after_records': after['records'],
                'percentage_point_change': round(float(delta * 100), 6),
                'direction': 'increase' if delta > 0 else 'decrease' if delta < 0 else 'unchanged',
                'inspection_prompt': sufficient and abs(delta) >= threshold})
    return {'profile': RESULT, 'synthetic_only': True, 'tag': FIXED['tag'], 'method_version': FIXED['method_version'],
        'before': before, 'after': after, 'comparisons': rows,
        'inspection_rule': {'minimum_records_in_each_batch': minimum_records, 'absolute_percentage_point_change': percentage_points},
        'state': ('descriptive_changes' if any(row['direction'] != 'unchanged' for row in rows)
                  else 'no_category_rate_change') if sufficient else 'insufficient_records_for_selected_inspection_rule',
        'records_are_people': False, 'repeated_metadata_establishes_duplicate_people': False,
        'reports_are_verified_errors': False, 'accuracy_measured': False, 'anomaly_diagnosed': False,
        'independent_evidence': False, 'training_labels_created': False, 'tags_asserted': [], 'network_used': False}
