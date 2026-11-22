"""Bounded JPEG section observations; not pixel or origin verification."""
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import signal
import stat
import struct
import subprocess
import sys
import tempfile
import time

PROFILE = 'jpeg-metadata-observation/1.0.0'
MAX_INPUT = 10 * 1024 * 1024
MAX_PIXELS = 4_000_000
MAX_MARKERS = 4096
MAX_TABLES = 64
MAX_METADATA = 256 * 1024
MAX_METADATA_SECTIONS = 128
MAX_OUTPUT = 8192
WALL_SECONDS = 4
ROOT = Path(__file__).resolve().parents[1]
META_KEYS = ('Exif_labelled', 'XMP_labelled', 'ICC_labelled', 'JFIF_labelled',
             'APP11_opaque', 'comment', 'other_APP')
REASONS = {'unsupported_format', 'unsupported_variant', 'malformed_structure',
           'trailing_data', 'input_limit', 'metadata_limit', 'source_unavailable',
           'worker_unavailable', 'invalid_request'}
FLAGS = {'metadata_values_returned': False, 'pixels_decoded': False,
         'watermark_verified': False, 'C2PA_inspected': False,
         'AI_origin': 'unknown', 'content_truth_established': False}


class ImageError(ValueError):
    def __init__(self, reason):
        self.reason = reason if reason in REASONS else 'worker_unavailable'
        super().__init__(self.reason)


def need(ok, reason='malformed_structure'):
    if not ok:
        raise ImageError(reason)


def marker(raw, offset):
    need(offset < len(raw) and raw[offset] == 255)
    while offset < len(raw) and raw[offset] == 255:
        offset += 1
    need(offset < len(raw) and raw[offset] != 0)
    return raw[offset], offset + 1


def segment(raw, offset):
    need(offset + 2 <= len(raw))
    length = int.from_bytes(raw[offset:offset + 2], 'big')
    need(length >= 2 and offset + length <= len(raw))
    return raw[offset + 2:offset + length], offset + length


def frame_info(data):
    need(len(data) >= 6)
    depth, height, width, count = struct.unpack('>BHHB', data[:6])
    need(len(data) == 6 + 3 * count and count > 0 and width > 0)
    need(height > 0, 'unsupported_variant')  # Valid DNL-deferred height is outside this subset.
    need(width * height <= MAX_PIXELS, 'input_limit')
    need(depth == 8 and count in (1, 3), 'unsupported_variant')
    components = {}
    for at in range(6, len(data), 3):
        key, sampling, table = data[at:at + 3]
        need(key not in components and 1 <= sampling >> 4 <= 4 and 1 <= sampling & 15 <= 4 and table <= 3)
        components[key] = (sampling, table)
    need(sum((s >> 4) * (s & 15) for s, _ in components.values()) <= 10, 'unsupported_variant')
    return {'width': width, 'height': height, 'precision': depth, 'components': count}, components


def tables(data, kind, quantizers, huffman, definitions):
    at = 0
    need(bool(data))
    while at < len(data):
        definitions += 1
        need(definitions <= MAX_TABLES, 'input_limit')
        spec = data[at]; at += 1
        if kind == 0xDB:
            precision, table = spec >> 4, spec & 15
            need(precision == 0 and table <= 3, 'unsupported_variant')
            need(at + 64 <= len(data) and all(data[at:at + 64]))
            at += 64; quantizers.add(table)
        else:
            category, table = spec >> 4, spec & 15
            need(category in (0, 1) and table in (0, 1), 'unsupported_variant')
            need(at + 16 <= len(data))
            lengths = data[at:at + 16]; at += 16; count = sum(lengths)
            need(0 < count <= 256 and at + count <= len(data))
            available = 1
            for count_at_length in lengths:
                available = 2 * available - count_at_length
                need(available > 0)  # Oversubscribed/all-ones code is forbidden.
            values = data[at:at + count]; at += count
            if category == 0:
                need(all(value <= 11 for value in values), 'unsupported_variant')
            else:
                need(all(value in (0, 0xF0) or 1 <= value & 15 <= 10 for value in values), 'unsupported_variant')
            huffman.add((category, table))
    return definitions


def scan(raw, offset, restart_interval, markers):
    data_bytes = 0; restarts = 0; segment_bytes = 0
    while offset < len(raw):
        if raw[offset] != 255:
            data_bytes += 1; segment_bytes += 1; offset += 1; continue
        start = offset
        if offset + 1 < len(raw) and raw[offset + 1] == 0:
            data_bytes += 1; segment_bytes += 1; offset += 2; continue
        code, after = marker(raw, offset)
        if 0xD0 <= code <= 0xD7:
            need(restart_interval > 0 and code == 0xD0 + restarts % 8 and segment_bytes > 0)
            markers += 1; need(markers <= MAX_MARKERS, 'input_limit')
            restarts += 1; segment_bytes = 0; offset = after; continue
        need(segment_bytes > 0)
        return start, markers, restarts, data_bytes
    raise ImageError('malformed_structure')


