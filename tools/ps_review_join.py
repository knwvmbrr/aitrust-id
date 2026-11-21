"""Owner-private advisory join. Hash consistency never certifies human labels."""
import hashlib
import json
import os
from pathlib import Path
import runpy
import selectors
import signal
import subprocess
import sys
import tempfile
import time

from tools.blind_review_io import directory, member, source
from tools.review_execution import canonical, execution_context

ROOT = Path(__file__).resolve().parents[1]
REVIEW = runpy.run_path(str(ROOT / 'scripts/prepare-ps-review.py'))
PS = runpy.run_path(str(ROOT / 'scripts/check-ps.py'))
FORMAT = 'ps-explicit-adjudication-input/v1'
MAX_TOTAL = 32_000_000
MAX_OUTPUT = 16_000_000
MAX_ADJUDICATION = 4_000_000
COHORT_SECONDS = 60
FILES = {'manifest.json': 64000, 'execution-context.json': 64000,
         'items.jsonl': 16_000_000, 'reviewer-1.json': 10_000_000,
         'reviewer-2.json': 10_000_000}
PRODUCER_FILES = ('tools/ps_review_join.py', 'scripts/ps-review-join.py',
                  'scripts/check-ps.py', 'scripts/build-device-detector.py',
                  'protocol/normalization.py', 'protocol/unicode15-data.json',
                  'services/evaluator/app.py')


class JoinError(ValueError):
    pass


class ExportUncertain(JoinError):
    """Filesystem failure leaves publication/cleanup state unconfirmed."""


def need(ok):
    if not ok:
        raise JoinError('Advisory join unavailable; no result exported.')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return canonical(value)


def sources():
    return {p: sha((ROOT / p).read_bytes()) for p in PRODUCER_FILES}


def capture(packet):
    raw = {}; total = 0
    with directory(packet, ROOT) as fd:
        for name, limit in FILES.items():
            value = member(fd, name, min(limit, MAX_TOTAL - total))
            total += len(value); need(total <= MAX_TOTAL)
            raw[name] = value
    return raw


def snapshot(packet):
    raw = capture(packet)
    comparison = REVIEW['compare'](packet, 'json', True)
    need(raw == capture(packet) and comparison['execution_binding_verified'])
    manifest = REVIEW['strict_json'](raw['manifest.json'])
    rows = REVIEW['parse_items'](raw['items.jsonl'])
    forms = [REVIEW['strict_json'](raw[f'reviewer-{i}.json']) for i in (1, 2)]
    labels = [{item['id']: item['label'] for item in form['items']} for form in forms]
    binding = {'format': FORMAT, 'dataset_sha256': manifest['dataset_sha256'],
               'method_sha256': manifest['method_sha256'],
               'packet_members_sha256': {n: sha(v) for n, v in raw.items()}}
    return raw, comparison, rows, labels, binding


def template(packet):
    raw, _, rows, _, binding = snapshot(packet)
    result = {**binding, 'decisions': [
        {'id': item['id'], 'item_sha256': sha(encoded(item)), 'label': None,
         'reason': ''} for item in rows]}
    need(len(encoded(result)) <= MAX_ADJUDICATION and raw == capture(packet))
    return result


def decisions(value, binding, rows):
    need(type(value) is dict and set(value) == set(binding) | {'decisions'})
    need({k: value[k] for k in binding} == binding)
    entries = value['decisions']; need(type(entries) is list and len(entries) == len(rows))
    expected = {r['id']: r for r in rows}; result = {}
    for item in entries:
        need(type(item) is dict and set(item) == {'id', 'item_sha256', 'label', 'reason'})
        key = item['id']; need(type(key) is str and key in expected and key not in result)
        need(item['item_sha256'] == sha(encoded(expected[key])))
        need(type(item['label']) is str and item['label'] in ('positive', 'negative', 'ambiguous'))
        reason = item['reason']
        need(type(reason) is str and 0 < len(reason.strip()) <= 2000 and len(reason) <= 2000 and '\0' not in reason)
        result[key] = item
    need(set(result) == set(expected))
    return result


