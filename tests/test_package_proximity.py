"""Spelling resemblance must not turn into accusations or hidden installs."""
import copy
import itertools
import json
from pathlib import Path
import socket
import subprocess
import sys
import pytest
from protocol.corpus import CorpusError, encoded
from tools import package_proximity as p

ROOT = Path(__file__).resolve().parents[1]


def source(ecosystem='pypi'):
    names = ['requests', 'numpy', 'Pandas', 'my_package'] if ecosystem == 'pypi' else ['react', '@one/widget', '@two/other']
    return {'format': 'ranked-package-input/v1', 'ecosystem': ecosystem,
            'measurement': {'start': '2026-09-01T00:00:00Z', 'end': '2026-10-01T00:00:00Z',
                            'source_url': 'https://example.invalid/synthetic-ranking',
                            'metric': 'download_count_in_interval', 'synthetic': True},
            'packages': [{'rank': i, 'name': name, 'downloads': 1000-i}
                         for i, name in enumerate(names, 1)]}


def record(data=None):
    content = {'format': p.FORMAT, 'source_sha256': 'a'*64, 'input': data or source()}
    return dict(content, manifest_sha256=p.sha(encoded(content)))


def oracle(a, b):
    rows = list(range(len(b)+1))
    for i, left in enumerate(a, 1):
        new = [i]
        for j, right in enumerate(b, 1):
            new.append(min(rows[j]+1, new[-1]+1, rows[j-1]+(left != right)))
        rows = new
    return min(3, rows[-1])


def test_banded_distance_matches_independent_full_matrix_oracle():
    words = [''.join(word) for size in range(5) for word in itertools.product('ab', repeat=size)]
    for a, b in itertools.product(words, repeat=2):
        assert p.distance(a, b) == oracle(a, b), (a, b)
    for a, b in [('requests', 'reqeusts'), ('abc', 'abcdef'), ('', ''), ('a'*128, 'a'*126+'bc')]:
        assert p.distance(a, b) == oracle(a, b)


def test_similarity_exact_spans_identity_and_no_malice():
    subject = '  reqeusts\r\nnumppy\n'
    out = p.observe(record(), subject)
    assert out['state'] == 'SIMILAR_NAME'
    assert [(f['reference_name'], f['distance']) for f in out['findings']] == [('numpy', 1), ('requests', 2)]
    assert [subject[s:e] for f in out['findings'] for s, e in f['spans']] == ['numppy', 'reqeusts']
    assert out['method_sha256'] == p.sha((ROOT/'tools/package_proximity.py').read_bytes())
    assert out['subject_sha256'] == p.sha(subject.encode('ascii'))
    assert out['tags'] == [] and out['maliciousness_established'] is False
    assert out['reference_freshness'] == 'unestablished' and not out['ranking_independently_verified']
    assert out['measurement']['synthetic'] is True
    assert p.observe(record(), subject) == out


def test_pypi_equivalences_are_exact_not_suspicious():
    out = p.observe(record(), 'REQUESTS\nmy...__--package\npandas')
    assert out['exact_reference_matches'] == 3 and not out['findings']
    assert out['state'] == 'NO_SIMILAR_NAME'


def test_scopes_and_ecosystems_not_merged():
    r = record(source('npm'))
    assert p.observe(r, '@one/widget')['exact_reference_matches'] == 1
    out = p.observe(r, '@onf/widget')
    assert out['findings'] and out['findings'][0]['reference_name'] == '@one/widget'
    assert p.observe(r, '@two/widget')['state'] == 'NO_SIMILAR_NAME'
    assert p.observe(r, 'widget')['state'] == 'NO_SIMILAR_NAME'
    assert p.observe(record(), 'react')['state'] == 'NO_SIMILAR_NAME'


def test_top_n_limits_and_ordering():
    assert p.observe(record(), 'numppy', 1)['state'] == 'NO_SIMILAR_NAME'
    assert p.observe(record(), 'numppy', 2)['state'] == 'SIMILAR_NAME'
    out = p.observe(record(), 'requests')
    assert out['exact_reference_matches'] == 1 and not out['findings']


@pytest.mark.parametrize('subject', ['', ' ', '\x00', '\ud800', 'réquests', 'requests==2',
                                    'pip install requests', 'x\n'*17, 'x'*4097,
                                    'requests\vother', '../requests'])
def test_invalid_subject_refused(subject):
    with pytest.raises(CorpusError):
        p.observe(record(), subject)


@pytest.mark.parametrize('value', [True, 0, 5, -1, 1.5, '1'])
def test_invalid_top_n_refused(value):
    with pytest.raises(CorpusError):
        p.observe(record(), 'requests', value)


@pytest.mark.parametrize('name', ['Requests', 'react!', '@UPPER/name', '@one/name/extra',
                                 '-name', '../react', 'name with spaces', 'a'*129])
def test_unsupported_npm_names_refused(name):
    with pytest.raises(CorpusError):
        p.canonical(name, 'npm')


