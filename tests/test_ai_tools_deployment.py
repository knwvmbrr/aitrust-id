"""Finite source/config preparation controls; not an effective systemd sandbox proof."""
import importlib.util
import io
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
def load(name):
    s=importlib.util.spec_from_file_location(name,ROOT/'deploy/ai-tools'/f'{name}.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
render=load('render');prepare=load('prepare')
class Deployment(unittest.TestCase):
    def test_closed_host_routes_tls_and_private_logging(self):
        s=render.caddyfile();self.assertIn('https://vps-18ef1326.vps.ovh.us',s);self.assertIn('admin off',s);self.assertIn('output discard',s);self.assertNotIn('\n    log\n',s);self.assertIn('disable_http_challenge',s);self.assertIn('auto_https disable_redirects',s);self.assertIn('path /healthz /v1/tags',s);self.assertIn('path /mcp /v1/check',s);self.assertNotIn('api.aitrustid.com',s)
    def test_proxy_limits_credentials_and_transport(self):
        s=render.caddyfile(19111,19112)
        for token in ['http://127.0.0.1:19111','127.0.0.1:19112','max_size 256000','max_header_size 8192','read_body 12s','write 15s','max_conns_per_host 16','header_up -Cookie','header_up -Authorization','header_up -X-Forwarded-For','compression off','Cache-Control "no-store"']:self.assertIn(token,s)
        self.assertNotIn('issuer acme',s)
    def test_config_bounds(self):
        for value in [True,0,80,65536,'8791']:
            with self.assertRaises(ValueError):render.caddyfile(value)
        with self.assertRaises(ValueError):render.caddyfile(8790)
    def test_app_readonly_nologin_swap_and_egress_policy(self):
        s=render.units('a'*40)['aitrustid-ai-tools.service']
        for token in ['DynamicUser=yes','ProtectHome=yes','ProtectSystem=strict','MemorySwapMax=0','MemoryMax=384M','CPUQuota=100%','TasksMax=64','OOMPolicy=kill','KillMode=control-group','IPAddressDeny=any','IPAddressAllow=localhost','CapabilityBoundingSet=','LimitCORE=0','StandardOutput=null','StandardError=null']:self.assertIn(token,s)
        self.assertNotIn('StateDirectory=',s)
    def test_proxy_is_separate_and_no_binds_to_other_units(self):
        u=render.units('b'*40);s=u['aitrustid-ai-tools-proxy.service'];self.assertIn('MemoryMax=192M',s);self.assertIn('StateDirectory=aitrustid-ai-tools-proxy',s);self.assertIn('CAP_NET_BIND_SERVICE',s);self.assertNotIn('BindsTo=',s);self.assertNotIn('PartOf=',s)
        for bad in ['main','a'*39,'A'*40,'a'*40+'\n']:
            with self.assertRaises(ValueError):render.units(bad)
    def test_exclusive_destination_refusal_before_git(self):
        with tempfile.TemporaryDirectory() as d:
            dest=Path(d)/('c'*40);dest.mkdir();(dest/'owned').write_text('keep')
            with patch.object(subprocess,'run',side_effect=AssertionError('not reached')):
                with self.assertRaises(ValueError):prepare.prepare(ROOT,'c'*40,dest)
            self.assertEqual((dest/'owned').read_text(),'keep')
    def test_source_symlink_refused_before_any_output(self):
        raw=io.BytesIO()
        with tarfile.open(fileobj=raw,mode='w') as t:
            m=tarfile.TarInfo('LICENSE');m.type=tarfile.SYMTYPE;m.linkname='/private';t.addfile(m)
        def fake(*args,**kwargs):
            kwargs['stdout'].write(raw.getvalue());return subprocess.CompletedProcess([],0)
        with tempfile.TemporaryDirectory() as d,patch.object(subprocess,'run',side_effect=fake):
            dest=Path(d)/('c'*40)
            with self.assertRaises(ValueError):prepare.prepare(ROOT,'c'*40,dest)
            self.assertFalse(dest.exists())
    def test_actual_tracked_source_prepare_no_activation_or_install(self):
        commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip()
        with tempfile.TemporaryDirectory() as d:
            dest=Path(d).resolve()/commit;report=prepare.prepare(ROOT,commit,dest)
            self.assertFalse(report['activated']);self.assertFalse(report['venv_provisioned']);self.assertEqual(set(report['source_sha256']),set(prepare.FILES));self.assertEqual((dest/'source/tools/remote_tag_server.py').read_bytes(),subprocess.check_output(['git','show',commit+':tools/remote_tag_server.py'],cwd=ROOT));self.assertEqual(dest.stat().st_mode&0o777,0o700)
if __name__=='__main__':unittest.main()
