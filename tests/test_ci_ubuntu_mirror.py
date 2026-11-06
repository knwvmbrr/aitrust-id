"""Keep package trust/suites unchanged and refuse unexpected CI/host contexts."""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('ci_ubuntu_mirror',ROOT/'scripts/ci-ubuntu-mirror.py')
mirror=importlib.util.module_from_spec(spec);spec.loader.exec_module(mirror)
SOURCE=b'Types: deb\nURIs: http://azure.archive.ubuntu.com/ubuntu/\nSuites: noble noble-updates noble-backports\nComponents: main universe restricted multiverse\nSigned-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg\n\nTypes: deb\nURIs: http://security.ubuntu.com/ubuntu/\nSuites: noble-security\nComponents: main universe restricted multiverse\nSigned-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg\n'
class Mirror(unittest.TestCase):
 def test_only_archive_uri_changes_and_repeated_transform_is_identical(self):
  raw,changed=mirror.transform(SOURCE);self.assertTrue(changed)
  self.assertEqual(raw,SOURCE.replace(b'http://azure.archive.ubuntu.com/ubuntu/',b'https://archive.ubuntu.com/ubuntu'))
  again,changed=mirror.transform(raw);self.assertEqual(again,raw);self.assertFalse(changed)
 def test_exact_github_mirror_file_uses_signed_canonical_archive(self):
  raw,changed=mirror.transform(SOURCE.replace(b'http://azure.archive.ubuntu.com/ubuntu/',b'mirror+file:/etc/apt/apt-mirrors.txt'))
  self.assertTrue(changed)
  self.assertEqual(raw,mirror.transform(SOURCE)[0])
  for uri in (b'mirror+file:/tmp/apt-mirrors.txt',b'mirror+file:/etc/apt/apt-mirrors.txt?x=1'):
   with self.assertRaises(ValueError):mirror.transform(SOURCE.replace(b'http://azure.archive.ubuntu.com/ubuntu/',uri))
 def test_untrusted_or_changed_policy_refused(self):
  values=[SOURCE.replace(b'azure.archive.ubuntu.com',b'evil.invalid'),SOURCE.replace(b'http://azure.archive.ubuntu.com',b'http://user@azure.archive.ubuntu.com'),SOURCE.replace(b'/ubuntu/',b'/ubuntu/?query=1'),SOURCE.replace(b'ubuntu-archive-keyring.gpg',b'other.gpg'),SOURCE.replace(b'noble ',b'other '),SOURCE.replace(b'Types: deb',b'Types: binary'),SOURCE+b'\nTrusted: yes\n',SOURCE.replace(b'URIs:',b'URIs: http://archive.ubuntu.com/ubuntu\nURIs:',1),SOURCE.replace(b'Signed-By:',b' Signed-By:',1),b' ',b'x'*65537]
  for raw in values:
   with self.subTest(raw=raw),self.assertRaises(ValueError):mirror.transform(raw)
 def test_explicit_runner_release_context(self):
  env={'GITHUB_ACTIONS':'true','AITRUST_CI_RUNNER_ENV':'github-hosted','AITRUST_CI_RUNNER_OS':'Linux'}
  mirror.context(env,'ID=ubuntu\nVERSION_ID="24.04"')
  for key in env:
   bad=dict(env);del bad[key]
   with self.assertRaises(ValueError):mirror.context(bad,'ID=ubuntu\nVERSION_ID="24.04"')
  for release in ('ID=debian\nVERSION_ID="24.04"','ID=ubuntu\nVERSION_ID="26.04"','ID=ubuntu\nID=other\nVERSION_ID="24.04"'):
   with self.assertRaises(ValueError):mirror.context(env,release)
 def test_ordinary_local_invocation_refused_without_output(self):
  with tempfile.TemporaryDirectory() as name:
   target=Path(name)/'aitrust-ubuntu.sources'
   result=subprocess.run([sys.executable,str(ROOT/'scripts/ci-ubuntu-mirror.py'),'--output',str(target)],env={'PATH':os.environ.get('PATH','')},capture_output=True,timeout=5)
   self.assertEqual(result.returncode,2);self.assertFalse(target.exists())
 def test_only_browser_jobs_install_prepared_source_without_trust_override(self):
  import yaml
  workflow=yaml.safe_load((ROOT/'.github/workflows/ci.yml').read_text())
  for job in ('site','accessibility'):
   row=workflow['jobs'][job];self.assertEqual(row['runs-on'],'ubuntu-24.04')
   step=next(s for s in row['steps'] if 'ci-ubuntu-mirror.py' in s.get('run',''))
   self.assertEqual(step['env']['AITRUST_CI_RUNNER_ENV'],'${{ runner.environment }}')
   self.assertEqual(row['timeout-minutes'],30)
   self.assertIn('mktemp -d',step['run'])
   self.assertIn('sudo install -o root -g root -m 0644',step['run']);self.assertNotIn('trusted=yes',step['run'])
   install=next(i for i,s in enumerate(row['steps']) if 'npx playwright install --with-deps' in s.get('run',''))
   self.assertLess(row['steps'].index(step),install)
   self.assertEqual(row['steps'][install]['timeout-minutes'],15)
if __name__=='__main__':unittest.main()
