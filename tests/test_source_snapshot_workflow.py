"""Protect actual source signing and publication boundaries, without executing CI."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
MAIN_ONLY = ("    if: github.repository == 'knwvmbrr/aitrust-id' && github.ref == 'refs/heads/main' "
             "&& (github.event_name == 'push' || github.event_name == 'workflow_dispatch')")
OUTPUTS = ('source.tar.gz', 'evidence.json', 'artifact.spdx.json',
           'sbom.sigstore.json', 'trusted-root.jsonl', 'managed-verified.json')


def source_job(text):
    names = re.findall(r'^  ([a-z][a-z0-9-]*):$', text, re.M)
    if len(names) != len(set(names)) or names.count('attest-managed-source') != 1:
        raise ValueError('Ambiguous source signing job')
    tail = text.split('  attest-managed-source:\n', 1)[1]
    following = re.search(r'^  [a-z][a-z0-9-]*:', tail, re.M)
    job = tail[:following.start()] if following else tail
    if (job.splitlines().count(MAIN_ONLY) != 1 or
            '    needs: [artifact-controls, managed-source-controls]\n' not in job or
            '    permissions:\n      contents: read\n      id-token: write\n      attestations: write\n' not in job or
            'pull_request_target' in text or 'secrets.' in job):
        raise ValueError('Source signing authority changed')
    expected = [f'            ${{{{ env.SOURCE_RELEASE_DIR }}}}/publish/{name}' for name in OUTPUTS]
    actual = [line for line in job.splitlines() if line.startswith('            ${{ env.SOURCE_RELEASE_DIR }}')]
    if actual != expected or 'include-hidden-files:' in job:
        raise ValueError('Private source stage cannot be published')
    operation = next((line for line in job.splitlines()
                      if 'scripts/verify-managed-source.py --artifact' in line), '')
    if ('--source-commit "$SOURCE_COMMIT"' not in operation or
            '--output "$SOURCE_RELEASE_DIR/publish/managed-verified.json"' not in operation or
            '>' in operation):
        raise ValueError('Publish the actual JSON summary, never CLI prose')
    if ('scripts/build-source-snapshot.py --commit "$SOURCE_COMMIT"' not in job or
            'evaluate(\'source-snapshot\')[\'release_allowed\']is True' not in job or
            'subject-path: ${{ env.SOURCE_RELEASE_DIR }}/publish/source.tar.gz' not in job or
            'sbom-path: ${{ env.SOURCE_RELEASE_DIR }}/publish/artifact.spdx.json' not in job):
        raise ValueError('Actual source, permission and exact predicate are required')
    return job


class SourceWorkflow(unittest.TestCase):
    def source(self):
        return (ROOT / '.github/workflows/artifact-sbom.yml').read_text()

    def test_actual_source_job_is_protected_and_uploads_exact_authenticated_summary(self):
        source_job(self.source())
        text = self.source()
        for expected in ("('test_source_snapshot_admission.py',10)",
                         "('test_source_snapshot_managed.py',21)",
                         "('test_source_snapshot_workflow.py',3)",
                         "('test_source_release_policy_v3.py',24)"):
            self.assertIn(expected, text)
        self.assertIn('assert suite.countTestCases()==count', text)
        self.assertIn('assert result.testsRun==58', text)

    def test_branch_missing_controls_extra_authority_and_ambiguous_job_refuse(self):
        text = self.source()
        for changed in (text.replace(MAIN_ONLY, MAIN_ONLY.replace('refs/heads/main', 'refs/heads/other')),
                        text.replace('needs: [artifact-controls, managed-source-controls]', 'needs: artifact-controls'),
                        text.replace('  attest-managed-source:', '  attest-managed-source:\n  attest-managed-source:'),
                        text.replace('      attestations: write\n', '      attestations: write\n      # secrets.FORBIDDEN\n')):
            with self.assertRaises(ValueError):
                source_job(changed)

    def test_private_stage_upload_or_human_stdout_as_json_refuses(self):
        text = self.source()
        for changed in (text.replace('/publish/managed-verified.json\n', '/.source-managed-private/**\n'),
                        text.replace('--output "$SOURCE_RELEASE_DIR/publish/managed-verified.json"',
                                     '--output "$SOURCE_RELEASE_DIR/consumer/verified.json" > "$SOURCE_RELEASE_DIR/publish/managed-verified.json"')):
            with self.assertRaises(ValueError):
                source_job(changed)


if __name__ == '__main__':
    unittest.main()
