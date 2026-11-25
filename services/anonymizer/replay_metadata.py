"""Record the actual selected redactor configuration without input or filesystem paths."""
import hashlib
import importlib.metadata
from pathlib import Path
import platform
import re
from protocol.replay_identity import digest, redactor_identity


_SPACY_CLASS = ('presidio_analyzer.predefined_recognizers.spacy_recognizer',
                'SpacyRecognizer')
_ENTITY = re.compile(r'[A-Z][A-Z0-9_]{0,79}')


def _recognizer_record(recognizer):
    """Copy one known capability set without changing operational ordering.

    The pinned Spacy NLP engine constructs this field from a set. Its analyzer
    uses membership; patterns/context and every other list keep their order.
    """
    raw = recognizer.to_dict()
    if type(raw) is not dict:
        raise ValueError('Invalid recognizer identity record')
    record = dict(raw)
    cls = type(recognizer)
    if (cls.__module__, cls.__name__) == _SPACY_CLASS:
        values = raw.get('supported_entities')
        if (type(values) is not list or not 1 <= len(values) <= 128
                or any(type(value) is not str or _ENTITY.fullmatch(value) is None
                       for value in values)
                or len(set(values)) != len(values)):
            raise ValueError('Invalid Spacy capability identity')
        record['supported_entities'] = sorted(values)
    return record


def identity(analyzer, model_identity):
    root=Path(__file__).resolve().parent
    names={'app':root/'app.py','model_loader':root/'model_identity.py',
           'requirements_lock':root/'requirements.lock',
           'identity_contract':root/'protocol/replay_identity.py',
           'identity_builder':root/'replay_metadata.py'}
    distributions={}
    records={}
    for d in importlib.metadata.distributions():
        name=d.metadata['Name'].lower().replace('_','-')
        record=d.read_text('RECORD')
        if not record or name in distributions:
            raise ValueError('Missing or duplicate installed distribution identity')
        distributions[name]=d.version
        records[name]=hashlib.sha256(record.encode()).hexdigest()
    recognizers=sorted((_recognizer_record(r) for r in analyzer.registry.recognizers),
                       key=lambda r:(r.get('name',''),r.get('supported_language','')))
    if model_identity['verified_before_load'] is not True:
        raise ValueError('Redactor assets were not verified')
    configuration={
        'python':platform.python_version(),
        'platform_machine':platform.machine(),
        'dependency_records':records,
        'model_manifest_sha256':model_identity['manifest_sha256'],
        'sources':{key:hashlib.sha256(file.read_bytes()).hexdigest() for key,file in names.items()},
        'dependencies':distributions,
        'recognizer_configuration_sha256':digest(recognizers),
        'recognizer_count':len(recognizers),
    }
    return redactor_identity(configuration)
