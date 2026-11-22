"""Narrow source guard for the reviewed controlled workflow, not a general YAML parser."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]

def job_environment(source):
    lines=source.splitlines();blocks=[]
    for i,line in enumerate(lines):
        if line.startswith('    env:'):
            if line!='    env:':raise ValueError('Unsupported controlled job env form')
            block=[]
            for child in lines[i+1:]:
                if child and not child.startswith('      '):break
                if child.strip():block.append(child.strip())
            blocks.append(block)
    if blocks!=[['SOURCE_COMMIT: ${{ github.sha }}']]:raise ValueError('Unsupported job context')
    if 'ARTIFACT_DIR="$RUNNER_TEMP/aitrust-source-artifact-sbom"'not in source or '>> "$GITHUB_ENV"'not in source:
        raise ValueError('Runner-local artifact path not exported')

class ArtifactWorkflowSource(unittest.TestCase):
    def test_actual_job_env_has_only_pre_runner_context(self):
        job_environment((ROOT/'.github/workflows/artifact-sbom.yml').read_text())
    def test_original_runner_at_job_env_counterexample_refuses(self):
        raw=(ROOT/'.github/workflows/artifact-sbom.yml').read_text();bad=raw.replace('    env:\n','    env:\n      ARTIFACT_DIR: ${{ runner.temp }}/forbidden\n',1)
        with self.assertRaises(ValueError):job_environment(bad)

if __name__=='__main__':unittest.main()
