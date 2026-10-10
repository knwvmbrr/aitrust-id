"""Review-bound current personal routes; not a universal security or release proof."""
import argparse
import ast
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from protocol.reports import write_report
from protocol.revalidation import assess
from protocol.evidence import read_evidence

PATTERNS = ('services/**/*', 'protocol/*', 'extension/**/*', 'site/src/**/*',
            'site/scripts/*', 'site/functions/**/*', 'site/public/*',
            'site/public/device/*', 'site/index.html', '.github/workflows/*',
            'deploy/docker-compose.yml', 'package.json', 'site/package.json',
            'scripts/verify-route-boundaries.py', 'scripts/verify-route-boundaries.cjs')
PATTERNS += ('tools/composition/*', 'scripts/receipt.cjs',
             'scripts/build-composition-tool.py', 'scripts/check-repetition.py')
RULES = ('X-01', 'X-03', 'X-04', 'X-06', 'X-08', 'X-12', 'X-15', 'N-007', 'N-008')
DEVICE_SOURCES = ['site/src/device-client.js', 'site/src/device-worker.js',
                  'site/src/ps-result.js', 'site/src/handheld.jsx',
                  'site/src/share-record.js', 'protocol/normalization.mjs',
                  'protocol/normalization-core.js', 'protocol/unicode15-data.json',
                  'services/evaluator/app.py']


def read_json(file):
    return read_evidence(file)


def device_evidence(binding, root=ROOT):
    commit = binding.get('source_commit', '')
    relative = binding.get('receipt', '')
    files = binding.get('sources', [])
    if (not re.fullmatch('[a-f0-9]{40}', commit) or not re.fullmatch(r'runs/[a-z0-9-]+\.json', relative)
            or files != DEVICE_SOURCES):
        raise ValueError('Invalid committed device evidence binding')
    def blob(name):
        result = subprocess.run(['git', 'show', commit + ':' + name], cwd=root,
                                capture_output=True, timeout=15, check=False)
        if result.returncode or len(result.stdout) > 2_000_000:
            raise ValueError('Committed source evidence unavailable')
        return result.stdout
    # Exact recorded evidence and the actual checked browser-method inputs must
    # be recoverable from the named commit. No remote Git fetch is attempted.
    for name in [relative, *files]:
        if blob(name) != (root / name).read_bytes():
            raise ValueError('Device execution or source changed')
    report = read_json(root / relative)
    build = read_json(root / 'site/src/device-manifest.json')
    expected_sha = hashlib.sha256((root / 'services/evaluator/app.py').read_bytes()).hexdigest()
    if (report.get('pass') is not True or report.get('method_sha256') != expected_sha
            or build.get('method_sha256') != expected_sha
            or build.get('bundle_sha256') != report.get('bundle_sha256')
            or build.get('normalization_data_sha256') != report.get('normalization_data_sha256')
            or report.get('physical_device_tested') is not False or report.get('independent_accuracy') is not False
            or not report.get('engines')):
        raise ValueError('Missing bounded device evidence')
    bundle = root / 'site/public/device' / ('method-' + report['bundle_sha256'] + '.py')
    if hashlib.sha256(bundle.read_bytes()).hexdigest() != report['bundle_sha256']:
        raise ValueError('Checked device bundle changed')
    for engine in report['engines']:
        for field in ['no_text_in_requests_or_cache', 'no_canary_in_browser_console',
                      'no_session_content_storage', 'minimal_summary_export',
                      'detailed_export_requires_opt_in', 'detail_consent_reset_for_new_input']:
            if engine.get(field) is not True:
                raise ValueError('Device privacy execution failed')
    return len(report['engines'])


def inventory(root):
    found = {}
    for pattern in PATTERNS:
        for file in root.glob(pattern):
            if '__pycache__' in file.parts:
                continue
            if file.is_symlink() or any(parent.is_symlink() for parent in file.parents if parent != root):
                raise ValueError('Boundary source symlink refused')
            if file.is_file():
                found[file.relative_to(root).as_posix()] = hashlib.sha256(file.read_bytes()).hexdigest()
    if not found:
        raise ValueError('Missing boundary sources')
    return dict(sorted(found.items()))


