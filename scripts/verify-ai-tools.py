#!/usr/bin/env python3
"""Execute optional AI-tool API and real MCP interoperability checks."""
from datetime import datetime, timezone
import argparse
import hashlib
import json
from pathlib import Path
import runpy
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
SOURCES = ('tools/tag_api.py', 'scripts/tag-api.py', 'scripts/ai-tools-server.py',
           'scripts/check-tags.py', 'scripts/check-ps.py', 'scripts/aitrust.py',
           'scripts/worker_process.py', 'scripts/build-device-detector.py',
           'services/evaluator/app.py', 'spec/assertion.schema.json',
           'protocol/normalization.py', 'protocol/unicode15-data.json',
           'integrations/mcp/requirements.in', 'integrations/mcp/requirements.lock',
           'integrations/ai-tools/function-tools.json', 'integrations/ai-tools/check-text.input.schema.json',
           'integrations/ai-tools/check-text.output.schema.json',
           'tests/test_ai_tag_api.py', 'tests/test_ai_tools_mcp.py', 'scripts/verify-ai-tools.py',
           'docs/ai-tools.md', 'docs/ai-tool-plugin-plan.md', 'docs/tag-safety-use-cases.json')


def fingerprints():
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in SOURCES}


def verify():
    from importlib.metadata import version
    if version('mcp') != '2.3.0':
        raise ValueError('Install the pinned optional SDK')
    before = fingerprints()
    server = runpy.run_path(str(ROOT / 'scripts/ai-tools-server.py'))
    expected = [
        ('integrations/ai-tools/check-text.input.schema.json', server['CHECK_SCHEMA']),
        ('integrations/ai-tools/check-text.output.schema.json', server['RESULT_SCHEMA']),
        ('integrations/ai-tools/function-tools.json', [{'type': 'function', 'name': t.name,
            'description': t.description, 'parameters': t.input_schema} for t in server['TOOLS']]),
    ]
    for path, value in expected:
        if json.loads((ROOT / path).read_text()) != value:
            raise ValueError('Tool schema differs from implementation')
    executed = []
    for test in ('test_ai_tag_api.py', 'test_ai_tools_mcp.py'):
        child = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-p', test, '-v'],
                               cwd=ROOT, capture_output=True, timeout=60)
        if child.returncode:
            raise ValueError('AI tool control failed')
        count = re.search(rb'Ran (\d+) tests?', child.stderr)
        if not count or b'skipped' in child.stderr.lower():
            raise ValueError('Required AI tool checks were skipped')
        executed.append({'suite': test, 'exit': child.returncode, 'tests_passed': int(count.group(1)),
                         'stdout_sha256': hashlib.sha256(child.stdout).hexdigest(),
                         'stderr_sha256': hashlib.sha256(child.stderr).hexdigest()})
    if before != fingerprints():
        raise ValueError('Source changed during execution')
    return {'kind': 'ai_tag_tools_software_verification', 'captured_at': datetime.now(timezone.utc).isoformat(),
            'pass': True, 'implemented_by': 'Codex', 'sources': before, 'suites': executed,
            'sdk': {'name': 'mcp', 'version': version('mcp')}, 'real_stdio_protocol': True,
            'actual_ps_check': True, 'independent_missing_privacy': True, 'cancellation_capacity': True,
            'private_marker_not_reflected': True, 'malformed_and_oversize_wire_refused': True,
            'public_endpoint_deployed': False, 'community_launched': False,
            'independent_tag_validation': False, 'original_requirements_closed': []}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', help='Repository execution receipt under runs/ or output/.')
    a = p.parse_args()
    try:
        row = verify()
        if a.output:
            from protocol.reports import write_report
            write_report(a.output, row)
        print(json.dumps(row))
    except Exception:
        print('AI tool verification unavailable or failed.', file=sys.stderr)
        raise SystemExit(1)
