"""Source-only qualification authority controls; never launches a workflow or model."""
import ast,hashlib,json,os,re,subprocess,textwrap,unittest
from pathlib import Path
from unittest import mock
ROOT=Path(__file__).resolve().parents[1]
WORKFLOW=ROOT/'.github/workflows/visual-score-qualification.yml'
ORIGINAL_SHA='75883b9feda6f324ebf98f91559335a48b55e79b10503a39df0aad0079906125'
ORIGINAL_ON="  workflow_dispatch:\n  push:\n    branches: [codex/offline-image-score]\n    paths:\n      - 'tools/visual_score*.py'\n      - 'scripts/inspect-visual-score.py'\n      - 'scripts/*visual-score-qualification.py'\n      - 'tests/test_visual_score*.py'\n      - 'integrations/visual-score-reference/**'\n      - 'integrations/image-metadata-reference/1.0.0/**'\n      - 'docs/offline-image-score*.md'\n      - '.github/workflows/visual-score-qualification.yml'\n"
IDENTITY_SHA='d258fe6f86d00508efdf5eef281f6e9549e83316c3ac214da37897d81c142d18'
BRANCH='refs/heads/codex/nov23-image-native-qualification'
EXPECTED='a'*40


def identity_source(text):
 start=text.index('      - name: Refuse unreviewed dispatch identity before qualification setup\n')
 end=text.index('      - uses: actions/setup-python@',start)
 block=text[start:end]
 code=textwrap.dedent(block.split("          python3 -I -S -B - <<'PY_IDENTITY'\n",1)[1].split('          PY_IDENTITY\n',1)[0])
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
  self.assertEqual(self.code.count(BRANCH),1)
  historical=self.code.replace(BRANCH,'refs/heads/codex/nov23-image-source-integration',1)
  self.assertEqual(hashlib.sha256(historical.encode()).hexdigest(),'0f78874276985bd8358577abd7341e4bdc7b2e1885425c38049af3d688bef3a4')
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
 def test_historical_bytes_not_rebound_and_current_caps_tighten(self):
  # Original execution proof keeps its original digest; this is an operator revision.
  self.assertNotEqual(hashlib.sha256(self.text.encode()).hexdigest(),ORIGINAL_SHA)
  self.assertIn('    timeout-minutes: 35\n',self.text)
  self.assertIn('retention-days: 7',self.text)
  self.assertIn('Always attempt owned cleanup using original budget and system stdlib\n        if: always()',self.text)
  self.assertIn('Always retain missing failure observations without adopting a stage\n        if: always()',self.text)
  self.assertIn('/usr/bin/python3 -I -S -B scripts/run-visual-score-phase.py run --phase cleanup',self.text)
  for phase in ['source','acquire','seal','forward','cleanup']:
   self.assertIn('--phase '+phase,self.text)
  self.assertIn('for phase in install fixtures',self.text)
  self.assertIn('--clear-groups --no-new-privs --bounding-set=-all --inh-caps=-all --ambient-caps=-all env -i',self.text)
  self.assertEqual(self.text.count('run-visual-score-phase.py start'),1)
  self.assertEqual(self.text.count('timeout-minutes: 1'),1)
  self.assertNotIn('id-token:',self.text);self.assertNotIn('secrets.',self.text)
  self.assertEqual(self.text.count('/qualification.json'),1)
  self.assertEqual(self.text.count('/cleanup.json'),1)
 def test_registered_source_checks_use_existing_runner_no_acquisition(self):
  manifest=json.loads((ROOT/'eval/revalidation.json').read_text())
  commands=[['{python}','-m','pytest','tests/'+p,'-q'] for p in ['test_visual_score.py','test_visual_score_qualification.py','test_visual_score_workflow.py','test_visual_score_budget.py']]+[['{python}','scripts/prepare-visual-score-qualification.py','check-lock']]
  protocol=manifest['capabilities']['protocol']
  for command in commands:self.assertEqual(protocol['commands'].count(command),1)
  start=protocol['commands'].index(commands[0]);self.assertEqual(protocol['commands'][start:start+len(commands)],commands)
  ci=(ROOT/'.github/workflows/ci.yml').read_text()
  step=ci.split('      - name: Verify image reference source without models or optional SDKs\n',1)[1].split('      - run:',1)[0]
  self.assertEqual(step.splitlines(),['        run: |','          python -m pytest tests/test_visual_score.py -q','          python -m pytest tests/test_visual_score_qualification.py -q','          python -m pytest tests/test_visual_score_workflow.py -q','          python -m pytest tests/test_visual_score_budget.py -q','          python scripts/prepare-visual-score-qualification.py check-lock'])
  self.assertNotIn('acquire',step);self.assertNotIn('pip install',step)

if __name__=='__main__':unittest.main()
