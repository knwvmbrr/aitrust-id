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
import runpy
import subprocess
import sys
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from protocol.reports import write_report
from protocol.revalidation import assess
from protocol.evidence import read_evidence
from scripts.dependency_pins import verify_root_inputs

PATTERNS = ('services/**/*', 'protocol/*', 'extension/**/*', 'site/src/**/*',
            'site/scripts/*', 'site/functions/**/*', 'site/public/*',
            'site/public/device/*', 'site/index.html', '.github/workflows/*',
            'deploy/docker-compose.yml', 'package.json', 'site/package.json',
            'scripts/verify-route-boundaries.py', 'scripts/verify-route-boundaries.cjs',
            'scripts/verify-registry-deferral.py', 'tests/test_registry_deferral.py',
            '.dockerignore', 'tests/test_route_boundaries.py', 'scripts/replay-assertion.py', 'scripts/verify-assertion-replay.py',
            'scripts/verify-replay-export.cjs', 'tests/test_assertion_replay.py')
PATTERNS += ('tools/composition/*', 'scripts/receipt.cjs',
             'scripts/build-composition-tool.py', 'scripts/check-repetition.py')
PATTERNS += ('.github/CODEOWNERS', '.github/dependabot.yml',
             'scripts/verify-dependency-automation.py', 'tests/test_dependency_automation.py')
PATTERNS += ('scripts/dependency_pins.py', 'scripts/verify-dependencies.py',
             'tests/test_python_input_pins.py', 'tests/test_dependency_contract.py',
             'eval/requirements.txt', 'eval/requirements.lock')
PATTERNS += ('scripts/spdx_inventory.py', 'scripts/verify-runtime-sbom.py',
             'scripts/verify-runtime-sbom-standard.py', 'tests/test_spdx_inventory.py',
             'spec/vendor/spdx-2.3.1/*', 'eval/dependencies/runtime-sbom.json', 'sbom/runtime/*')
PATTERNS += ('scripts/source_snapshot.py', 'scripts/build-source-snapshot.py',
             'scripts/verify-source-provenance.py', 'tests/test_source_provenance.py')
PATTERNS += ('scripts/independent_timestamp.py', 'scripts/timestamp-artifact.py',
             'tests/test_independent_timestamp.py', 'tests/fixtures/timestamp-freetsa-2026/*')
PATTERNS += ('scripts/group-receipt.cjs', 'tests/group-receipts.cjs',
             'tests/test_group_receipts.py', 'tests/fixtures/group-receipt-2026/*')
PATTERNS += ('scripts/revocation.cjs', 'tests/offline-revocation.cjs',
             'tests/test_offline_revocation.py', 'tests/fixtures/offline-revocation-2026/*')
PATTERNS += ('scripts/key-backup.cjs', 'scripts/atomic-output.cjs', 'tests/key-backup.cjs', 'tests/test_key_backup.py')
PATTERNS += ('scripts/gateway-key.cjs','scripts/verify-signed-gateway.cjs','tests/test_transport_signing.py','deploy/docker-compose.signing.yml')
PATTERNS += ('spec/image-provenance-boundary.json', 'scripts/verify-image-provenance-boundary.py',
             'scripts/conformance-statement.cjs', 'tests/author-choice.cjs',
             'tests/conformance-statement.cjs', 'tests/test_consent_conformance.py',
             'scripts/corpus-support.py', 'tests/test_corpus_support.py',
             'scripts/verify-consent-conformance.py')
PATTERNS += ('tools/package_proximity.py', 'tools/language_observations.py',
             'tools/credential_flow.py', 'scripts/package-proximity.py',
             'scripts/language-observations.py', 'scripts/credential-flow.py',
             'scripts/verify-independent-observations.py', 'tests/test_package_proximity.py',
             'tests/test_language_observations.py', 'tests/test_credential_flow.py')
PATTERNS += ('tests/test_observation_verifier.py', 'scripts/verify-mobile-payload.cjs')
PATTERNS += ('tools/manifest_inspection.py', 'scripts/inspect-manifest.py',
             'scripts/verify-manifest-inspection.py', 'tests/test_manifest_inspection.py',
             'tests/test_manifest_workflow.py',
             'eval/c2pa-inspection.lock', 'eval/dependencies/c2pa-inspection.json',
             'tests/fixtures/c2pa-inspection-2026/*')
PATTERNS += ('.gitattributes', 'scripts/license_notices.py', 'scripts/verify-redistribution-notices.py',
             'scripts/collect-runtime-notices.py', 'tests/test_license_notices.py',
             'sbom/notices/*')
PATTERNS += ('deploy/research/metadata-development.sql', 'scripts/verify-metadata-store.py',
             'scripts/metadata-store-sandbox.py', 'tests/test_metadata_store.py')