def predict(text, remaining):
    """Reuse the actual unchanged standalone PS worker, with held finite stdin."""
    need(type(text) is str and text.strip() and len(text) <= PS['MAX_CHARS'])
    raw = text.encode('utf-8', 'strict'); need(len(raw) <= PS['MAX_BYTES'])
    child = None; selector = selectors.DefaultSelector(); output = bytearray()
    deadline = time.monotonic() + min(remaining, PS['DEADLINE'])
    try:
        with tempfile.TemporaryFile() as input_file:
            input_file.write(raw); input_file.seek(0)
            child = subprocess.Popen([sys.executable, '-I', '-S', '-B',
                str(ROOT / 'scripts/check-ps.py'), '--worker'], stdin=input_file,
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                start_new_session=True, close_fds=True,
                env={'PATH': os.defpath, 'LANG': 'C.UTF-8'})
            os.set_blocking(child.stdout.fileno(), False)
            selector.register(child.stdout, selectors.EVENT_READ)
            eof = False
            while not eof:
                left = deadline - time.monotonic(); need(left > 0)
                for key, _ in selector.select(min(.1, left)):
                    try:
                        chunk = os.read(key.fd, min(65536, PS['MAX_RESULT'] - len(output) + 1))
                    except BlockingIOError:
                        continue
                    if not chunk:
                        eof = True; break
                    need(len(chunk) <= PS['MAX_RESULT'] - len(output)); output.extend(chunk)
            left = deadline - time.monotonic(); need(left > 0)
            code = child.wait(timeout=left); need(code == 0 and time.monotonic() <= deadline)
        return PS['validate'](REVIEW['strict_json'](bytes(output)), text)
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


def join(packet, adjudication):
    started = time.monotonic(); deadline = started + COHORT_SECONDS
    before = sources()
    raw, comparison, rows, labels, binding = snapshot(packet)
    adjudicated_raw = source(adjudication, ROOT, MAX_ADJUDICATION)
    selected = decisions(REVIEW['strict_json'](adjudicated_raw), binding, rows)
    counts = dict(tp=0, fp=0, fn=0, tn=0); categories = {}; records = []; failures = []
    ambiguous = []; total = 0
    for item in rows:
        remaining = deadline - time.monotonic(); need(remaining > 0)
        prediction = predict(item['text'], remaining)
        decision = selected[item['id']]; actual = decision['label']
        positive = prediction['state'] == 'FINDING'
        category = item['category']
        category_counts = categories.setdefault(category, {**dict(tp=0, fp=0, fn=0, tn=0), 'ambiguous': 0})
        if actual == 'ambiguous':
            ambiguous.append(item['id']); category_counts['ambiguous'] += 1
        else:
            key = 'tp' if actual == 'positive' and positive else 'fn' if actual == 'positive' else 'fp' if positive else 'tn'
            counts[key] += 1; category_counts[key] += 1
            if key in ('fp', 'fn'):
                failures.append({'id': item['id'], 'category': category, 'error': key})
        record = {'id': item['id'], 'item_sha256': sha(encoded(item)),
            'raw_text_sha256': sha(item['text'].encode()), 'source_field_sha256': sha(item['source'].encode()),
            'category': category, 'reviewer_labels': [x[item['id']] for x in labels],
            'explicit_decision': actual, 'decision_reason_sha256': sha(decision['reason'].encode()),
            'prediction': prediction}
        size = len(encoded(record)); need(size <= MAX_OUTPUT - total)
        total += size; records.append(record)
    need(time.monotonic() <= deadline)
    need(raw == capture(packet) and source(adjudication, ROOT, MAX_ADJUDICATION) == adjudicated_raw)
    REVIEW['compare'](packet, 'json', True)
    need(before == sources() and time.monotonic() <= deadline)
    report = {'PS': {**counts, 'category_failures': failures, 'category_counts': categories},
        'dataset': {'sha256': binding['dataset_sha256'], 'kind': 'advisory_review_join',
            'independently_labeled': False, 'method_fixed_before_run': False},
        'advisory': {'format': 'ps-adjudicated-predictions/v1', 'packet_binding': binding,
            'adjudication_sha256': sha(adjudicated_raw), 'producer_sources': before,
            'route': 'standalone-PS-source-projection-after-frozen-NFC',
            'frozen_recipe_consistency_verified': True, 'human_adjudication_verified': False,
            'independence_verified': False, 'sampling_accepted': False,
            'release_assessed': False, 'evaluation_gate_pass': False,
            'item_count': len(rows), 'ambiguous_ids': ambiguous,
            'binary_denominator': sum(counts.values()),
            'original_disagreement_ids': comparison['disagreement_ids'],
            'original_ambiguous_ids': comparison['ambiguous_ids'],
            'calibration_supplied': False, 'heuristic_scores_are_probabilities': False}}
    evidence = {'format': 'ps-adjudicated-private-items/v1', 'packet_binding': binding,
                'adjudication_sha256': sha(adjudicated_raw), 'records': records}
    files = {'report.json': encoded(report) + b'\n', 'predictions.json': encoded(evidence) + b'\n'}
    need(sum(map(len, files.values())) <= MAX_OUTPUT)
    return files, lambda: (need(raw == capture(packet)),
        need(source(adjudication, ROOT, MAX_ADJUDICATION) == adjudicated_raw),
        need(before == sources()), need(time.monotonic() <= deadline))