def inspect_bytes(raw):
    need(type(raw) is bytes, 'invalid_request')
    need(len(raw) <= MAX_INPUT, 'input_limit')
    need(raw.startswith(b'\xff\xd8'), 'unsupported_format')
    offset = 2; marker_count = 1; metadata_bytes = metadata_count = definitions = 0
    metadata = dict.fromkeys(META_KEYS, 0)
    image = components = None; quantizers = set(); huffman = set()
    scanned = False; entropy_bytes = restart_count = restart_interval = 0
    while offset < len(raw):
        code, offset = marker(raw, offset)
        marker_count += 1; need(marker_count <= MAX_MARKERS, 'input_limit')
        if code == 0xD9:
            need(offset == len(raw), 'trailing_data')
            need(image is not None and scanned, 'unsupported_variant')
            return {'profile': PROFILE, 'state': 'OBSERVED', 'asset_sha256': hashlib.sha256(raw).hexdigest(),
                    'asset_bytes': len(raw), 'image': image, 'marker_count': marker_count,
                    'metadata_bytes': metadata_bytes, 'metadata_sections': metadata,
                    'entropy_framing': {'scan_count': 1, 'data_bytes': entropy_bytes, 'restart_markers': restart_count,
                                        'decoded': False, 'MCU_intervals_verified': False}, **FLAGS, 'tags': []}
        need(code not in (0xD8, *range(0xD0, 0xD8)))
        need(code != 1 and code >= 0xC0, 'unsupported_variant')
        data, offset = segment(raw, offset)
        if 0xE0 <= code <= 0xEF or code == 0xFE:
            metadata_bytes += len(data); metadata_count += 1
            need(metadata_bytes <= MAX_METADATA and metadata_count <= MAX_METADATA_SECTIONS, 'metadata_limit')
            category = ('comment' if code == 0xFE else
                        'Exif_labelled' if code == 0xE1 and data.startswith(b'Exif\0\0') else
                        'XMP_labelled' if code == 0xE1 and data.startswith(b'http://ns.adobe.com/xap/1.0/\0') else
                        'ICC_labelled' if code == 0xE2 and data.startswith(b'ICC_PROFILE\0') else
                        'JFIF_labelled' if code == 0xE0 and data.startswith(b'JFIF\0') else
                        'APP11_opaque' if code == 0xEB else 'other_APP')
            metadata[category] += 1
        elif code == 0xC0:
            need(image is None and not scanned)
            image, components = frame_info(data)
        elif code in (0xDB, 0xC4):
            need(not scanned, 'unsupported_variant')
            definitions = tables(data, code, quantizers, huffman, definitions)
        elif code == 0xDD:
            need(not scanned, 'unsupported_variant'); need(len(data) == 2)
            restart_interval = int.from_bytes(data, 'big')
        elif code == 0xDA:
            need(not scanned, 'unsupported_variant'); need(image is not None and len(data) >= 4)
            count = data[0]; need(len(data) == 1 + 2 * count + 3)
            need(count == len(components) and data[-3:] == b'\0\x3f\0', 'unsupported_variant')
            selected = set()
            for at in range(1, 1 + 2 * count, 2):
                key, table = data[at:at + 2]
                need(key in components and key not in selected); selected.add(key)
                need(components[key][1] in quantizers and (0, table >> 4) in huffman and (1, table & 15) in huffman, 'unsupported_variant')
            offset, marker_count, restart_count, entropy_bytes = scan(raw, offset, restart_interval, marker_count)
            scanned = True
        else:
            raise ImageError('unsupported_variant')
    raise ImageError('malformed_structure')


def unavailable(reason, raw=None):
    value = {'profile': PROFILE, 'state': 'UNAVAILABLE', 'reason': reason if reason in REASONS else 'worker_unavailable', **FLAGS, 'tags': []}
    if type(raw) is bytes and len(raw) <= MAX_INPUT:
        value.update(asset_sha256=hashlib.sha256(raw).hexdigest(), asset_bytes=len(raw))
    return value


