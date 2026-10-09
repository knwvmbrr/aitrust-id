"""Fast engineering loop. Passing here never grants release validation."""
import concurrent.futures
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def run(command):
    start = time.monotonic()
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    return {'command':command, 'exit_code':result.returncode,
            'elapsed_seconds':round(time.monotonic()-start,3),
            'output':result.stdout, 'stderr':result.stderr}


def main():
    start = time.monotonic()
    commands = [[sys.executable,'-m','pytest','tests','-q'],
                [sys.executable,'scripts/verify-regressions.py']]
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        checks = list(pool.map(run,commands))
    report = {'format':'ai-trust-id-fast-engineering/v1',
              'engineering_pass':all(row['exit_code']==0 for row in checks),
              'elapsed_seconds':round(time.monotonic()-start,3), 'checks':checks,
              'independent_accuracy_evidence':False, 'release_assessed':False,
              'scope':'Python source checks and all active development fixtures; mobile engines, live services and human review are separate.'}
    (ROOT/'eval/fast-engineering-report.json').write_text(json.dumps(report,indent=2)+'\n')
    for row in checks:
        name = 'pytest tests' if row['command'][1] == '-m' else Path(row['command'][1]).name
        print(f"{name}: exit {row['exit_code']}, {row['elapsed_seconds']}s")
        if row['exit_code']:
            print(row['output'],row['stderr'])
    print(f"Engineering {'PASS' if report['engineering_pass'] else 'FAIL'} in {report['elapsed_seconds']}s; release not assessed.")
    return 0 if report['engineering_pass'] else 1


if __name__ == '__main__':
    sys.exit(main())
