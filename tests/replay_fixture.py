"""Synthetic redactor identity for HTTP contract tests, not observed model evidence."""
import hashlib
from pathlib import Path
from protocol.replay_identity import redactor_identity
ROOT=Path(__file__).resolve().parents[1]
def synthetic_identity():
    paths={'app':'services/anonymizer/app.py','model_loader':'services/anonymizer/model_identity.py','requirements_lock':'services/anonymizer/requirements.lock','identity_contract':'protocol/replay_identity.py','identity_builder':'services/anonymizer/replay_metadata.py'}
    return redactor_identity({'python':'3.12.14','platform_machine':'x86_64','model_manifest_sha256':'a'*64,'sources':{k:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for k,p in paths.items()},'dependencies':{'synthetic-test-only':'1.0'},'dependency_records':{'synthetic-test-only':'b'*64},'recognizer_configuration_sha256':'c'*64,'recognizer_count':1})