def publish(path, files, stable):
    """Exclusive fixed-name export with single raw-FD ownership and rollback."""
    path = Path(path).absolute(); need(set(files) in ({'adjudication.json'}, {'report.json', 'predictions.json'}))
    need(all(type(v) is bytes for v in files.values()) and sum(map(len, files.values())) <= MAX_OUTPUT)
    stable()
    with directory(path.parent, ROOT) as parent:
        os.mkdir(path.name, 0o700, dir_fd=parent)
        fd = None; owned = {}; directory_id = None
        try:
            fd = os.open(path.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            info = os.fstat(fd); directory_id = (info.st_dev, info.st_ino)
            for name, value in files.items():
                output = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=fd)
                try:
                    info = os.fstat(output); owned[name] = (info.st_dev, info.st_ino)
                    offset = 0
                    while offset < len(value):
                        wrote = os.write(output, memoryview(value)[offset:]); need(wrote > 0); offset += wrote
                    os.fsync(output)
                finally:
                    os.close(output)
            stable()
            need(set(os.listdir(fd)) == set(files))
            for name, value in files.items():
                info = os.stat(name, dir_fd=fd, follow_symlinks=False)
                need((info.st_dev, info.st_ino) == owned[name] and member(fd, name, len(value)) == value)
            info = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
            need((info.st_dev, info.st_ino) == directory_id)
            os.fsync(fd); os.fsync(parent)
            stable()
        except BaseException:
            uncertain = fd is None
            if fd is not None:
                for name, identity in owned.items():
                    try:
                        info = os.stat(name, dir_fd=fd, follow_symlinks=False)
                        if (info.st_dev, info.st_ino) == identity:
                            os.unlink(name, dir_fd=fd)
                        else:
                            uncertain = True
                    except FileNotFoundError:
                        pass
                    except OSError:
                        uncertain = True
                try:
                    info = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
                    if (info.st_dev, info.st_ino) == directory_id:
                        os.rmdir(path.name, dir_fd=parent)
                    else:
                        uncertain = True
                except FileNotFoundError:
                    pass
                except OSError:
                    uncertain = True
            if uncertain:
                raise ExportUncertain('Private output may remain; do not accept it.') from None
            raise
        finally:
            if fd is not None:
                owned_fd = fd; fd = None
                try:
                    os.close(owned_fd)
                except OSError:
                    raise ExportUncertain('Private output may remain; do not accept it.') from None
