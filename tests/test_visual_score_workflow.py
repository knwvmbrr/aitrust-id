"""Source-only qualification authority controls; never launches a workflow or model."""
import ast,hashlib,json,os,re,subprocess,textwrap,unittest
from pathlib import Path
from unittest import mock
ROOT=Path(__file__).resolve().parents[1]
WORKFLOW=ROOT/'.github/workflows/visual-score-qualification.yml'
ORIGINAL_SHA='75883b9feda6f324ebf98f91559335a48b55e79b10503a39df0aad0079906125'
ORIGINAL_ON="  workflow_dispatch:\n  push:\n    branches: [codex/offline-image-score]\n    paths:\n      - 'tools/visual_score*.py'\n      - 'scripts/inspect-visual-score.py'\n      - 'scripts/*visual-score-qualification.py'\n      - 'tests/test_visual_score*.py'\n      - 'integrations/visual-score-reference/**'\n      - 'integrations/image-metadata-reference/1.0.0/**'\n      - 'docs/offline-image-score*.md'\n      - '.github/workflows/visual-score-qualification.yml'\n"
IDENTITY_SHA='0f78874276985bd8358577abd7341e4bdc7b2e1885425c38049af3d688bef3a4'
BRANCH='refs/heads/codex/nov23-image-source-integration'
EXPECTED='a'*40


def identity_source(text):
 start=text.index('      - name: Refuse unreviewed dispatch identity before qualification setup\n')
 end=text.index('      - uses: actions/setup-python@',start)
 block=text[start:end]
 code=textwrap.dedent(block.split("          python3 -I -S -B - <<'PY_IDENTITY'\n",1)[1].rsplit('          PY_IDENTITY\n',1)[0])
 return block,code


def env():
 return {'EXPECTED_COMMIT':EXPECTED,'GITHUB_SHA':EXPECTED,'GITHUB_EVENT_NAME':'workflow_dispatch','GITHUB_REPOSITORY':'knwvmbrr/aitrust-id','GITHUB_REF':BRANCH}