PATTERNS += ('tools/quantitative_observations.py', 'scripts/quantitative-observations.py',
             'scripts/verify-quantitative-observations.py', 'tests/test_quantitative_observations.py')
PATTERNS += ('scripts/measure-pipeline-performance.py', 'tests/test_pipeline_performance.py',
             'tests/pipeline-timing.cjs', 'runs/2026-10-11-staging-pipeline-performance.json',
             'runs/2026-10-11-staging-pipeline-identity-checked.json')
PATTERNS += ('tools/reviewer_agreement.py', 'scripts/reviewer-agreement.py',
             'scripts/verify-reviewer-agreement.py', 'tests/test_reviewer_agreement.py')
PATTERNS += ('scripts/verify-scope-plan.py', 'scripts/render-scope-plan.py', 'tests/test_scope_index.py')
PATTERNS += ('scripts/verify-workflows.cjs',)
PATTERNS += ('tools/redaction_observations.py', 'scripts/measure-redaction-development.py',
             'scripts/redaction-development-worker.py', 'scripts/build-redaction-performance.py',
             'eval/fixtures/pii-recognition-development.json', 'tests/test_complete_ipv6.py',
             'tests/test_redaction_observations.py', 'tests/test_redaction_development_client.py',
             'tests/test_redaction_development_builder.py', 'tests/redaction-performance.cjs',
             'runs/2026-10-11-pii-recognition-staging.json', 'runs/2026-10-11-pii-pipeline-timing.json')
PATTERNS += ('eval/fixtures/pii-compact-addresses.json', 'runs/2026-10-11-pii-labels-recognition.json', 'runs/2026-10-11-pii-labels-compact.json', 'runs/2026-10-11-pii-labels-timing.json')
PATTERNS += ('tools/blind_review_io.py', 'scripts/prepare-ps-review.py', 'scripts/verify-blind-review-privacy.py',
             'scripts/verify-blind-review-browser.cjs', 'tests/test_blind_review.py',
             'tests/test_blind_review_privacy.py', 'tests/blind-review-files.cjs', 'docs/independent-review.md')
PATTERNS += ('research/nli/**/*', 'research/__init__.py', 'scripts/check-nli-pairs.py',
             'scripts/fetch-nli-assets.py', 'scripts/verify-nli-pairs.py', 'scripts/verify-nli-profile.py',
             'tests/test_nli_pairs.py', 'tests/test_nli_network.py', 'tests/test_nli_cli.py',
             'docs/nli-pairs.md', 'docs/nli-pairs-plan.md')
PATTERNS += ('scripts/check-nli-references.py','scripts/verify-nli-references.py',
             'tests/test_captured_corpus.py','tests/test_nli_references.py','tests/test_nli_reference_cli.py',
             'docs/nli-references.md','docs/nli-reference-plan.md')
PATTERNS += ('tools/choice_framing.py','scripts/check-choice-framing.py','scripts/prepare-choice-demo.py',
             'scripts/verify-choice-framing.py','tests/test_choice_framing.py','tests/test_choice_framing_cli.py',
             'docs/choice-framing.md','docs/choice-framing-plan.md','docs/choice-grammar-result.md','docs/changelog-policy.md',
             'eval/revalidation.json','tests/test_website_evidence_inputs.py')
PATTERNS += ('scripts/build-device-detector.py',)
# Host font rendering changes this decorative raster, not executable sources.
# The versioned prepare.mjs generator remains fingerprinted; deployment checks
# still compare every published artifact byte. No other source is excluded.
HOST_RENDERED_ASSET = 'site/public/share-card.png'

PATTERNS += ('mobile/ios/**/*', 'scripts/native_bundle.py', 'scripts/native-probe-cases.py',
             'scripts/prepare-native-bundle.py', 'scripts/verify-ios-bundle.py', 'scripts/verify-shared-text.py',
             'tests/test_native_bundle.py', 'docs/native-share-plan.md', 'docs/native-engine-checks.md',
             'docs/experiments/native-share-unreleased.json', 'tools/private_policy.py',
             'scripts/check-private-policy.py', 'scripts/prepare-private-policy-demo.py',
             'scripts/verify-private-policy.py', 'tests/test_private_policy.py', 'tests/test_private_policy_cli.py',
             'docs/private-policy-plan.md', 'docs/private-policy.md', 'docs/private-policy-result.md')

PATTERNS += ('scripts/asset_notices.py', 'scripts/verify-asset-notices.py', 'tests/test_asset_notices.py',
             'sbom/assets/*', 'site/public/device-licenses/*', 'site/public/fonts/*',
             'eval/vectors/unicode/LICENSE.txt', 'docs/asset-notices-plan.md', 'docs/asset-notices.md', 'docs/asset-notices-result.md')