def routes(root, relative):
    tree = ast.parse((root / relative).read_text())
    result = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for deco in node.decorator_list:
                if (isinstance(deco, ast.Call) and isinstance(deco.func, ast.Attribute)
                        and isinstance(deco.func.value, ast.Name) and deco.func.value.id == 'app'
                        and deco.func.attr in ('get', 'post', 'put', 'delete', 'patch', 'websocket')):
                    if not deco.args or not isinstance(deco.args[0], ast.Constant):
                        raise ValueError('Dynamic endpoint requires review')
                    result.append([deco.func.attr, deco.args[0].value])
    return sorted(result)


def compose_boundary(value):
    services = value['services']
    active = {name for name, row in services.items() if not row.get('profiles')}
    if active != {'gateway', 'anonymizer', 'evaluator'}:
        raise ValueError('Unreviewed active service or collection container')
    gateway = services['gateway']
    if (gateway.get('ports') != ['127.0.0.1:8787:8000'] or gateway.get('volumes')
            or set(gateway.get('environment', {})) != {'AITRUST_TOKEN', 'ANONYMIZER_URL', 'EVALUATOR_URL'}
            or value['networks']['inspection'].get('internal') is not True):
        raise ValueError('Collection, persistence or service access boundary changed')
    for name in ['anonymizer', 'evaluator']:
        if (services[name].get('ports') or services[name].get('volumes')
                or services[name].get('networks') != ['inspection']):
            raise ValueError('Private processor access boundary changed')
    return sorted(active)


def service_evidence(relative, root=ROOT):
    if not isinstance(relative, str) or not re.fullmatch(r'runs/[a-z0-9-]+\.json', relative):
        raise ValueError('Invalid service evidence path')
    report = read_json(root / relative)
    if (report.get('pass') is not True or set(report.get('services', {})) != {'gateway', 'anonymizer', 'evaluator'}
            or report.get('synthetic_markers_absent_from_application_logs') is not True
            or report.get('no_store_headers_checked_on_all_gateway_cases') is not True):
        raise ValueError('Missing service boundary execution')
    for name, row in report['services'].items():
        if (row['source_sha256'] != hashlib.sha256((root / 'services' / name / 'app.py').read_bytes()).hexdigest()
                or row['uid'] != 10001 or row['read_only'] is not True
                or row['published_port_scope'] != ('127.0.0.1:8787' if name == 'gateway' else 'none')):
            raise ValueError('Service source or observed access changed')
    cases = {case['name']: case for case in report['cases']}
    for name in ['unsupported_code', 'unsupported_image', 'unsupported_audio', 'unsupported_video', 'unsupported_document']:
        if name not in cases or cases[name]['status'] != 422 or cases[name]['pass'] is not True:
            raise ValueError('Reserved modality was not refused')
    return len(report['cases'])


def evaluate(manifest, root=ROOT):
    fields = {'schema_version', 'wire_version', 'reviewed_at', 'reviewed_by', 'rules',
              'independent_release_approval', 'sources', 'engineering_receipts',
              'device_evidence', 'service_evidence'}
    if (set(manifest) != fields or manifest.get('schema_version') != 1 or manifest.get('wire_version') != '0.1.0'
            or manifest.get('rules') != list(RULES)
            or manifest.get('independent_release_approval') is not False):
        raise ValueError('Unsupported boundary review')
    try:
        moment = datetime.fromisoformat(manifest['reviewed_at'])
        if moment.tzinfo is None or moment > datetime.now(timezone.utc) or not manifest['reviewed_by']:
            raise ValueError('Invalid dated boundary review')
    except (KeyError, TypeError, ValueError):
        raise ValueError('Invalid dated boundary review') from None
    if manifest.get('sources') != inventory(root):
        raise ValueError('Current route differs from reviewed source inventory')
    expected = {
        'services/gateway/app.py': [['get', '/healthz'], ['post', '/v1/evaluate']],
        'services/evaluator/app.py': [['get', '/healthz'], ['post', '/signals']],
        'services/anonymizer/app.py': [['get', '/healthz'], ['post', '/redact']],
    }
    observed = {name: routes(root, name) for name in expected}
    if observed != expected:
        raise ValueError('Application endpoint surface changed')
    active = compose_boundary(yaml.safe_load((root / 'deploy/docker-compose.yml').read_text()))
    extension = read_json(root / 'extension/manifest.json')
    if (extension.get('permissions') != ['storage'] or extension.get('optional_permissions')
            or extension.get('host_permissions') != ['http://127.0.0.1:8787/*']
            or extension.get('optional_host_permissions')
            or len(extension.get('content_scripts', [])) != 1
            or extension['content_scripts'][0]['matches'] != ['https://chatgpt.com/*']):
        raise ValueError('Extension access requires new boundary review')
    receipts = manifest.get('engineering_receipts', {})
    if set(receipts) != {'extension', 'website'}:
        raise ValueError('Missing selected browser evidence')
    for capability, relative in receipts.items():
        file = root / relative
        if relative.startswith('/') or '..' in Path(relative).parts:
            raise ValueError('Unsafe receipt path')
        if not assess(read_json(file), capability, root)['pass']:
            raise ValueError('Missing or stale browser execution')
    engines = device_evidence(manifest.get('device_evidence', {}), root)
    service_cases = service_evidence(manifest.get('service_evidence'), root)
    return {'routes': observed, 'source_files': len(manifest['sources']),
            'browser_receipts_current': True, 'extension_access_unchanged': True,
            'committed_device_engine_evidence': engines, 'active_services': active,
            'current_remote_service_cases': service_cases}


