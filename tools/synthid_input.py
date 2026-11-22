"""Optional, token-only SynthID research input. No tag or origin assertion."""
import hashlib
import json
import math
import os
from pathlib import Path
import selectors
import signal
import stat
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
SDK = ROOT / 'integrations/synthid-reference'
UPSTREAM = '6452fbb837d0ad4281ccddb94b0af75d219b1a14'
PROFILE = 'synthid-text-0.3-single-key-reference/v1'
MAX_INPUT = 16384
MAX_OUTPUT = 8192
DEADLINE = 12
SOURCE = {
    'detector_frequentist.py': 'a8a8092b2f741307579be4c82aeaa96a8c6712a0b8f254eddb0be8a344600ec7',
    'logits_processing.py': 'fcf4d2c3902dbf52e646c189bc508fa1ed5b7cf4e55c595cf5fbd9972036226b',
    'hashing_function.py': '8be617a6e1a302eda10135aa09312db8d3fb80ab1b3bf71c70538f1ded204b04',
}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('ascii')


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Invalid vendor packet')
        result[key] = value
    return result


def parse(raw):
    if type(raw) is not bytes or len(raw) > MAX_INPUT:
        raise ValueError('Invalid vendor packet')
    return json.loads(raw, object_pairs_hook=unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Invalid number')))


def validate_packet(packet):
    if type(packet) is not dict or set(packet) != {'profile', 'public_key', 'vocabulary_size', 'eos_token_id', 'token_ids', 'prompt_removed'}:
        raise ValueError('Invalid vendor packet')
    if packet['profile'] != PROFILE or packet['prompt_removed'] is not True:
        raise ValueError('Unsupported declared profile')
    key, vocab, eos, ids = (packet[k] for k in ('public_key', 'vocabulary_size', 'eos_token_id', 'token_ids'))
    if (type(key) is not int or not 0 <= key < 2**63 or type(vocab) is not int
            or not 2 <= vocab <= 65536 or type(eos) is not int or not 0 <= eos < vocab
            or type(ids) is not list or not 1 <= len(ids) <= 512
            or any(type(i) is not int or not 0 <= i < vocab for i in ids)):
        raise ValueError('Invalid vendor packet')
    # Roundtrip disallows custom mappings/lists and stabilizes the worker subject.
    return parse(canonical(packet))


def read_packet(path):
    path = Path(path).absolute()
    # Reject symlink parents as well as the leaf. Never read a FIFO/device.
    for part in [*reversed(path.parents), path]:
        if part.is_symlink():
            raise ValueError('Invalid vendor file')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_INPUT:
            raise ValueError('Invalid vendor file')
        raw = os.read(fd, MAX_INPUT + 1)
        after = os.fstat(fd)
        current = os.stat(path, follow_symlinks=False)
        identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
        if len(raw) != before.st_size or len(raw) > MAX_INPUT or identity(before) != identity(after) or identity(before) != identity(current):
            raise ValueError('Vendor file changed')
        return validate_packet(parse(raw))
    finally:
        os.close(fd)


def read_source(path, cap=65536):
    path = Path(path)
    for part in [*reversed(path.absolute().parents), path]:
        if part.is_symlink():
            raise ValueError('Vendor source unavailable')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size > cap:
            raise ValueError('Vendor source unavailable')
        raw = os.read(fd, cap + 1)
        after = os.fstat(fd)
        current = os.stat(path, follow_symlinks=False)
        ident = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
        if len(raw) != before.st_size or len(raw) > cap or ident(before) != ident(after) or ident(before) != ident(current):
            raise ValueError('Vendor source unavailable')
        return raw
    finally:
        os.close(fd)


def source_identity():
    result = {}
    for name, expected in SOURCE.items():
        path = SDK / 'synthid_text' / name
        if path.is_symlink() or path.parent.is_symlink() or SDK.is_symlink():
            raise ValueError('Vendor source unavailable')
        raw = read_source(path)
        if len(raw) > 65536 or hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError('Vendor source unavailable')
        result[name] = expected
    result['tools/synthid_input.py'] = hashlib.sha256(read_source(Path(__file__))).hexdigest()
    result['scripts/inspect-synthid-input.py'] = hashlib.sha256(read_source(ROOT / 'scripts/inspect-synthid-input.py')).hexdigest()
    return result


def empty(state, reason):
    return {'format': 'ai-trust-id-vendor-input/v1', 'vendor': 'Google DeepMind SynthID Text',
            'profile': PROFILE, 'state': state, 'reason': reason, 'verified': False,
            'tags': [], 'text_relationship': 'UNBOUND', 'origin_established': False,
            'statistics': None, 'subject': None, 'method': None, 'configuration': None,
            'token_ids_included': False, 'research_submitted': False}


def observed(packet, p_value, positions, ones):
    trials = positions * 30
    if type(positions) is not int or type(ones) is not int or not 0 <= positions <= max(0, len(packet['token_ids']) - 4) or not 0 <= ones <= trials:
        raise ValueError('Invalid vendor statistics')
    if type(p_value) is not float or not math.isfinite(p_value) or not 0 <= p_value <= 1:
        raise ValueError('Invalid vendor statistics')
    row = empty('OBSERVED' if positions else 'INSUFFICIENT',
                'conditional_research_statistic' if positions else 'no_scored_positions')
    row['statistics'] = {'p_value': p_value if positions else None,
                         'scored_positions': positions, 'trials': trials, 'ones': ones}
    row['subject'] = {'kind': 'generated_token_ids', 'token_count': len(packet['token_ids']),
                      'sha256': hashlib.sha256(canonical(packet['token_ids'])).hexdigest(),
                      'packet_sha256': hashlib.sha256(canonical(packet)).hexdigest()}
    row['configuration'] = {k: packet[k] for k in ('public_key', 'vocabulary_size', 'eos_token_id', 'prompt_removed')}
    row['configuration'].update({'ngram_len': 5, 'depth': 30, 'context_history_size': 1024, 'num_leaves': 2})
    row['method'] = {'upstream_commit': UPSTREAM, 'sdk_version': '0.3.0',
                     'detector': 'FrequentistDetector', 'sources': source_identity()}
    return row


def score(packet):
    """Execute the exact optional official detector. Called only in the child."""
    packet = validate_packet(packet)
    before = source_identity()
    import importlib.metadata
    import sys
    manifest = read_source(SDK / 'sources.json')
    if hashlib.sha256(manifest).hexdigest() != 'e6abc9476ba0e5ad94b94bc85b0095c7055fe1a6cdb67782472b41f66e363503':
        raise ValueError('Vendor source unavailable')
    versions = json.loads(manifest)['runtime_versions']
    if any(importlib.metadata.version(name) != version for name, version in versions.items()):
        raise ValueError('Vendor runtime unavailable')
    sys.path.insert(0, str(SDK))
    import torch
    from synthid_text.logits_processing import SynthIDLogitsProcessor
    from synthid_text.detector_frequentist import FrequentistDetector
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    processor = SynthIDLogitsProcessor(ngram_len=5, key=packet['public_key'], depth=30,
                                     context_history_size=1024, device=torch.device('cpu'))
    if len(packet['token_ids']) < 5:
        result = observed(packet, 1.0, 0, 0)
    else:
        ids = torch.tensor([packet['token_ids']], dtype=torch.long, device='cpu')
        with torch.no_grad():
            g_values, mask = processor.compute_g_values_and_mask(ids, packet['eos_token_id'])
            positions = int(mask.sum().item())
            ones = int((g_values * mask.unsqueeze(-1)).sum().item())
            p = float(FrequentistDetector(processor, packet['eos_token_id']).p_value(ids)[0])
        result = observed(packet, p, positions, ones)
    if source_identity() != before:
        raise ValueError('Vendor source changed')
    return result


def validate_result(row, packet):
    packet = validate_packet(packet)
    if type(row) is not dict or set(row) != set(empty('UNAVAILABLE', 'x')) or type(row.get('statistics')) is not dict:
        raise ValueError('Invalid vendor result')
    stats = row['statistics']
    if set(stats) != {'p_value', 'scored_positions', 'trials', 'ones'}:
        raise ValueError('Invalid vendor result')
    p = stats['p_value']
    expected = observed(packet, 1.0 if p is None else p, stats['scored_positions'], stats['ones'])
    if row != expected or canonical(row) != canonical(expected):
        raise ValueError('Vendor result does not bind requested input')
    return row


def _run(argv, raw, *, timeout=DEADLINE):
    # Direct fixed worker, never a shell or packet-selected executable.
    env = {k: v for k, v in os.environ.items() if k in {'PATH', 'SYSTEMROOT', 'TMPDIR', 'LANG'}}
    env.update({'OMP_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1',
                'VECLIB_MAXIMUM_THREADS': '1', 'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1',
                'PYTHONDONTWRITEBYTECODE': '1', 'TOKENIZERS_PARALLELISM': 'false'})
    deadline = time.monotonic() + timeout
    selector = None
    child = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                             stderr=subprocess.DEVNULL, env=env, start_new_session=True, close_fds=True, bufsize=0)
    try:
        selector = selectors.DefaultSelector()
        output = bytearray()
        offset = 0
        os.set_blocking(child.stdin.fileno(), False)
        os.set_blocking(child.stdout.fileno(), False)
        selector.register(child.stdin, selectors.EVENT_WRITE, 'input')
        selector.register(child.stdout, selectors.EVENT_READ, 'output')
        eof = False
        while not eof:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError('Vendor worker unavailable')
            for key, _ in selector.select(min(remaining, .1)):
                if key.data == 'input':
                    try:
                        offset += os.write(key.fd, raw[offset:offset + 4096])
                    except BlockingIOError:
                        continue
                    except BrokenPipeError:
                        offset = len(raw)
                    if offset == len(raw):
                        selector.unregister(key.fileobj)
                        key.fileobj.close()
                else:
                    try:
                        data = os.read(key.fd, min(4096, MAX_OUTPUT - len(output) + 1))
                    except BlockingIOError:
                        continue
                    if not data:
                        selector.unregister(key.fileobj)
                        eof = True
                        break
                    output.extend(data)
                    if len(output) > MAX_OUTPUT:
                        raise ValueError('Vendor worker unavailable')
        remaining = deadline - time.monotonic()
        if remaining <= 0 or child.wait(timeout=max(.001, remaining)) != 0:
            raise ValueError('Vendor worker unavailable')
        return bytes(output)
    finally:
        # Known-reaped IDs must never be signaled again, even after later errors.
        try:
            if child.returncode is None:
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                child.wait(timeout=5)
        finally:
            try:
                if selector is not None:
                    selector.close()
            finally:
                try:
                    child.stdin.close()
                finally:
                    child.stdout.close()