PATTERNS += ('tools/newsroom.py','tools/editorial_cli.py','scripts/editorial-review.py',
             'scripts/prepare-editorial-review.py','scripts/prepare-editorial-demo.py',
             'scripts/verify-editorial-cli.py','scripts/verify-editorial-workflow.cjs',
             'tests/test_newsroom.py','tests/test_editorial_cli.py','tests/test_local_cli.py',
             'docs/editorial-workflow-plan.md','docs/editorial-workflow.md','docs/editorial-workflow-result.md')

PATTERNS += ('tests/fixtures/legacy-review-v1/*', 'tools/review_execution.py', 'tests/test_review_execution_binding.py',
             'docs/review-execution-binding-plan.md', 'docs/review-execution-binding-result.md')

RULES = ('X-01', 'X-03', 'X-04', 'X-06', 'X-08', 'X-12', 'X-14', 'X-15', 'N-007', 'N-008')
DEVICE_SOURCES = ['site/src/device-client.js', 'site/src/device-worker.js',
                  'site/src/ps-result.js', 'site/src/handheld.jsx', 'site/src/review-file.js',
                  'site/src/share-record.js', 'protocol/normalization.mjs',
                  'protocol/normalization-core.js', 'protocol/unicode15-data.json',
                  'services/evaluator/app.py', 'scripts/verify-device.cjs']


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


PATTERNS += ('deploy/backup/*','tests/test_restore_isolation.py','tests/restore_isolation_kernel.py',
             'docs/restore-isolation-plan.md','docs/restore-isolation-result.md')
PATTERNS += ('deploy/research/metadata-invitation-development.sql','scripts/verify-research-invitations.py',
             'tests/test_research_invitations.py','docs/research-invitation-plan.md',
             'docs/research-invitations.md','docs/research-invitation-result.md')

def inventory(root):
    found = {}
    for pattern in PATTERNS:
        for file in root.glob(pattern):
            if '__pycache__' in file.parts:
                continue
            if file.is_symlink() or any(parent.is_symlink() for parent in file.parents if parent != root):
                raise ValueError('Boundary source symlink refused')
            if file.is_file():
                relative = file.relative_to(root).as_posix()
                if (relative in (HOST_RENDERED_ASSET, 'site/src/device-manifest.json')
                        or re.fullmatch(r'site/public/device/method-[a-f0-9]{64}\.py', relative)):
                    continue
                found[relative] = hashlib.sha256(file.read_bytes()).hexdigest()
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


def registry_boundary(value):
    expected = {'profiles': ['registry'], 'build': '../services/registry',
                'network_mode': 'none', 'read_only': True, 'cap_drop': ['ALL'],
                'security_opt': ['no-new-privileges:true'], 'pids_limit': 16,
                'mem_limit': '32m', 'restart': 'no'}
    if value != expected:
        raise ValueError('Deferred registry activation or persistence changed')


def registry_image_boundary(root=ROOT):
    # Bind the reviewed refusal launcher independently of a new source inventory.
    # A future operational registry requires explicit policy/code review.
    expected_launcher = 'a700c02e4c113a92c1e92ab053159df47afbf0953a1c76df6f2e94d4bfd78e10'
    if hashlib.sha256((root/'services/registry/deferred.py').read_bytes()).hexdigest() != expected_launcher:
        raise ValueError('Deferred registry launcher changed')
    lines = (root/'services/registry/Dockerfile').read_text().strip().splitlines()
    if lines != [
        'FROM python:3.12-slim@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1',
        'WORKDIR /app', 'COPY --chmod=0444 deferred.py .',
        'ENV PYTHONDONTWRITEBYTECODE=1', 'USER 10001:10001',
        'CMD ["python", "deferred.py"]']:
        raise ValueError('Deferred registry image activates unreviewed code')



def registry_evidence(relative, root=ROOT):
    if not isinstance(relative, str) or not re.fullmatch(r'runs/[a-z0-9-]+\.json', relative):
        raise ValueError('Invalid registry evidence path')
    report = read_json(root / relative)
    names = ['services/registry/Dockerfile', 'services/registry/deferred.py',
             'scripts/verify-registry-deferral.py']
    expected = {n: hashlib.sha256((root/n).read_bytes()).hexdigest() for n in names}
    if (report.get('pass') is not True or report.get('sources') != expected
            or report.get('registry_activated') is not False
            or report.get('synthetic_data_only') is not True
            or report.get('independent_accuracy_evidence') is not False):
        raise ValueError('Missing or stale registry execution')
    identity = {'uid': 10001, 'caps': {'CapEff': 0, 'CapPrm': 0, 'CapBnd': 0},
                'no_new_privileges': 1}
    if report.get('runtime_identity') != identity or report.get('cleanup') != {
            'owned_containers_removed': 3, 'owned_image_absent': True, 'verified': True}:
        raise ValueError('Registry sandbox or staging cleanup failed')
    cases = report.get('cases', [])
    if len(cases) != 2 or {x.get('name') for x in cases} != {'default', 'unaccepted_future_version'}:
        raise ValueError('Missing registry refusal cases')
    for case in cases:
        expected_case = {'exit_code': 64, 'fixed_output': True, 'data_unchanged': True,
            'synthetic_mount_target': '/tmp', 'user': '10001:10001', 'read_only': True,
            'network': 'none', 'no_published_ports': True, 'not_running': True,
            'memory_limit_bytes': 33554432, 'pid_limit': 16}
        if any(case.get(k) != v for k, v in expected_case.items()) or any(
                line != 'C /etc' for line in case.get('runtime_file_deltas', ['missing'])):
            raise ValueError('Registry refusal execution boundary failed')
    return len(cases)


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
    registry_boundary(services.get('registry'))
    if value.get('volumes'):
        raise ValueError('Initial release acquired persistent registry storage')
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



