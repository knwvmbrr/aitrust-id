"""Operator-key authentication for exact loopback response bytes, not accuracy."""
import base64
import hashlib
import os
from pathlib import Path
import re
import stat

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, utils

PROFILE = 'loopback-response/p256-sha256/v1'
ORDER = int('ffffffff00000000ffffffffffffffffbce6faada7179e84f3b9cac2fc632551', 16)


def payload(nonce, request_bytes, response_bytes):
    if not isinstance(nonce, str) or not re.fullmatch('[a-f0-9]{64}', nonce):
        raise ValueError('Invalid request nonce')
    prefix = PROFILE + '\n' + nonce + '\n' + hashlib.sha256(request_bytes).hexdigest() + '\n'
    return prefix.encode('ascii') + response_bytes


def load_private_key(filename):
    """No implicit key creation; reject links, permissive modes and swapped files."""
    path = Path(filename).absolute()
    for parent in (path, *path.parents):
        if parent.is_symlink():
            raise ValueError('Signing key links are refused')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid()
                or stat.S_IMODE(info.st_mode) not in (0o400, 0o600)
                or not 1 <= info.st_size <= 16_384):
            raise ValueError('Signing key must be an owner-private regular file')
        raw = os.read(fd, 16_385)
        after = os.fstat(fd)
        if len(raw) != info.st_size or (after.st_size, after.st_mtime_ns) != (info.st_size, info.st_mtime_ns):
            raise ValueError('Signing key changed while reading')
    finally:
        os.close(fd)
    key = serialization.load_pem_private_key(raw, password=None)
    if not isinstance(key, ec.EllipticCurvePrivateKey) or not isinstance(key.curve, ec.SECP256R1):
        raise ValueError('Signing key must use P-256')
    return key


def public_profile(key):
    raw = key.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    return {'profile': PROFILE, 'public_key': base64.urlsafe_b64encode(raw).decode().rstrip('='),
            'key_id': hashlib.sha256(raw).hexdigest()}


def sign_headers(key, nonce, request_bytes, response_bytes):
    signed = key.sign(payload(nonce, request_bytes, response_bytes), ec.ECDSA(hashes.SHA256()))
    r, s = utils.decode_dss_signature(signed)
    raw = r.to_bytes(32, 'big') + min(s, ORDER-s).to_bytes(32, 'big')
    return {'X-AITrust-Profile': PROFILE, 'X-AITrust-Key': public_profile(key)['key_id'],
            'X-AITrust-Signature': base64.urlsafe_b64encode(raw).decode().rstrip('=')}
