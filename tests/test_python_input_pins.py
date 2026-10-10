"""Installed lock agreement for direct and frozen Python build inputs."""
import pytest
from scripts.dependency_pins import pin, pinned_inputs, python_lock, verify_inputs

HASH = ' --hash=sha256:' + 'a' * 64


def test_normalized_inputs_match_real_hashed_install_identity():
    result = verify_inputs('Some_Pkg==1.2.3\n', 'some-pkg==1.2.3' + HASH, 'some.pkg==1.2.3\n')
    assert result['direct_pins'] == 1 and result['frozen_input_checked']


@pytest.mark.parametrize('manifest', ['foo==1.0', 'bar==2.0'])
def test_changed_or_missing_direct_pin_is_not_an_install_update(manifest):
    with pytest.raises(ValueError, match='manifest and installed lock disagree'):
        verify_inputs(manifest, 'foo==2.0' + HASH)


def test_direct_input_and_frozen_version_must_both_match():
    with pytest.raises(ValueError, match='manifest and frozen input disagree'):
        verify_inputs('foo==2.0', 'foo==2.0' + HASH, 'foo==1.0')


def test_frozen_transitive_pin_cannot_drift():
    with pytest.raises(ValueError, match='Frozen Python input and installed lock disagree'):
        verify_inputs('foo==2.0', 'foo==2.0' + HASH + '\nbar==3.0' + HASH, 'foo==2.0\nbar==2.0')


def test_complete_accepted_extra_has_installed_dependencies():
    deps = ['httptools', 'python-dotenv', 'pyyaml', 'uvloop', 'watchfiles', 'websockets']
    lock = '\n'.join(name + '==1.0' + HASH for name in ['uvicorn', *deps])
    assert verify_inputs('uvicorn[standard]==1.0', lock)['manifest_matches_install_lock']
    for name in deps:
        with pytest.raises(ValueError, match='extra is incomplete'):
            verify_inputs('uvicorn[standard]==1.0', '\n'.join(line for line in lock.splitlines() if not line.startswith(name+'==')))


@pytest.mark.parametrize('value', ['foo>=1.0', 'foo===1.0', 'foo==latest', 'foo==1.0;python_version>"3"',
                                 '--index-url https://example.invalid', '-r other.txt', 'foo[other]==1.0',
                                 'uvicorn[standard,standard]==1.0', 'foo==1.0 \\', 'foo.==1.0', 'foo-==1.0', ''])
def test_unreviewed_forms_cannot_be_unconstrained(value):
    with pytest.raises(ValueError):
        pinned_inputs(value)


def test_normalized_duplicate_inputs_are_refused():
    with pytest.raises(ValueError, match='Duplicate normalized'):
        pinned_inputs('a_b==1.0\na.b==1.0')


@pytest.mark.parametrize('url', ['https://user:secret@example.invalid/a.whl',
                               'https://example.invalid/a.whl?token=synthetic',
                               'https://example.invalid/a.whl#not-a-hash'])
def test_private_or_unknown_url_parameters_refused(url):
    with pytest.raises(ValueError):
        pin('foo @ ' + url)


def test_model_artifact_url_and_fragment_hash_are_bound():
    url = 'https://example.invalid/model.whl#sha256=' + 'a'*64
    assert verify_inputs('foo @ '+url, 'foo @ '+url+HASH, 'foo @ '+url)['manifest_matches_install_lock']
    with pytest.raises(ValueError, match='URL artifact hash disagrees'):
        python_lock('foo @ '+url+' --hash=sha256:'+'b'*64)
    with pytest.raises(ValueError, match='manifest and installed lock disagree'):
        verify_inputs('foo @ https://example.invalid/changed.whl#sha256='+'a'*64, 'foo @ '+url+HASH)


def test_a_synchronized_change_is_accepted_not_permanently_pinned():
    for version in ['1.0', '2.0']:
        assert verify_inputs('foo=='+version, 'foo=='+version+HASH, 'foo=='+version)['manifest_matches_install_lock']
