import copy
import importlib.util
import json
import os
from pathlib import Path
import socket
import stat
from unittest.mock import Mock

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('local_setup', ROOT / 'scripts/setup-local.py')
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


def state():
    return {'version': 1, 'engine': 'podman', 'project': 'aitrust-local-' + 'a' * 32,
            'containers': ['b' * 64], 'networks': ['c' * 64], 'images': ['d' * 64], 'status': 'starting'}


@pytest.mark.parametrize('network',[
    {'internal':True,'subnets':[{'subnet':'10.89.0.0/24','gateway':'10.89.0.1'}]},
    {'Internal':True,'IPAM':{'Config':[{'Subnet':'10.89.0.0/24','Gateway':'10.89.0.1'}]}},
])
def test_backends_get_distinct_reserved_private_addresses(network):
    assert setup.private_dependency_addresses(network)=={'anonymizer':'10.89.0.2','evaluator':'10.89.0.3'}


def test_reserved_addresses_exclude_a_nonstandard_gateway():
    row={'internal':True,'subnets':[{'subnet':'172.22.0.0/24','gateway':'172.22.0.2'}]}
    assert setup.private_dependency_addresses(row)=={'anonymizer':'172.22.0.3','evaluator':'172.22.0.4'}


@pytest.mark.parametrize('network',[
    {'internal':False,'subnets':[{'subnet':'10.89.0.0/24','gateway':'10.89.0.1'}]},
    {'internal':True,'subnets':[]},
    {'internal':True,'IPAM':None},
    {'internal':True,'subnets':[None]},
    {'internal':True,'subnets':[{'subnet':'bad','gateway':'10.89.0.1'}]},
    {'internal':True,'subnets':[{'subnet':'8.8.8.0/24','gateway':'8.8.8.1'}]},
    {'internal':True,'subnets':[{'subnet':'10.89.0.0/31','gateway':'10.89.0.1'}]},
    {'internal':True,'subnets':[{'subnet':'10.89.0.0/24','gateway':'10.90.0.1'}]},
    {'internal':True,'subnets':[{'subnet':'10.89.0.0/24','gateway':'10.89.0.0'}]},
    {'internal':True,'subnets':[{'subnet':'fd00::/64'}]},
    {'internal':True,'subnets':[{'subnet':'10.89.0.0/24','gateway':'10.89.0.1'},
                              {'subnet':'10.90.0.0/24','gateway':'10.90.0.1'}]},
])
def test_untrusted_or_ambiguous_subnet_cannot_choose_backend_addresses(network):
    with pytest.raises(setup.SetupError):setup.private_dependency_addresses(network)


def test_state_is_private_exclusive_and_outside_repo(tmp_path):
    folder = setup.private_directory(tmp_path / 'private', create=True)
    setup.write_state(folder, state())
    assert stat.S_IMODE(folder.stat().st_mode) == 0o700
    assert stat.S_IMODE((folder / 'setup.json').stat().st_mode) == 0o600
    assert setup.read_state(folder) == state()
    before = (folder / 'setup.json').read_bytes()
    with pytest.raises(FileExistsError):
        setup.private_directory(folder, create=True)
    assert (folder / 'setup.json').read_bytes() == before
    with pytest.raises(setup.SetupError):
        setup.private_directory(ROOT / 'unsafe-state', create=True)


@pytest.mark.parametrize('change', ['public-directory', 'linked-parent', 'public-record', 'linked-record'])
def test_untrusted_paths_are_refused_without_mutation(tmp_path, change):
    folder = setup.private_directory(tmp_path / 'private', create=True)
    setup.write_state(folder, state())
    before = (folder / 'setup.json').read_bytes()
    if change == 'public-directory':
        folder.chmod(0o755)
        call = lambda: setup.private_directory(folder)
    elif change == 'linked-parent':
        (tmp_path / 'linked').symlink_to(folder)
        call = lambda: setup.private_directory(tmp_path / 'linked/new', create=True)
    elif change == 'public-record':
        (folder / 'setup.json').chmod(0o644)
        call = lambda: setup.read_state(folder)
    else:
        (folder / 'setup.json').rename(folder / 'original.json')
        (folder / 'setup.json').symlink_to(folder / 'original.json')
        call = lambda: setup.read_state(folder)
    with pytest.raises((setup.SetupError, OSError)):
        call()
    assert (folder / 'setup.json').read_bytes() == before


@pytest.mark.parametrize('field,value', [('engine', 'other'), ('project', 'unrelated'),
                                      ('containers', ['--all']), ('networks', ['short']), ('images', ['sha256:' + 'd' * 64])])