def replay_evidence(relative, root=ROOT):
    if not isinstance(relative,str) or not re.fullmatch(r'runs/[a-z0-9-]+\.json',relative):
        raise ValueError('Invalid replay evidence path')
    report=read_json(root/relative)
    required=['ordinary','command','pii','both_unicode','quoted_warning','download_only',
              'wrong_original','altered_finding','historical_identity_missing','different_source',
              'invalid_digest','future_wire','credential_permissions']
    if (report.get('pass') is not True or report.get('synthetic_only') is not True
            or report.get('actual_pipeline_and_cli_executed') is not True
            or report.get('private_markers_absent_from_logs') is not True
            or report.get('temporary_input_directory_removed') is not True
            or report.get('public_intake_connected') is not False
            or report.get('independent_accuracy_evidence') is not False
            or [c.get('name') for c in report.get('cases',[])]!=required):
        raise ValueError('Missing bounded current replay execution')
    expected=['protocol/replay.py','protocol/replay_identity.py','protocol/normalization.py',
              'protocol/unicode15-data.json','scripts/replay-assertion.py',
              'scripts/verify-assertion-replay.py','services/gateway/app.py',
              'services/anonymizer/app.py','services/anonymizer/model_identity.py',
              'services/anonymizer/replay_metadata.py','services/anonymizer/requirements.lock',
              'services/evaluator/app.py','spec/assertion.schema.json']
    if report.get('sources')!={n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in expected}:
        raise ValueError('Replay execution source changed')
    states=[('matched',0)]*6+[('input_mismatch',2),('mismatch',1),('unavailable',3),
                             ('unavailable',3),('invalid',4),('unavailable',3),('invalid',4)]
    for row,(state,code) in zip(report['cases'],states):
        if row.get('status')!=state or row.get('exit_code')!=code or row.get('output_contains_no_private_marker') is not True:
            raise ValueError('Replay outcome control failed')
    return len(required)

def evaluate(manifest, root=ROOT):
    fields = {'schema_version', 'wire_version', 'reviewed_at', 'reviewed_by', 'rules',
              'independent_release_approval', 'sources', 'engineering_receipts',
              'device_evidence', 'service_evidence', 'registry_evidence', 'replay_evidence'}
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
    registry_image_boundary(root)
    runpy.run_path(str(root/'scripts/verify-image-provenance-boundary.py'))['verify'](root)
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
    registry_cases = registry_evidence(manifest.get('registry_evidence'), root)
    replay_cases = replay_evidence(manifest.get('replay_evidence'), root)
    return {'routes': observed, 'source_files': len(manifest['sources']),
            'browser_receipts_current': True, 'extension_access_unchanged': True,
            'committed_device_engine_evidence': engines, 'active_services': active,
            'current_remote_service_cases': service_cases, 'registry_0_1_deferred_enforced': True,
            'actual_registry_refusal_cases': registry_cases, 'actual_full_pipeline_replay_cases':replay_cases}


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
    pins = verify_root_inputs(root)
    manifest = read_json(root / 'eval/route-boundaries.json')
    observed = evaluate(manifest, root)
    intake = intake_controls(root)
    if inventory(root) != before:
        raise ValueError('Boundary sources changed during verification')
    return {'captured_at': datetime.now(timezone.utc).isoformat(), 'pass': True,
            'rules': list(RULES), **observed, **intake,
            'python_manifest_lock_roots_verified': len(pins),
            'review_manifest_sha256': hashlib.sha256((root / 'eval/route-boundaries.json').read_bytes()).hexdigest(),
            'independent_accuracy_evidence': False, 'release_approved': False,
            'scope': 'Reviewed current personal source/access/endpoint boundaries and source-bound browser checks. '
                     'Not a proof against host compromise, third-party collection, future changes or new organizational/research routes. '
                     'The deferred registry is refused by this release. Future research intake and license clearance remain separate.'}


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
