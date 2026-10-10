"""Run a selected local redactor image offline, then require tampered startup to fail."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parents[1]


def verify(engine, image):
    if engine not in ('podman', 'docker') or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9/_.:@-]{0,255}', image):
        raise ValueError('Choose a valid local image and supported engine.')
    base = [engine, 'run', '--rm', '--pull=never', '--network', 'none', '--read-only',
            '--cap-drop', 'all', '--security-opt', 'no-new-privileges',
            '--pids-limit', '128', '--memory', '1024m', '--user', '10001:10001',
            '--entrypoint', 'python']
    def run(program, extra=()):
        return subprocess.run(base+list(extra)+[image, '-c', program],
                              capture_output=True, text=True, timeout=45)
    hashes = {}
    for name in ('app.py', 'healthcheck.py', 'model_identity.py'):
        result = run('import hashlib; print(hashlib.sha256(open('+repr(name)+',"rb").read()).hexdigest())')
        expected = hashlib.sha256((ROOT/'services/anonymizer'/name).read_bytes()).hexdigest()
        if result.returncode or result.stdout.strip() != expected:
            raise ValueError('Image source differs from this checkout.')
        hashes[name] = expected
    positive = run('import app,json,os; d=dict(r.split(":",1) for r in open("/proc/self/status") if ":" in r); print(json.dumps({"health":app.healthz(),"uid":os.getuid(),"capabilities":{k:int(d[k].strip(),16) for k in ("CapEff","CapPrm","CapBnd")}}))')
    if positive.returncode:
        raise ValueError('Positive model startup failed.')
    record = json.loads(positive.stdout)
    identity = record['health']['model_identity']
    if (record['health']['ok'] is not True or identity['verified_before_load'] is not True
            or record['uid'] != 10001 or any(record['capabilities'].values())):
        raise ValueError('Model startup did not verify identity.')
    target = run('import model_identity; print(next(model_identity.installed_root().rglob("config.cfg")))')
    path = target.stdout.strip()
    if target.returncode or not path.startswith('/usr/local/lib/python3.12/site-packages/en_core_web_sm/') or not path.endswith('/config.cfg'):
        raise ValueError('Expected installed model configuration was not found.')
    with tempfile.TemporaryDirectory(prefix='aitrust-staging-model-') as directory:
        folder = Path(directory); folder.chmod(0o755)
        source = folder/'config.cfg'; source.write_text('changed model asset\n'); source.chmod(0o444)
        negative = run('import app', ('-v',str(source)+':'+path+':ro'))
    if negative.returncode == 0 or 'English model assets failed integrity verification.' not in negative.stderr:
        raise ValueError('Tampered model startup was not refused by the integrity guard.')
    inspected = subprocess.run([engine, 'image', 'inspect', '--format', '{{.Id}}', image],
                               capture_output=True, text=True, timeout=15, check=True)
    return {'captured_at':datetime.now(timezone.utc).isoformat(), 'pass':True,
            'image_id':inspected.stdout.strip(), 'runtime_file_sha256':hashes,
            'positive_app_startup':True, 'tampered_real_model_config_startup_refused':True,
            'negative_exit':negative.returncode, 'isolated_network_none':True,
            'runtime_uid':record['uid'], 'runtime_capabilities':record['capabilities'],
            'isolation_options_requested':['read-only','network none','no-new-privileges','pids 128','memory 1024 MiB'],
            'model_identity':identity, 'engine':engine,
            'independent_accuracy_evidence':False, 'engine_auto_started':False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--engine', choices=('podman','docker'), required=True)
    parser.add_argument('--image', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        report = verify(args.engine, args.image)
        args.output.write_text(json.dumps(report, indent=2)+'\n')
        print('Offline image startup and tampered-model rejection passed.')
    except (ValueError, KeyError, OSError, subprocess.SubprocessError):
        print('Model image verification failed; no acceptance recorded.')
        raise SystemExit(1)