def test_untrusted_resource_record_cannot_authorize_cleanup(tmp_path, field, value):
    folder = setup.private_directory(tmp_path / 'private', create=True)
    row = state()
    row[field] = value
    setup.write_state(folder, row)
    with pytest.raises(setup.SetupError):
        setup.read_state(folder)


def test_cleanup_refuses_changed_ownership_and_preserves_resource():
    engine = Mock()
    engine.inspect.return_value = {'Config': {'Labels': {setup.LABEL: 'someone-else'}},
                                   'Labels': {setup.LABEL: 'someone-else'}}
    row = state()
    before = copy.deepcopy(row)
    assert setup.cleanup(engine, row) is False
    engine.run.assert_not_called()
    assert row == before


def test_cleanup_removes_only_matching_recorded_ids():
    engine = Mock()
    row = state()
    engine.inspect.return_value = {'Config': {'Labels': {setup.LABEL: row['project']}},
                                   'Labels': {setup.LABEL: row['project']}}
    assert setup.cleanup(engine, row) is True
    assert [call.args for call in engine.run.call_args_list] == [
        ('container', 'rm', '-f', 'b' * 64), ('network', 'rm', 'c' * 64), ('image', 'rm', 'd' * 64)]
    assert all(row[key] == [] for key in ('containers', 'networks', 'images'))


def test_podman_lowercase_network_labels_are_checked():
    engine = Mock()
    row = state()
    engine.inspect.return_value = {'labels': {setup.LABEL: row['project']}, 'internal': True}
    assert setup.owned(engine, 'network', 'c' * 64, row['project'])['internal'] is True
    engine.inspect.return_value['labels'][setup.LABEL] = 'other'
    with pytest.raises(setup.SetupError):
        setup.owned(engine, 'network', 'c' * 64, row['project'])


@pytest.mark.parametrize('field', ['CapInh', 'CapPrm', 'CapEff', 'CapBnd', 'CapAmb'])
def test_actual_capability_sets_must_all_be_empty(field):
    values = {name: '0000000000000000' for name in ['CapInh', 'CapPrm', 'CapEff', 'CapBnd', 'CapAmb']}
    assert setup.no_process_capabilities(json.dumps(values))
    values[field] = '0000000000000001'
    assert not setup.no_process_capabilities(json.dumps(values))
    values.pop(field)
    assert not setup.no_process_capabilities(json.dumps(values))


@pytest.mark.parametrize('address', ['127.0.0.1', '0.0.0.0', '1.1.1.1', '169.254.1.2', '::1', 'example.test', None])
def test_dependency_addresses_are_bounded_private_inspection_only(address):
    row = {'NetworkSettings': {'Networks': {'private': {'NetworkID': 'a' * 64, 'IPAddress': address}}}}
    with pytest.raises(setup.SetupError):
        setup.inspection_address(row, 'a' * 64)


def test_dependency_address_must_match_recorded_network():
    row = {'NetworkSettings': {'Networks': {'private': {'NetworkID': 'a' * 64, 'IPAddress': '10.89.1.2'}}}}
    assert setup.inspection_address(row, 'a' * 64) == '10.89.1.2'
    with pytest.raises(setup.SetupError):
        setup.inspection_address(row, 'b' * 64)


def test_build_dns_uses_configured_upstream_instead_of_host_stub(tmp_path):
    stub = tmp_path / 'stub'
    upstream = tmp_path / 'upstream'
    stub.write_text('nameserver 127.0.0.53\n')
    upstream.write_text('nameserver 192.0.2.53\nnameserver 192.0.2.53\n')
    assert setup.build_dns((stub, upstream)) == ['192.0.2.53']


@pytest.mark.parametrize('text', ['nameserver 127.0.0.1', 'nameserver ::1',
                                'nameserver 0.0.0.0', 'nameserver 224.0.0.1', 'nameserver invalid'])
def test_unusable_builder_resolvers_refused_without_arbitrary_fallback(tmp_path, text):
    path = tmp_path / 'resolver'
    path.write_text(text)
    with pytest.raises(setup.SetupError):
        setup.build_dns((path,))


def test_actual_port_collision_precedes_state_creation(tmp_path, monkeypatch, capsys):
    engine = Mock()
    monkeypatch.setattr(setup, 'Engine', lambda name: engine)
    with socket.socket() as listener:
        try:
            listener.bind(('127.0.0.1', 8787))
        except OSError:
            pytest.skip('Port already used; exercised by real Linux failure controls')
        listener.listen()
        assert setup.main(['--state-dir', str(tmp_path / 'unused')]) == 1
    assert not (tmp_path / 'unused').exists()
    assert 'Port 8787 is already in use' in capsys.readouterr().err