def validate_shape(value):
    need(type(value) is dict and value.get('profile') == PROFILE, 'worker_unavailable')
    base = {'profile', 'state', 'asset_sha256', 'asset_bytes', 'tags', *FLAGS}
    need(type(value.get('asset_sha256')) is str and re.fullmatch('[a-f0-9]{64}', value['asset_sha256']) is not None and type(value.get('asset_bytes')) is int and 0 <= value['asset_bytes'] <= MAX_INPUT, 'worker_unavailable')
    need(all(type(value.get(k)) is type(v) and value[k] == v for k, v in FLAGS.items()) and type(value.get('tags')) is list and value['tags'] == [], 'worker_unavailable')
    if value.get('state') == 'UNAVAILABLE':
        need(set(value) == base | {'reason'} and value['reason'] in REASONS, 'worker_unavailable'); return value
    need(value.get('state') == 'OBSERVED' and set(value) == base | {'image', 'marker_count', 'metadata_bytes', 'metadata_sections', 'entropy_framing'}, 'worker_unavailable')
    image = value['image']
    need(type(image) is dict and set(image) == {'width', 'height', 'precision', 'components'} and image.get('precision') == 8 and type(image['precision']) is int and type(image.get('components')) is int and image['components'] in (1, 3), 'worker_unavailable')
    need(all(type(image.get(k)) is int and 0 < image[k] <= MAX_PIXELS for k in ('width', 'height')) and image['width'] * image['height'] <= MAX_PIXELS, 'worker_unavailable')
    need(type(value['marker_count']) is int and 1 <= value['marker_count'] <= MAX_MARKERS and type(value['metadata_bytes']) is int and 0 <= value['metadata_bytes'] <= MAX_METADATA, 'worker_unavailable')
    meta = value['metadata_sections']
    need(type(meta) is dict and set(meta) == set(META_KEYS) and all(type(n) is int and 0 <= n <= MAX_METADATA_SECTIONS for n in meta.values()) and sum(meta.values()) <= MAX_METADATA_SECTIONS, 'worker_unavailable')
    entropy = value['entropy_framing']
    need(type(entropy) is dict and set(entropy) == {'scan_count', 'data_bytes', 'restart_markers', 'decoded', 'MCU_intervals_verified'} and type(entropy['scan_count']) is int and entropy['scan_count'] == 1 and entropy['decoded'] is False and entropy['MCU_intervals_verified'] is False and type(entropy['data_bytes']) is int and 0 < entropy['data_bytes'] <= MAX_INPUT and type(entropy['restart_markers']) is int and 0 <= entropy['restart_markers'] <= MAX_MARKERS, 'worker_unavailable')
    return value


def validate_record(value, raw):
    validate_shape(value)
    need(value['asset_sha256'] == hashlib.sha256(raw).hexdigest() and value['asset_bytes'] == len(raw), 'worker_unavailable')
    if value['state'] == 'OBSERVED':
        # Replay the small framing observation, not pixel/entropy decoding.
        need(value == inspect_bytes(raw), 'worker_unavailable')
    return value


def identity(info):
    return info.st_dev, info.st_ino, info.st_mode, info.st_size, info.st_mtime_ns, info.st_ctime_ns


def inspect_file(path):
    """Retain no-follow ancestors and one captured regular-file descriptor."""
    fds = []; directories = []; failure = False
    try:
        selected = Path(path).expanduser().absolute()
        need('..' not in selected.parts and 1 < len(selected.parts) <= 128 and len(str(selected)) <= 4096, 'source_unavailable')
        parent = os.open(selected.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_NONBLOCK); fds.append(parent)
        for name in selected.parts[1:-1]:
            child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent); fds.append(child)
            info = os.fstat(child); need(stat.S_ISDIR(info.st_mode), 'source_unavailable')
            directories.append((parent, name, child, (info.st_dev, info.st_ino, info.st_mode))); parent = child
        fd = os.open(selected.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent); fds.append(fd)
        before = os.fstat(fd); need(stat.S_ISREG(before.st_mode), 'source_unavailable'); need(before.st_size <= MAX_INPUT, 'input_limit')
        raw = bytearray()
        while True:
            value = os.read(fd, min(65536, MAX_INPUT - len(raw) + 1))
            if not value:
                break
            need(len(value) <= MAX_INPUT - len(raw), 'input_limit'); raw.extend(value)
        raw = bytes(raw); need(len(raw) == before.st_size and identity(before) == identity(os.fstat(fd)), 'source_unavailable')
        os.lseek(fd, 0, os.SEEK_SET); value = worker_record(fd)
        need(identity(before) == identity(os.fstat(fd)) == identity(os.stat(selected.name, dir_fd=parent, follow_symlinks=False)), 'source_unavailable')
        for ancestor, name, opened, expected in directories:
            a, b = os.fstat(opened), os.stat(name, dir_fd=ancestor, follow_symlinks=False)
            need((a.st_dev, a.st_ino, a.st_mode) == expected == (b.st_dev, b.st_ino, b.st_mode), 'source_unavailable')
        return validate_record(value, raw)
    except (OSError, ValueError, TypeError) as error:
        if isinstance(error, ImageError):
            raise
        raise ImageError('source_unavailable') from None
    finally:
        # Each raw handle is relinquished before one close attempt, all attempted.
        owned = fds; fds = []
        for fd in reversed(owned):
            try:
                os.close(fd)
            except OSError:
                failure = True
        if failure:
            raise ImageError('source_unavailable')


