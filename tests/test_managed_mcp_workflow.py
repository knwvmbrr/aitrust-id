"""Controlled signing-job security guards, not a generic YAML interpreter."""
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tests'))
from test_artifact_workflow import job_environment

MAIN_ONLY = ("    if: github.repository == 'knwvmbrr/aitrust-id' && github.ref == 'refs/heads/main' "
             "&& (github.event_name == 'push' || github.event_name == 'workflow_dispatch')")
OUTPUTS = ['checker.zip', 'evidence.json', 'artifact.spdx.json',
           'sbom.sigstore.json', 'trusted-root.jsonl', 'managed-verified.json']


def managed_job(source):
    names = re.findall(r'^  ([a-z][a-z0-9-]*):$', source, re.M)
    if len(names) != len(set(names)) or names.count('attest-managed-mcp') != 1:
        raise ValueError('Ambiguous controlled job')
    job = source.split('  attest-managed-mcp:\n', 1)[1]
    if re.search(r'^  [a-z][a-z0-9-]*:', job, re.M):
        raise ValueError('Controlled job must remain last')
    if job.splitlines().count(MAIN_ONLY) != 1:
        raise ValueError('Protected main identity required')
    if '    needs: [artifact-controls, managed-mcp-controls]' not in job:
        raise ValueError('Required independent controls missing')
    if ('    permissions:\n      contents: read\n      id-token: write\n      attestations: write\n' not in job
            or 'secrets.' in job or 'pull_request_target' in source):
        raise ValueError('Unsupported signing authority')
    expected = [f'            ${{{{ env.MCP_RELEASE_DIR }}}}/publish/{name}' for name in OUTPUTS]
    actual = [line for line in job.splitlines() if line.startswith('            ${{ env.MCP_RELEASE_DIR }}')]
    if actual != expected or '/consumer/' in '\n'.join(actual):
        raise ValueError('Private installation cannot be published')
    if 'scripts/install-managed-mcp.py --artifact' not in job or '--source-commit "$SOURCE_COMMIT"' not in job:
        raise ValueError('Managed consumer required')
    job_environment(source)
    return job


class ManagedWorkflow(unittest.TestCase):
    def source(self):
        return (ROOT / '.github/workflows/artifact-sbom.yml').read_text()

    def test_actual_protected_job_and_explicit_companion_allowlist(self):
        managed_job(self.source())

    def test_branch_escape_and_missing_controls_refuse(self):
        source = self.source()
        for bad in (source.replace(MAIN_ONLY, MAIN_ONLY.replace('refs/heads/main', 'refs/heads/other')),
                    source.replace('    needs: [artifact-controls, managed-mcp-controls]', '    needs: artifact-controls'),
                    source.replace('  attest-managed-mcp:', '  attest-managed-mcp:\n  attest-managed-mcp:')):
            with self.assertRaises(ValueError): managed_job(bad)

    def test_private_workspace_upload_and_runner_job_context_refuse(self):
        source = self.source()
        for bad in (source.replace('/publish/managed-verified.json\n', '/consumer/connection.json\n'),
                    source.replace('    env:\n', '    env:\n      BAD: ${{ runner.temp }}\n', 1)):
            with self.assertRaises(ValueError): managed_job(bad)


if __name__ == '__main__':
    unittest.main()
