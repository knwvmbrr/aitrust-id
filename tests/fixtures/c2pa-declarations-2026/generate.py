"""Author synthetic declarations; pixels are hand-built, never AI ground truth.

Ephemeral untrusted TEST keys remain in memory. Run explicitly in the existing
pinned optional environment to a new private directory; CI reads frozen assets.
"""
import datetime
import hashlib
import io
import json
from pathlib import Path
import struct
import sys
import zlib

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from tools import manifest_inspection as parser


def generate(destination):
    c2pa, pins = parser.load_verified_sdk()
    from cryptography import x509
    from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    require = lambda value: None if value else (_ for _ in ()).throw(ValueError('Fixture prerequisite refused'))
    require(c2pa.__version__ == pins['package_version'] and c2pa.sdk_version() == pins['sdk_version'])
    destination = Path(destination).resolve(); require(not destination.exists())
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))
    header = chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0))
    pixel = chunk(b'IDAT', zlib.compress(b'\x00\xff\xff\xff'))
    blank = b'\x89PNG\r\n\x1a\n' + header + pixel + chunk(b'IEND', b'')
    now = datetime.datetime.now(datetime.timezone.utc)
    ca, key = ec.generate_private_key(ec.SECP256R1()), ec.generate_private_key(ec.SECP256R1())
    def name(value): return x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, value)])
    root_name = name('Synthetic TEST declaration root - not a real authority')
    root = (x509.CertificateBuilder().subject_name(root_name).issuer_name(root_name)
        .public_key(ca.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(now-datetime.timedelta(days=1)).not_valid_after(now+datetime.timedelta(days=3650))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), True)
        .add_extension(x509.KeyUsage(False, False, False, False, False, True, True, False, False), True)
        .sign(ca, hashes.SHA256()))
    cert = (x509.CertificateBuilder().subject_name(name('Synthetic TEST declaration signer - identity unverified'))
        .issuer_name(root.subject).public_key(key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(now-datetime.timedelta(days=1)).not_valid_after(now+datetime.timedelta(days=3650))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), True)
        .add_extension(x509.KeyUsage(True, False, False, False, False, False, False, False, False), True)
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.EMAIL_PROTECTION]), False)
        .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca.public_key()), False)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), False)
        .sign(ca, hashes.SHA256()))
    chain = cert.public_bytes(serialization.Encoding.PEM) + root.public_bytes(serialization.Encoding.PEM)
    private = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    base = 'http://cv.iptc.org/newscodes/digitalsourcetype/'
    created = lambda source: {'action': 'c2pa.created', 'digitalSourceType': base + source}
    edited = {'action': 'c2pa.edited', 'digitalSourceType': base + 'compositeWithTrainedAlgorithmicMedia'}
    inputs = {
        'declared-creation.png': {'actions': [created('trainedAlgorithmicMedia')], 'allActionsIncluded': False},
        'declared-edit.png': {'actions': [created('softwareImage'), edited], 'allActionsIncluded': False},
        'compatible-declarations.png': {'actions': [created('trainedAlgorithmicMedia'), edited], 'allActionsIncluded': False},
        'non-generative.png': {'actions': [created('softwareImage')], 'allActionsIncluded': False},
        'custom-declaration.png': {'actions': [{'action': 'c2pa.created', 'digitalSourceType': 'org.example.PRIVATE_CANARY'}], 'allActionsIncluded': False},
        'template-only.png': {'actions': [created('softwareImage')], 'templates': [{'action': '*', 'digitalSourceType': base + 'trainedAlgorithmicMedia'}], 'allActionsIncluded': False},
    }
    outputs = {}
    with c2pa.Context.from_dict(parser.SETTINGS) as context:
        with c2pa.Signer.from_info(c2pa.C2paSignerInfo('es256', chain, private, None)) as signer:
            for filename, actions in inputs.items():
                definition = {'claim_generator': 'AI Trust ID synthetic declaration fixture', 'title': 'DECLARATION_PRIVATE_METADATA_CANARY',
                    'format': 'image/png', 'assertions': [
                        {'label': 'c2pa.actions.v2', 'created': True, 'data': actions},
                        {'label': 'org.aitrust.fixture', 'data': {'private_note': 'DECLARATION_PRIVATE_METADATA_CANARY'}}]}
                output = io.BytesIO()
                with c2pa.Builder(definition, context=context) as builder:
                    builder.sign(signer, 'image/png', io.BytesIO(blank), output)
                outputs[filename] = output.getvalue()
    replacement = chunk(b'IDAT', zlib.compress(b'\x00\x00\x00\x00'))
    require(outputs['declared-creation.png'].count(pixel) == 1)
    outputs['declared-creation-altered.png'] = outputs['declared-creation.png'].replace(pixel, replacement)
    manifest = {'schema_version': 1, 'license': 'Apache-2.0', 'fixture_only': True,
        'pixels': 'hand-built one-pixel PNG; no AI generation was performed',
        'claims': 'intentionally authored producer declarations; not origin ground truth or training labels',
        'private_keys_written': False, 'test_root_trusted': False, 'independent_accuracy_evidence': False,
        'package_version': pins['package_version'], 'sdk_version': pins['sdk_version'],
        'generated_at': now.isoformat(), 'generator_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'files': {name: hashlib.sha256(raw).hexdigest() for name, raw in sorted(outputs.items())}}
    destination.mkdir(mode=0o700, parents=False)
    for filename, raw in outputs.items():
        with (destination/filename).open('xb') as stream: stream.write(raw)
    with (destination/'manifest.json').open('x') as stream: json.dump(manifest, stream, indent=2); stream.write('\n')
    return {'files': len(outputs), 'fixture_only': True, 'private_keys_written': False}


if __name__ == '__main__':
    print(json.dumps(generate(sys.argv[1])))