def inspect(packet, runtime):
    try:
        packet = validate_packet(packet)
    except (ValueError, TypeError, OverflowError):
        return empty('UNSUPPORTED', 'invalid_or_unsupported_packet')
    try:
        before = source_identity()
        runtime = Path(runtime).absolute()
        # The operator chooses a trusted runtime; the packet cannot choose it.
        if runtime.name != 'python' or not runtime.is_file():
            raise ValueError('Vendor runtime unavailable')
        raw = _run([str(runtime), '-I', '-B', str(ROOT / 'scripts/inspect-synthid-input.py'), '--worker'], canonical(packet))
        result = validate_result(parse(raw), packet)
        if source_identity() != before:
            raise ValueError('Vendor source changed')
        return result
    except (OSError, ValueError, TypeError, ImportError, RuntimeError, subprocess.SubprocessError):
        return empty('UNAVAILABLE', 'no_valid_vendor_observation')


def brief(row):
    if row['state'] == 'OBSERVED':
        s = row['statistics']
        return (f"SynthID reference: {s['scored_positions']} scored positions; raw p-value {s['p_value']:.6g}. "
                'Unverified research input; no tag or AI-origin verdict.')
    if row['state'] == 'INSUFFICIENT':
        return 'SynthID reference: insufficient scored positions. No watermark or origin conclusion.'
    return 'SynthID reference: unavailable or unsupported. Your personal checks remain separate.'
