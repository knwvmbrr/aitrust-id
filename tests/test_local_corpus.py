"""Exercise private source attachment, reproducible passages and corrupt-input rejection."""
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import pytest
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('local_corpus', ROOT/'protocol/corpus.py')
c = importlib.util.module_from_spec(spec); spec.loader.exec_module(c)


@pytest.fixture
def attached(tmp_path):
    tmp_path.chmod(0o700)
    source = tmp_path/'source.txt'
    source.write_text('🧪 Cafe\u0301 handbook. This is a source. This is a source.', encoding='utf-8')
    output = tmp_path/'corpus.json'
    c.create([('handbook', source)], output)
    return tmp_path, source, output


def test_nfc_codepoint_matches_are_bound_to_raw_document(attached):
    _, source, output = attached
    record = c.load(output)
    match = c.query(record, 'Café')['matches'][0]
    assert match['source_span'] == [2, 6]
    assert match['passage'] == 'Café'
    assert match['document_sha256'] == c.sha(source.read_bytes())
    assert c.query(record, 'a source')['matches'][1]['source_span'][0] > 20
    assert not c.query(record, 'missing')['tag_assertion']
    assert c.query(record, 'missing')['state'] == 'NO_REFERENCE_MATCH'
    assert output.stat().st_mode & 0o777 == 0o600


def test_reordered_sources_produce_same_version(tmp_path):
    tmp_path.chmod(0o700)
    a, b = tmp_path/'a.txt', tmp_path/'b.md'
    a.write_text('one'); b.write_text('two')
    c.create([('a', a), ('b', b)], tmp_path/'one.json')
    c.create([('b', b), ('a', a)], tmp_path/'two.json')
    assert (tmp_path/'one.json').read_bytes() == (tmp_path/'two.json').read_bytes()


def test_no_network_or_execution(attached, monkeypatch):
    monkeypatch.setattr(socket, 'socket', lambda *a, **k: pytest.fail('Network creation forbidden'))
    _, source, output = attached
    source.write_text('<script>alert(1)</script> $(touch DOES_NOT_RUN) https://example.invalid/ ESC\x1b[31m')
    output.unlink(); c.create([('passive', source)], output)
    assert len(c.query(c.load(output), '$(touch DOES_NOT_RUN)')['matches']) == 1
    assert not (ROOT/'DOES_NOT_RUN').exists()


@pytest.mark.parametrize('change', [
    lambda d: d['documents'][0].update(text='changed'),
    lambda d: d.update(manifest_sha256='0'*64),
    lambda d: d.update(format='local-reference-corpus/v2'),
    lambda d: d.update(extra='unexpected'),
    lambda d: d.update(documents=[]),
    lambda d: d['documents'].append(dict(d['documents'][0])),
    lambda d: d['documents'][0].update(text='\ud800'),
    lambda d: d['documents'][0].update(id='../private'),
    lambda d: d['documents'][0].update(sha256=123),
    lambda d: d['documents'][0].update(text=''),
])
def test_corruption_never_returns_partial_matches(attached, change):
    _, _, output = attached
    record = json.loads(output.read_text()); change(record)
    output.write_text(json.dumps(record))
    with pytest.raises(c.CorpusError): c.load(output)


@pytest.mark.parametrize('bad', ['{"format":1,"format":2}', '[]', '{', '{"x":NaN}', '['*1100, '{"x":'+ '9'*100000+'}', '{"x":1.5}'])
def test_invalid_json_rejected(attached, bad):
    _, _, output = attached; output.write_text(bad)
    with pytest.raises(c.CorpusError): c.load(output)


@pytest.mark.parametrize('value', [None, 5, '', '   ', '\ud800', 'a'*2001])
def test_invalid_query_rejected(attached, value):
    with pytest.raises(c.CorpusError): c.query(c.load(attached[2]), value)


def test_symlink_permissions_and_fifo_rejected(attached):
    folder, source, output = attached
    link = folder/'link.txt'; link.symlink_to(source)
    with pytest.raises(c.CorpusError): c.create([('one', link)], folder/'other.json')
    fifo = folder/'fifo.txt'; os.mkfifo(fifo)
    with pytest.raises(c.CorpusError): c.create([('one', fifo)], folder/'other.json')
    output.chmod(0o644)
    with pytest.raises(c.CorpusError, match='private'): c.load(output)


def test_oversize_duplicate_and_unsupported_sources(attached):
    folder, source, _ = attached
    for sources in ([], [('same', source)]*2, [('a', folder/'unsupported.pdf')], [('bad/id', source)], [('a', source)]*33):
        with pytest.raises(c.CorpusError): c.create(sources, folder/'next.json')
    source.write_bytes(b'a'*800001)
    with pytest.raises(c.CorpusError, match='byte limit'): c.create([('large', source)], folder/'next.json')
    source.write_text('a'*200001)
    with pytest.raises(c.CorpusError, match='character limit'): c.create([('large', source)], folder/'next.json')
    source.write_bytes(b'\xff')
    with pytest.raises(c.CorpusError, match='UTF-8'): c.create([('invalid', source)], folder/'next.json')


def test_total_limit_and_match_limit(attached):
    folder, source, output = attached
    source.write_text('é'*180000)
    with pytest.raises(c.CorpusError, match='total byte limit'):
        c.create([(str(i), source) for i in range(6)], folder/'next.json')
    source.write_text('needle '*30)
    output.unlink(); c.create([('many', source)], output)
    assert len(c.query(c.load(output), 'needle')['matches']) == 10


def test_existing_file_preserved_and_repository_storage_rejected(attached):
    folder, source, output = attached
    before = output.read_bytes()
    with pytest.raises(c.CorpusError, match='new'): c.create([('one', source)], output)
    assert output.read_bytes() == before
    with pytest.raises(c.CorpusError, match='outside'): c.create([('one', source)], ROOT/'private-corpus.json')
    folder.chmod(0o755)
    with pytest.raises(c.CorpusError, match='0700'): c.create([('one', source)], folder/'next.json')


def test_actual_command_workflow_and_safe_errors(attached):
    folder, source, output = attached
    command = [sys.executable, str(ROOT/'scripts/corpus.py')]
    create = subprocess.run(command+['create', '--output', str(folder/'cli.json'), '--source', f'guide={source}'], capture_output=True, text=True)
    assert create.returncode == 0 and not json.loads(create.stdout)['tag_assertion']
    found = subprocess.run(command+['query', '--corpus', str(folder/'cli.json'), '--text', 'Café'], capture_output=True, text=True)
    assert found.returncode == 0 and json.loads(found.stdout)['state'] == 'REFERENCE_MATCH'
    private = subprocess.run(command+['query', '--corpus', str(folder/'cli.json'), '--stdin'], input='Café', capture_output=True, text=True)
    assert private.returncode == 0 and json.loads(private.stdout) == json.loads(found.stdout)
    inspection = subprocess.run(command+['inspect', '--corpus', str(folder/'cli.json')], capture_output=True, text=True)
    assert inspection.returncode == 0 and 'text' not in json.loads(inspection.stdout)['documents'][0]
    failed = subprocess.run(command+['inspect', '--corpus', str(folder/'PRIVATE_CANARY')], capture_output=True, text=True)
    assert failed.returncode == 2 and 'PRIVATE_CANARY' not in failed.stderr