def test_missing_engine_does_not_create_credentials(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(setup.shutil, 'which', lambda name: None)
    assert setup.main(['--state-dir', str(tmp_path / 'unused')]) == 1
    assert not (tmp_path / 'unused').exists()
    assert 'Install the selected' in capsys.readouterr().err


def test_failed_build_cleans_only_owned_ids_and_never_prints_diagnostics(tmp_path, monkeypatch, capsys):
    engine = Mock()
    monkeypatch.setattr(setup, 'Engine', lambda name: engine)
    monkeypatch.setattr(setup, 'preflight', lambda engine: None)
    monkeypatch.setattr(setup, 'install_checker', lambda *args: 'unused')
    def fail(engine, folder, row, build_network):
        assert build_network == 'private'
        row['containers'].append('b' * 64)
        engine.inspect.return_value = {'Config': {'Labels': {setup.LABEL: row['project']}}}
        raise OSError('secret-token-and-private-engine-output')
    monkeypatch.setattr(setup, 'build_and_start', fail)
    assert setup.main(['--state-dir', str(tmp_path / 'private')]) == 1
    row = setup.read_state(tmp_path / 'private')
    assert row['status'] == 'failed' and row['cleanup_complete'] is True
    assert row['containers'] == []
    assert (tmp_path / 'private/runtime.env').is_file()
    output = capsys.readouterr()
    assert 'secret-token' not in output.out + output.err
    token = setup.aitrust.read_token(tmp_path / 'private/runtime.env')
    assert token not in output.out + output.err
    engine.run.assert_called_once_with('container', 'rm', '-f', 'b' * 64)


@pytest.mark.parametrize('mutation', ['pids', 'memory', 'root', 'write', 'capabilities', 'privileges', 'published', 'network', 'source'])
def test_effective_engine_configuration_must_be_verified(mutation):
    row = state()
    row['containers'] = ['b' * 64, 'c' * 64, 'd' * 64]
    engine = Mock()
    def inspected(kind, identity):
        if kind == 'network':
            return {'Labels': {setup.LABEL: row['project']}, 'Internal': mutation != 'network'}
        role = setup.ROLES[row['containers'].index(identity)]
        result = {'Config': {'User': '10001:10001', 'Labels': {setup.LABEL: row['project']}},
                  'HostConfig': {'ReadonlyRootfs': True, 'PidsLimit': 128,
                                 'Memory': setup.MEMORY[role] * 1024 * 1024, 'CapDrop': ['ALL'],
                                 'SecurityOpt': ['no-new-privileges'], 'PortBindings': {}},
                  'NetworkSettings': {'Networks': {'private': {}}}}
        field, value = {'pids': ('PidsLimit', 0), 'memory': ('Memory', 0),
                        'write': ('ReadonlyRootfs', False), 'capabilities': ('CapDrop', []),
                        'privileges': ('SecurityOpt', []), 'published': ('PortBindings', {'8000/tcp': [{}]})}.get(mutation, ('unused', None))
        if field != 'unused':
            result['HostConfig'][field] = value
        if mutation == 'root':
            result['Config']['User'] = '0'
        return result
    engine.inspect.side_effect = inspected
    engine.run.return_value = 'wrong-source'
    with pytest.raises(setup.SetupError):
        setup.verify_security(engine, row)


def test_failed_engine_stdout_and_stderr_are_not_exposed(monkeypatch):
    result = Mock(returncode=1, stdout=b'private-token', stderr=b'private-input')
    monkeypatch.setattr(setup.subprocess, 'run', lambda *a, **kw: result)
    with pytest.raises(setup.SetupError) as error:
        setup.command(['unused'])
    assert 'private' not in str(error.value)


def test_wheelhouse_never_relaxes_lock_hashes(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(setup, 'command', lambda argv, *args: calls.append(argv) or '')
    setup.install_checker(tmp_path, tmp_path)
    pip = calls[-1]
    assert '--require-hashes' in pip and '--isolated' in pip and '--only-binary=:all:' in pip
    assert '--no-index' in pip and '--find-links' in pip


def test_stop_obeys_recorded_engine_not_a_conflicting_argument(tmp_path, monkeypatch):
    folder = setup.private_directory(tmp_path / 'private', create=True)
    row = state()
    row.update(containers=[], networks=[], images=[])
    setup.write_state(folder, row)
    selected = []
    monkeypatch.setattr(setup, 'Engine', lambda name: selected.append(name) or Mock())
    assert setup.main(['--stop', '--engine', 'docker', '--state-dir', str(folder)]) == 0
    assert selected == ['podman']
    assert setup.read_state(folder)['status'] == 'stopped'