def intake_controls(root=ROOT):
    # No live credential, network client or evaluation is used here. Execute the
    # real input model: a local check needs only text, never an identity/receipt.
    previous = os.environ.get('AITRUST_TOKEN')
    os.environ['AITRUST_TOKEN'] = 'synthetic-boundary-control-not-a-live-token'
    try:
        spec = importlib.util.spec_from_file_location('boundary_gateway', root / 'services/gateway/app.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        if previous is None:
            os.environ.pop('AITRUST_TOKEN', None)
        else:
            os.environ['AITRUST_TOKEN'] = previous
    request = module.EvalRequest.model_validate({'text': 'An ordinary answer.'})
    if request.model_dump() != {'text': 'An ordinary answer.', 'origin_host': 'unknown', 'modality': 'text'}:
        raise ValueError('Personal check acquired an extra prerequisite')
    controls = ['payment', 'subscription', 'receipt', 'author_id', 'keystroke_template',
                'biometric_profile', 'telemetry', 'training_consent', 'pilot_upload',
                'report_attachment', 'promotion_destination']
    for field in controls:
        try:
            module.EvalRequest.model_validate({'text': 'An ordinary answer.', field: 'synthetic-control'})
        except module.ValidationError:
            continue
        raise ValueError('Undeclared intake field accepted')
    if module.PRODUCTION_TAGS != frozenset({'PS', 'PII_REDACTED'}):
        raise ValueError('Production capabilities changed')
    return {'ordinary_text_without_account_payment_receipt': True,
            'undeclared_intake_fields_refused': len(controls), 'network_executed': False}


def verify(root=ROOT):
    before = inventory(root)
    manifest = read_json(root / 'eval/route-boundaries.json')
    observed = evaluate(manifest, root)
    intake = intake_controls(root)
    if inventory(root) != before:
        raise ValueError('Boundary sources changed during verification')
    return {'captured_at': datetime.now(timezone.utc).isoformat(), 'pass': True,
            'rules': list(RULES), **observed, **intake,
            'review_manifest_sha256': hashlib.sha256((root / 'eval/route-boundaries.json').read_bytes()).hexdigest(),
            'independent_accuracy_evidence': False, 'release_approved': False,
            'scope': 'Reviewed current personal source/access/endpoint boundaries and source-bound browser checks. '
                     'Not a proof against host compromise, third-party collection, future changes or new organizational/research routes. '
                     'Optional registry proposals and license clearance are outside this guard.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'output/verification/route-boundaries.json')
    args = parser.parse_args()
    try:
        report = verify()
        write_report(args.output, report)
        print(json.dumps(report))
    except (ValueError, KeyError, TypeError, OSError, SyntaxError) as error:
        print('Boundary verification failed: ' + str(error), file=sys.stderr)
        raise SystemExit(1)