def worker_record(fd):
    selector = selectors.DefaultSelector(); child = None; output = bytearray()
    deadline = time.monotonic() + WALL_SECONDS
    try:
        with tempfile.TemporaryDirectory(prefix='aitrust-jpeg-') as cwd:
            os.chmod(cwd, 0o700)
            child = subprocess.Popen([sys.executable, '-I', '-S', '-B', str(ROOT / 'scripts/inspect-jpeg-metadata.py'), '--worker'], stdin=fd,
                                     stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, cwd=cwd,
                                     env={'PATH': os.defpath, 'LANG': 'C.UTF-8'}, start_new_session=True, close_fds=True)
            os.set_blocking(child.stdout.fileno(), False); selector.register(child.stdout, selectors.EVENT_READ)
            eof = False
            while not eof:
                remaining = deadline - time.monotonic(); need(remaining > 0, 'worker_unavailable')
                for key, _ in selector.select(min(.1, remaining)):
                    try:
                        value = os.read(key.fd, min(65536, MAX_OUTPUT - len(output) + 1))
                    except BlockingIOError:
                        continue
                    if not value:
                        eof = True; break
                    need(len(value) <= MAX_OUTPUT - len(output), 'worker_unavailable'); output.extend(value)
            remaining = deadline - time.monotonic(); need(remaining > 0, 'worker_unavailable')
            code = child.wait(timeout=remaining); need(code == 0 and time.monotonic() <= deadline, 'worker_unavailable')
        def unique(pairs):
            value = {}
            for key, item in pairs:
                need(key not in value, 'worker_unavailable'); value[key] = item
            return value
        try:
            return json.loads(output, object_pairs_hook=unique,
                              parse_constant=lambda _: (_ for _ in ()).throw(ImageError('worker_unavailable')))
        except (ValueError, UnicodeError, RecursionError):
            raise ImageError('worker_unavailable') from None
    except (OSError, subprocess.SubprocessError):
        raise ImageError('worker_unavailable') from None
    finally:
        if child is not None:
            if child.returncode is None:
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                child.wait(timeout=5)
            child.stdout.close()
        selector.close()


def text_result(value):
    if value.get('state') == 'OBSERVED' or 'asset_sha256' in value:
        validate_shape(value)
    else:
        need(type(value) is dict and value == unavailable(value.get('reason')), 'worker_unavailable')
    lines = ['AI TRUST ID · JPEG details']
    if value['state'] != 'OBSERVED':
        messages = {'unsupported_format': 'Choose a supported local JPEG file.',
                    'unsupported_variant': 'This JPEG variant is outside this reader’s supported profile.',
                    'malformed_structure': 'The JPEG framing could not be read.',
                    'trailing_data': 'Extra data follows the first JPEG image; this profile cannot interpret it.',
                    'input_limit': 'This file exceeds the supported size or structure limits.',
                    'metadata_limit': 'The stored metadata exceeds the supported limits.',
                    'source_unavailable': 'The selected regular file could not be read.',
                    'worker_unavailable': 'The JPEG check did not complete.',
                    'invalid_request': 'Choose a supported local JPEG file.'}
        lines.append(messages[value['reason']])
    else:
        image = value['image']
        lines.append(f"JPEG · {image['width']} × {image['height']} header pixels · {image['components']} component(s)")
        lines.append('Metadata sections counted: ' + str(sum(value['metadata_sections'].values())))
        labels = {'Exif_labelled': 'Exif-labelled', 'XMP_labelled': 'XMP-labelled', 'ICC_labelled': 'Color-profile-labelled',
                  'JFIF_labelled': 'JFIF-labelled', 'APP11_opaque': 'Opaque APP11', 'comment': 'Comment', 'other_APP': 'Other application'}
        for key, label in labels.items():
            if value['metadata_sections'][key]:
                lines.append(label + ': ' + str(value['metadata_sections'][key]) + ' (contents unverified).')
        lines.append('Names, GPS, comments and URLs are not shown. The original file may still contain identifying information.')
    lines += ['Pixels and entropy codes are not decoded; valid framing is not proof of a valid or authentic image.',
              'AI origin: Unknown. No watermark or Content Credential verified. No tag issued.']
    return '\n'.join(lines)
