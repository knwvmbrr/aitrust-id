"""Synthetic JPEG engineering fixtures. No vendor/user image or persistent key.

The minimal baseline image is a single grayscale DCT block, DC=0 and EOB,
with all 1 quantizers. The two one-bit Huffman codes are each zero; remaining
scan bits are 1 padding. This is not an origin/accuracy corpus.
"""
import datetime
import io
import json
from pathlib import Path
import struct

CANARY = 'JPEG_PRIVATE_METADATA_CANARY'
CREATION = 'http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia'
EDIT = 'http://cv.iptc.org/newscodes/digitalsourcetype/compositeWithTrainedAlgorithmicMedia'


def segment(code, data):
    return bytes([255, code])+struct.pack('>H', len(data)+2)+data


def blank():
    counts = b'\1'+b'\0'*15
    return (b'\xff\xd8'+segment(0xDB, b'\0'+b'\1'*64)
        +segment(0xC0, struct.pack('>BHHB', 8, 1, 1, 1)+b'\1\x11\0')
        +segment(0xC4, b'\0'+counts+b'\0'+b'\x10'+counts+b'\0')
        +segment(0xDA, b'\1\1\0\0\x3f\0')+b'\x3f\xff\xd9')


def generate(directory, checkpoint=lambda stage: None):
    checkpoint('fixture_imports')
    import c2pa
    from cryptography import x509
    from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    destination = Path(directory)
    destination.mkdir(mode=0o700, exist_ok=False)
    checkpoint('fixture_certificates')
    now = datetime.datetime.now(datetime.timezone.utc)
    def names(text):
        return x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, text)])
    ca, key = ec.generate_private_key(ec.SECP256R1()), ec.generate_private_key(ec.SECP256R1())
    root_name = names('SYNTHETIC JPEG TEST ROOT ONLY')
    root = (x509.CertificateBuilder().subject_name(root_name).issuer_name(root_name)
        .public_key(ca.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(now-datetime.timedelta(days=1)).not_valid_after(now+datetime.timedelta(days=10))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), True)
        .add_extension(x509.KeyUsage(False, False, False, False, False, True, True, False, False), True)
        .sign(ca, hashes.SHA256()))
    cert = (x509.CertificateBuilder().subject_name(names(CANARY)).issuer_name(root.subject)
        .public_key(key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(now-datetime.timedelta(days=1)).not_valid_after(now+datetime.timedelta(days=10))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), True)
        .add_extension(x509.KeyUsage(True, False, False, False, False, False, False, False, False), True)
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.EMAIL_PROTECTION]), False)
        .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca.public_key()), False)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), False)
        .sign(ca, hashes.SHA256()))
    root_pem = root.public_bytes(serialization.Encoding.PEM)
    public_chain = cert.public_bytes(serialization.Encoding.PEM)+root_pem
    private = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    settings = {'verify': {'remote_manifest_fetch': False, 'ocsp_fetch': False},
                'core': {'allowed_network_hosts': [], 'decode_identity_assertions': False},
                'builder': {'thumbnail': {'enabled': False}}}
    values = {'unsigned.jpg': blank()}
    checkpoint('fixture_context')
    with c2pa.Context.from_dict(settings) as context:
        for name, action, source in [('creation', 'c2pa.created', CREATION), ('edit', 'c2pa.edited', EDIT),
                                     ('ordinary', 'c2pa.created', 'http://cv.iptc.org/newscodes/digitalsourcetype/digitalCapture')]:
            definition = {'claim_generator': 'AI TRUST ID synthetic JPEG test', 'title': CANARY, 'format': 'image/jpeg',
                'assertions': [{'label': 'c2pa.actions', 'data': {'actions': [{'action': action, 'digitalSourceType': source}]}},
                               {'label': 'org.aitrust.synthetic', 'data': {'private_note': CANARY}}]}
            checkpoint('fixture_signer_'+name)
            out = io.BytesIO()
            with c2pa.Signer.from_info(c2pa.C2paSignerInfo('es256', public_chain, private, None)) as signer:
                checkpoint('fixture_builder_'+name)
                with c2pa.Builder(definition, context=context) as builder:
                    checkpoint('fixture_sign_'+name)
                    builder.sign(signer, 'image/jpeg', io.BytesIO(blank()), out)
            values[name+'.jpg'] = out.getvalue()
    checkpoint('fixture_altered_and_private_files')
    signed = values['creation.jpg']
    marker = segment(0xDB, b'\0'+b'\1'*64)
    assert signed.count(marker) == 1
    values['altered.jpg'] = signed.replace(marker, segment(0xDB, b'\0'+b'\2'+b'\1'*63))
    values['unsupported.jpg'] = blank().replace(b'\xff\xc0', b'\xff\xc2', 1)
    values['malformed.jpg'] = blank()[:-1]
    for name, value in {**values, 'root.pem': root_pem}.items():
        with (destination/name).open('xb') as stream:
            stream.write(value)
        (destination/name).chmod(0o600)
    return {'fixture_only': True, 'private_keys_written': False, 'files': len(values)+1}


if __name__ == '__main__':
    import sys
    print(json.dumps(generate(sys.argv[1])))
