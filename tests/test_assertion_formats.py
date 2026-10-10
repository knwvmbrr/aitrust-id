"""Date-time checking is mandatory, including when optional packages are absent."""
import copy
from jsonschema import FormatChecker
import pytest
from protocol.assertions import validator
from test_extension_consumer import envelope
@pytest.mark.parametrize('value',['2026-02-31T00:00:00Z','not a timestamp','2026-13-01T00:00:00Z','2026-10-10','2026-10-10T10:00:00','2026-10-10T25:00:00Z','2026-10-10T10:00:00+25:00'])
def test_bad_timestamps_are_rejected(value):
    a=envelope();a['subject']['captured_at']=value;assert not validator().is_valid(a)
@pytest.mark.parametrize('value',['2026-10-10T10:00:00Z','2024-02-29T23:59:59.123456+00:00','2026-10-10T12:30:45-04:00'])
def test_real_producer_timestamp_formats_are_valid(value):
    a=envelope();a['subject']['captured_at']=value;assert validator().is_valid(a)
def test_missing_checker_is_an_error_even_for_valid_records():
    checker=FormatChecker();checker.checkers=dict(checker.checkers);checker.checkers.pop('date-time',None)
    with pytest.raises(RuntimeError,match='checker missing'):validator(checker=checker)
def test_invalid_uuid_never_passes():
    a=envelope();a['assertion_id']='not-a-uuid';assert not validator().is_valid(a)
def test_schema_cannot_contact_an_external_reference():
    with pytest.raises(ValueError,match='External schema reference'):validator({'$ref':'https://example.test/schema.json'})
