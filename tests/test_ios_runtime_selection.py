"""A newer device-specific image must not be selected for the wrong phone."""
from pathlib import Path
import runpy
import pytest

ROOT = Path(__file__).resolve().parents[1]
module = runpy.run_path(str(ROOT / 'scripts/select-ios-runtime.py'))


def row(version, *, phone=module['PHONE'], available=True, suffix=''):
    return {'identifier': 'com.apple.CoreSimulator.SimRuntime.iOS-' + version.replace('.', '-') + suffix,
            'version': version, 'isAvailable': available, 'supportedDeviceTypes': [{'identifier': phone}]}


def test_device_specific_newest_runtime_is_excluded():
    good = row('26.2')
    new = row('27.2', phone='com.apple.CoreSimulator.SimDeviceType.iPhone-19-4', suffix='-iPhone19-4')
    assert module['select']({'runtimes': [good, new]}) == good['identifier']


def test_versions_sort_numerically():
    good = row('26.10')
    assert module['select']({'runtimes': [row('26.9'), good]}) == good['identifier']


@pytest.mark.parametrize('field,value', [('isAvailable', False), ('isAvailable', 'true'),
    ('supportedDeviceTypes', []), ('supportedDeviceTypes', None), ('version', 'unknown'),
    ('identifier', 'https://example.invalid/runtime'), ('identifier', 'bad; command')])
def test_missing_or_unsupported_inventory_is_refused(field, value):
    candidate = row('26.2'); candidate[field] = value
    with pytest.raises(ValueError): module['select']({'runtimes': [candidate]})


@pytest.mark.parametrize('value', [None, {}, {'runtimes': []}, {'runtimes': [row('17.5')]}])
def test_no_compatible_runtime_is_unavailable(value):
    with pytest.raises(ValueError): module['select'](value)
