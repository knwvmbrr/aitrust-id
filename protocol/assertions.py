"""Offline assertion-schema validation; required formats must never be skipped."""
import json
from pathlib import Path
from jsonschema import Draft202012Validator,FormatChecker
ROOT=Path(__file__).resolve().parents[1]
def validator(schema=None, checker=None):
    if schema is None:schema=json.loads((ROOT/'spec/assertion.schema.json').read_text())
    required=set()
    def visit(value):
        if isinstance(value,dict):
            if 'format' in value:required.add(value['format'])
            for key in ('$ref','$dynamicRef','$recursiveRef'):
                if key in value and not value[key].startswith('#/'):raise ValueError('External schema reference refused')
            for item in value.values():visit(item)
        elif isinstance(value,list):
            for item in value:visit(item)
    Draft202012Validator.check_schema(schema);visit(schema)
    if checker is None:checker=FormatChecker()
    if any(name not in checker.checkers for name in required):
        raise RuntimeError('Required assertion format checker missing; install hashed evaluation dependencies')
    return Draft202012Validator(schema,format_checker=checker)
