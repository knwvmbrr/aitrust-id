"""Recalculate environment-specific timing summaries from input-free observations."""
import math

def validate_timing(timing,total):
    if type(total) is not int or total<1 or timing.get('sample_count')!=total:raise ValueError('Invalid timing denominator')
    rows=timing.get('samples')
    if not isinstance(rows,list) or len(rows)!=total:raise ValueError('Missing timing observations')
    ids=set()
    for row in rows:
        if not isinstance(row.get('case_id'),str) or not row['case_id'] or row['case_id'] in ids:raise ValueError('Duplicate/missing timing identity')
        ids.add(row['case_id'])
        duration=row.get('duration_ms')
        if type(duration) not in (int,float) or not math.isfinite(duration) or duration<0:raise ValueError('Invalid timing duration')
        if type(row.get('input_length_codepoints')) is not int or row['input_length_codepoints']<0 or not isinstance(row.get('category'),str):raise ValueError('Invalid timing metadata')
    def check(samples,summary):
        values=sorted(r['duration_ms'] for r in samples)
        if summary.get('sample_count')!=len(values) or summary.get('p50_ms')!=values[math.ceil(len(values)*.5)-1] or summary.get('p95_ms')!=values[math.ceil(len(values)*.95)-1]:raise ValueError('Timing summary differs from observations')
    check(rows,timing)
    categories=set(r['category'] for r in rows)
    if set(timing.get('per_category',{}))!=categories:raise ValueError('Missing category timing')
    for category in categories:check([r for r in rows if r['category']==category],timing['per_category'][category])
    lengths=[r['input_length_codepoints'] for r in rows]
    if timing.get('input_lengths_codepoints')!={'min':min(lengths),'max':max(lengths)}:raise ValueError('Invalid declared input sizes')
    cold=timing.get('cold_load_ms')
    if type(cold) not in (int,float) or not math.isfinite(cold) or cold<0:raise ValueError('Invalid cold-load observation')
    return timing


# IEEE-754/libm implementations can differ by an ulp. This bound is for Wilson
# interval endpoints only, never counts, points, denominators, hashes or gates.
WILSON_ENDPOINT_ABS_TOLERANCE = 1e-14

def measurements_match(published, recomputed):
    """Strict structural/value comparison with bounded interval-only arithmetic."""
    if isinstance(recomputed, dict):
        if not isinstance(published, dict) or set(published) != set(recomputed):
            return False
        for key, expected in recomputed.items():
            actual = published[key]
            if key == 'interval' and isinstance(expected, list):
                if (not isinstance(actual, list) or len(actual) != 2 or len(expected) != 2
                        or any(type(x) not in (int, float) or not math.isfinite(x)
                               or not 0 <= x <= 1 for x in actual + expected)
                        or actual[0] > actual[1] or expected[0] > expected[1]
                        or any(abs(a-b) > WILSON_ENDPOINT_ABS_TOLERANCE
                               for a,b in zip(actual, expected))):
                    return False
            elif not measurements_match(actual, expected):
                return False
        return True
    if isinstance(recomputed, list):
        return (isinstance(published, list) and len(published) == len(recomputed)
                and all(measurements_match(a,b) for a,b in zip(published,recomputed)))
    if type(published) is not type(recomputed):
        return False
    if isinstance(recomputed, float) and (not math.isfinite(recomputed)
                                          or not math.isfinite(published)):
        return False
    return published == recomputed