class WorkflowTests(unittest.TestCase):
 def setUp(self):self.text=WORKFLOW.read_text();self.block,self.code=identity_source(self.text)
 def test_manual_only_closed_job_authority_and_env_input(self):
  triggers=self.text.split('on:\n',1)[1].split('permissions:\n',1)[0]
  self.assertEqual(re.findall(r'^  ([a-z_]+):',triggers,re.M),['workflow_dispatch'])
  self.assertEqual(re.findall(r'^      ([a-z_]+):',triggers,re.M),['expected_commit'])
  self.assertIn('        required: true\n        type: string\n',triggers)
  self.assertEqual(self.text.split('permissions:\n',1)[1].split('jobs:\n',1)[0],'  contents: read\n')
  line=next(x.strip() for x in self.text.splitlines() if x.strip().startswith('if: github.'))
  self.assertEqual(line,"if: github.event_name == 'workflow_dispatch' && github.repository == 'knwvmbrr/aitrust-id' && github.ref == '"+BRANCH+"' && inputs.expected_commit == github.sha")
  self.assertIn('          EXPECTED_COMMIT: ${{ inputs.expected_commit }}\n',self.block)
  self.assertNotIn('${{',self.code)
  self.assertEqual(hashlib.sha256(self.code.encode()).hexdigest(),IDENTITY_SHA)
  self.assertLess(self.text.index(self.block),self.text.index('      - uses: actions/setup-python@'))
  ast.parse(self.code)
 def test_actual_identity_guard_exact_and_wrong_authorities(self):
  with mock.patch.dict(os.environ,env(),clear=True),mock.patch.object(subprocess,'check_output',return_value=EXPECTED+'\n') as call:
   exec(compile(self.code,'fixed-dispatch-guard','exec'),{})
   call.assert_called_once_with(['git','rev-parse','HEAD'],text=True,stderr=subprocess.DEVNULL,timeout=5)
  cases=[{'EXPECTED_COMMIT':''},{'EXPECTED_COMMIT':'PRIVATE_NOT_A_COMMIT'},{'EXPECTED_COMMIT':'A'*40},{'EXPECTED_COMMIT':'a'*41},{'EXPECTED_COMMIT':'b'*40},{'GITHUB_SHA':'b'*40},{'GITHUB_EVENT_NAME':'push'},{'GITHUB_EVENT_NAME':'pull_request'},{'GITHUB_REPOSITORY':'other/repository'},{'GITHUB_REF':'refs/heads/main'},{'GITHUB_REF':'refs/pull/1/merge'}]
  for change in cases:
   with self.subTest(field=next(iter(change))),mock.patch.dict(os.environ,env()|change,clear=True),mock.patch.object(subprocess,'check_output') as call:
    with self.assertRaises(SystemExit) as error:exec(compile(self.code,'fixed-dispatch-guard','exec'),{})
    self.assertEqual(str(error.exception),'Qualification identity refused.');call.assert_not_called()
 def test_checked_out_identity_failure_has_fixed_refusal(self):
  for response in ['b'*40+'\n',subprocess.CalledProcessError(128,['git']),subprocess.TimeoutExpired(['git'],5),OSError('PRIVATE_PATH_CANARY')]:
   with self.subTest(kind=type(response).__name__),mock.patch.dict(os.environ,env(),clear=True),mock.patch.object(subprocess,'check_output',**({'side_effect':response} if isinstance(response,Exception) else {'return_value':response})):
    with self.assertRaises(SystemExit) as error:exec(compile(self.code,'fixed-dispatch-guard','exec'),{})
    self.assertEqual(str(error.exception),'Qualification identity refused.')
 def test_all_acquisition_runtime_resource_and_cleanup_bytes_unchanged(self):
  restored=self.text.replace('on:\n'+self.text.split('on:\n',1)[1].split('permissions:\n',1)[0],'on:\n'+ORIGINAL_ON,1)
  new_line="    if: github.event_name == 'workflow_dispatch' && github.repository == 'knwvmbrr/aitrust-id' && github.ref == '"+BRANCH+"' && inputs.expected_commit == github.sha"
  old_line="    if: github.repository == 'knwvmbrr/aitrust-id' && github.ref == 'refs/heads/codex/offline-image-score'"
  self.assertEqual(restored.count(new_line),1);restored=restored.replace(new_line,old_line,1)
  self.assertEqual(restored.count(self.block),1);restored=restored.replace(self.block,'',1)
  line='          python -I -S -B -m unittest discover -s tests -p test_visual_score_workflow.py\n'
  self.assertEqual(restored.count(line),1);restored=restored.replace(line,'',1)
  restored=restored.replace('test "$GITHUB_REF" = '+BRANCH,'test "$GITHUB_REF" = refs/heads/codex/offline-image-score',1)
  self.assertEqual(hashlib.sha256(restored.encode()).hexdigest(),ORIGINAL_SHA)
 def test_registered_source_checks_use_existing_runner_no_acquisition(self):
  manifest=json.loads((ROOT/'eval/revalidation.json').read_text())
  commands=[['{python}','-m','pytest','tests/'+p,'-q'] for p in ['test_visual_score.py','test_visual_score_qualification.py','test_visual_score_workflow.py']]+[['{python}','scripts/prepare-visual-score-qualification.py','check-lock']]
  protocol=manifest['capabilities']['protocol']
  for command in commands:self.assertEqual(protocol['commands'].count(command),1)
  self.assertEqual(protocol['commands'][-4:],commands)
  ci=(ROOT/'.github/workflows/ci.yml').read_text()
  step=ci.split('      - name: Verify image reference source without models or optional SDKs\n',1)[1].split('      - run:',1)[0]
  self.assertEqual(step.splitlines(),['        run: |','          python -m pytest tests/test_visual_score.py -q','          python -m pytest tests/test_visual_score_qualification.py -q','          python -m pytest tests/test_visual_score_workflow.py -q','          python scripts/prepare-visual-score-qualification.py check-lock'])
  self.assertNotIn('acquire',step);self.assertNotIn('pip install',step)

if __name__=='__main__':unittest.main()
