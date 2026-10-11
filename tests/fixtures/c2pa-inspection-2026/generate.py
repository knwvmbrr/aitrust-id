"""Generate synthetic parser fixtures, never production credentials.

The ephemeral private keys exist only in this process and are not written.
Run explicitly with the optional SDK environment; regular CI reads frozen PNGs.
"""
import datetime
import io
import json
from pathlib import Path
import struct
import zlib


def generate(destination):
    import c2pa
    from cryptography import x509
    from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec

    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))
    header = chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0))
    pixel = chunk(b'IDAT', zlib.compress(b'\x00\xff\xff\xff'))
    blank = b'\x89PNG\r\n\x1a\n' + header + pixel + chunk(b'IEND', b'')
    now = datetime.datetime.now(datetime.timezone.utc)
    ca, key = ec.generate_private_key(ec.SECP256R1()), ec.generate_private_key(ec.SECP256R1())
    def name(value):
        return x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, value)])
    root_name = name('Synthetic TEST root, not an authority')
    root = (x509.CertificateBuilder().subject_name(root_name).issuer_name(root_name)
        .public_key(ca.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(now-datetime.timedelta(days=1)).not_valid_after(now+datetime.timedelta(days=3650))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), True)
        .add_extension(x509.KeyUsage(False, False, False, False, False, True, True, False, False), True)
        .sign(ca, hashes.SHA256()))
    cert = (x509.CertificateBuilder().subject_name(name('Synthetic TEST signer, no identity claim'))
        .issuer_name(root.subject).public_key(key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(now-datetime.timedelta(days=1)).not_valid_after(now+datetime.timedelta(days=3650))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), True)
        .add_extension(x509.KeyUsage(True, False, False, False, False, False, False, False, False), True)
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.EMAIL_PROTECTION]), False)
        .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca.public_key()), False)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), False)
        .sign(ca, hashes.SHA256()))
    pem = cert.public_bytes(serialization.Encoding.PEM) + root.public_bytes(serialization.Encoding.PEM)
    private = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    context = c2pa.Context.from_dict({'verify': {'remote_manifest_fetch': False, 'ocsp_fetch': False},
        'core': {'allowed_network_hosts': [], 'decode_identity_assertions': False}})
    definition = {'claim_generator': 'Synthetic C2PA parser fixture', 'title': 'SYNTHETIC_ONLY',
        'format': 'image/png', 'assertions': [
            {'label': 'c2pa.actions', 'data': {'actions': [{'action': 'c2pa.created',
                'digitalSourceType': 'http://cv.iptc.org/newscodes/digitalsourcetype/softwareImage'}]}},
            {'label': 'org.aitrust.test', 'data': {'note': 'SYNTHETIC_ONLY_NOT_AUTHORSHIP',
                'private_canary': 'FIXTURE_PRIVATE_METADATA_CANARY'}}]}
    output = io.BytesIO()
    with c2pa.Signer.from_info(c2pa.C2paSignerInfo('es256', pem, private, None)) as signer:
        with c2pa.Builder(definition, context=context) as builder:
            builder.sign(signer, 'image/png', io.BytesIO(blank), output)
    signed = output.getvalue()
    # Change the valid IDAT pixel chunk after signing, without breaking PNG CRC.
    new_pixel = chunk(b'IDAT', zlib.compress(b'\x00\x00\x00\x00'))
    assert signed.count(pixel) == 1
    altered = signed.replace(pixel, new_pixel)
    for filename, value in [('unsigned.png', blank), ('signed.png', signed), ('altered.png', altered)]:
        path = destination / filename
        with path.open('xb') as stream:
            stream.write(value)
    return {'files': 3, 'private_keys_written': False, 'fixture_only': True}


if __name__ == '__main__':
    import sys
    print(json.dumps(generate(sys.argv[1])))
