"""Record the actual selected redactor configuration without input or filesystem paths."""
import hashlib
import importlib.metadata
from pathlib import Path
import platform
from protocol.replay_identity import digest, redactor_identity


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
    recognizers=sorted((r.to_dict() for r in analyzer.registry.recognizers),
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
