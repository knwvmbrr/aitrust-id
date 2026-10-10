"""A libm ulp may vary; substantive evidence and release thresholds may not."""
from copy import deepcopy
import math
import pytest
from protocol.measurements import measurements_match, WILSON_ENDPOINT_ABS_TOLERANCE

BASE = {'counts': {'tp': 3, 'fp': 0}, 'metric': {'point': 1.0,
        'denominator': 3, 'interval': [0.5101091635454028, 0.9999999999999999]},
        'method_sha256': 'a' * 64, 'gate': 0.93, 'release_validated': False}


def test_real_mac_linux_interval_ulps_reproduce():
    other = deepcopy(BASE)
    other['metric']['interval'] = [0.5101091635454027, 1.0]
    assert measurements_match(BASE, other)
    assert measurements_match(other, BASE)


@pytest.mark.parametrize('value', [math.nan, math.inf, -math.inf, True, '0.51',
                                   -1e-16, 1.0000000000000002])
def test_invalid_endpoint_never_tolerated(value):
    other = deepcopy(BASE)
    other['metric']['interval'][0] = value
    assert not measurements_match(other, BASE)


@pytest.mark.parametrize('mutation', ['count', 'bool_count', 'denominator', 'point',
                                     'gate', 'hash', 'extra', 'missing', 'null',
                                     'short_interval', 'reversed', 'substantive'])
def test_non_arithmetic_evidence_changes_refused(mutation):
    other = deepcopy(BASE)
    if mutation == 'count': other['counts']['tp'] += 1
    elif mutation == 'bool_count': other['counts']['fp'] = False
    elif mutation == 'denominator': other['metric']['denominator'] = 4
    elif mutation == 'point': other['metric']['point'] = math.nextafter(1.0, 0.0)
    elif mutation == 'gate': other['gate'] = math.nextafter(.93, 0.0)
    elif mutation == 'hash': other['method_sha256'] = 'b' * 64
    elif mutation == 'extra': other['metric']['extra'] = 1
    elif mutation == 'missing': del other['metric']['denominator']
    elif mutation == 'null': other['metric']['interval'] = None
    elif mutation == 'short_interval': other['metric']['interval'] = [.51]
    elif mutation == 'reversed': other['metric']['interval'] = [1.0, .51]
    else: other['metric']['interval'][0] += WILSON_ENDPOINT_ABS_TOLERANCE * 2
    assert not measurements_match(other, BASE)


def test_null_interval_and_non_interval_nan_or_type_remain_strict():
    assert measurements_match({'interval': None}, {'interval': None})
    assert not measurements_match({'point': math.nan}, {'point': math.nan})
    assert not measurements_match({'point': 1}, {'point': 1.0})