@pytest.mark.parametrize('mutation', [
    lambda d: d.update(ecosystem='cargo'),
    lambda d: d.update(format='future'),
    lambda d: d.update(packages=[]),
    lambda d: d['packages'][0].update(rank=True),
    lambda d: d['packages'][0].update(rank=2),
    lambda d: d['packages'][0].update(downloads=True),
    lambda d: d['packages'][0].update(downloads=-1),
    lambda d: d['packages'][0].update(downloads=10**16),
    lambda d: d['packages'][1].update(downloads=1001),
    lambda d: d['packages'][1].update(name='Requests'),
    lambda d: d['packages'][0].update(unknown='value'),
    lambda d: d['measurement'].update(synthetic='true'),
    lambda d: d['measurement'].update(metric='popularity'),
    lambda d: d['measurement'].update(start='2026-10-02T00:00:00Z'),
    lambda d: d['measurement'].update(end='2026-02-30T00:00:00Z'),
    lambda d: d['measurement'].update(end='2026-10-01'),
    lambda d: d['measurement'].update(source_url='https://user:pass@example.com'),
    lambda d: d['measurement'].update(source_url='file:///secret'),
    lambda d: d['measurement'].update(source_url='https://example.com:bad'),
    lambda d: d['measurement'].update(source_url='https://example.com/#fragment'),
    lambda d: d.update(extra='value'),
])
def test_invalid_even_rehashed_ranking_refused(mutation):
    data = source(); mutation(data)
    with pytest.raises(CorpusError):
        p.observe(record(data), 'requests')


def test_altered_manifest_and_unknown_envelope_rejected():
    r = record(); r['input']['packages'][0]['name'] = 'altered'
    with pytest.raises(CorpusError): p.observe(r, 'requests')
    r = record(); r['extra'] = 'value'
    r['manifest_sha256'] = p.sha(encoded({k:v for k,v in r.items() if k != 'manifest_sha256'}))
    with pytest.raises(CorpusError): p.observe(r, 'requests')


def test_actual_import_private_cli_and_failures(tmp_path, monkeypatch):
    tmp_path.chmod(0o700)
    src = tmp_path/'ranking.json'; src.write_text(json.dumps(source()))
    output = tmp_path/'snapshot.json'
    monkeypatch.setattr(socket, 'socket', lambda *a, **kw: (_ for _ in ()).throw(AssertionError('Network forbidden')))
    info = p.create(src, output)
    assert output.stat().st_mode & 0o777 == 0o600
    assert info['source_sha256'] == p.sha(src.read_bytes())
    assert p.observe(p.load(output), 'reqeusts')['findings']
    command = [sys.executable, str(ROOT/'scripts/package-proximity.py'), 'check', '--snapshot', str(output)]
    good = subprocess.run(command, input='reqeusts', text=True, capture_output=True)
    assert good.returncode == 0 and json.loads(good.stdout)['state'] == 'SIMILAR_NAME'
    bad = subprocess.run(command, input='PRIVATE_QUERY_CANARY==password', text=True, capture_output=True)
    assert bad.returncode == 2 and json.loads(bad.stdout)['state'] == 'UNAVAILABLE'
    assert 'PRIVATE_QUERY_CANARY' not in bad.stdout + bad.stderr
    output.chmod(0o644)
    with pytest.raises(CorpusError): p.load(output)
    output.chmod(0o600)
    with pytest.raises(CorpusError): p.create(src, output)
    link = tmp_path/'link'; link.symlink_to(output)
    with pytest.raises(CorpusError): p.load(link)
    src.write_text('{"format":"bad","format":"bad"}')
    with pytest.raises(CorpusError): p.create(src, tmp_path/'other.json')


def test_import_cli_and_future_rankings(tmp_path):
    tmp_path.chmod(0o700); src = tmp_path/'ranking.json'; output = tmp_path/'snapshot.json'
    src.write_text(json.dumps(source()))
    command = [sys.executable, str(ROOT/'scripts/package-proximity.py'), 'import', '--source', str(src), '--output', str(output)]
    assert subprocess.run(command, capture_output=True).returncode == 0
    data = source(); data['measurement']['end'] = '2999-10-01T00:00:00Z'
    src.write_text(json.dumps(data))
    result = subprocess.run(command[:-1]+[str(tmp_path/'future.json')], capture_output=True)
    assert result.returncode == 2 and not (tmp_path/'future.json').exists()


def test_all_reference_and_output_limits():
    data = source(); data['packages'] = [{'name': 'pack'+str(i), 'rank': i+1, 'downloads': 3000-i} for i in range(2049)]
    with pytest.raises(CorpusError): p.observe(record(data), 'pack0')
    data['packages'] = data['packages'][:100]
    out = p.observe(record(data), 'packz\n'*16)
    assert len(out['findings']) == 32 and out['total_matches'] > 32
    assert out['maximum_findings'] == 32
